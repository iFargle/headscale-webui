"""Headscale WebUI Flask server."""

import asyncio
import atexit
import datetime
import functools
from multiprocessing import Lock
from typing import Awaitable, Callable, Type, TypeVar

import headscale_api.schema.headscale.v1 as schema
from aiohttp import ClientConnectionError
from apscheduler.schedulers.background import BackgroundScheduler  # type: ignore
from betterproto import Message
from flask import Flask, redirect, render_template, url_for
from flask_pydantic.core import validate
from headscale_api.headscale import UnauthorizedError
from markupsafe import Markup
from pydantic import BaseModel, Field
from werkzeug.middleware.proxy_fix import ProxyFix

import renderer
from auth import AuthManager
from config import Config, InitCheckError
from headscale import HeadscaleApi


def create_tainted_app(app: Flask, error: InitCheckError) -> Flask:
    """Run tainted version of the Headscale WebUI after encountering an error."""
    app.logger.error(
        "Encountered error when trying to run initialization checks. Running in "
        "tainted mode (only the error page is available). Correct all errors and "
        "restart the server."
    )

    @app.route("/<path:path>")
    def catchall_redirect(path: str):  # pylint: disable=unused-argument
        return redirect(url_for("error_page"))

    @app.route("/error")
    async def error_page():
        return render_template(
            "error.html",
            error_message=Markup(
                "".join(sub_error.format_message() for sub_error in error)
            ),
        )

    return app


async def create_app() -> Flask:
    """Run Headscale WebUI Flask application.

    For arguments refer to `Flask.run()` function.
    """
    app = Flask(__name__, static_url_path="/static")
    app.wsgi_app = ProxyFix(  # type: ignore[method-assign]
        app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1  # type: ignore
    )
    try:
        # Try to initialize configuration from environment.
        config = Config()  # type: ignore

        with app.app_context():
            # Try to create authentication handler (including loading auth config).
            auth = AuthManager(config)

            # Try to create Headscale API interface.
            headscale = HeadscaleApi(config)

        # Check health of Headscale API.
        if not await headscale.health_check():
            raise ClientConnectionError(f"Health check failed on {headscale.base_url}")
    except Exception as error:  # pylint: disable=broad-exception-caught
        # We want to catch broad exception to ensure no errors whatsoever went through
        # the environment init.
        with app.app_context():
            check_error = InitCheckError.from_exception(error)
        return create_tainted_app(app, check_error)

    app.logger.setLevel(config.log_level)
    app.logger.info(
        "Headscale-WebUI Version: %s / %s", config.app_version, config.git_branch
    )
    app.logger.info("Logger level set to %s.", config.log_level)
    app.logger.info("Debug state: %s", config.debug_mode)

    register_pages(app, headscale, auth)
    register_api_endpoints(app, headscale, auth)
    register_scheduler(app, headscale)

    return app


def register_pages(app: Flask, headscale: HeadscaleApi, auth: AuthManager):
    """Register user-facing pages."""
    config = headscale.app_config

    # Convenience short for render_defaults
    render_defaults = functools.partial(
        renderer.render_defaults, config, auth.oidc_handler
    )

    @app.route("/")
    @app.route("/overview")
    @auth.require_login
    @headscale.key_check_guard
    async def overview_page():
        return render_template(
            "overview.html",
            render_page=await renderer.render_overview(headscale),
            **render_defaults(),
        )

    @app.route("/routes", methods=("GET", "POST"))
    @auth.require_login
    @headscale.key_check_guard
    async def routes_page():
        return render_template(
            "routes.html",
            render_page=await renderer.render_routes(headscale),
            **render_defaults(),
        )

    @app.route("/machines", methods=("GET", "POST"))
    @auth.require_login
    @headscale.key_check_guard
    async def machines_page():
        return render_template(
            "machines.html",
            cards=await renderer.render_machines_cards(headscale),
            headscale_server=config.hs_server,
            inpage_search=renderer.render_search(),
            **render_defaults(),
        )

    @app.route("/users", methods=("GET", "POST"))
    @auth.require_login
    @headscale.key_check_guard
    async def users_page():
        return render_template(
            "users.html",
            cards=await renderer.render_users_cards(headscale),
            inpage_search=renderer.render_search(),
        )

    @app.route("/settings", methods=("GET", "POST"))
    @auth.require_login
    async def settings_page():
        return render_template(
            "settings.html",
            url=headscale.base_url,
            BUILD_DATE=config.build_date,
            APP_VERSION=config.app_version,
            GIT_REPO_URL=config.git_repo_url,
            GIT_COMMIT=config.git_commit,
            GIT_BRANCH=config.git_branch,
            HS_VERSION=config.hs_version,
            **render_defaults(),
        )

    @app.route("/error")
    async def error_page():
        """Error page redirect.

        Once we get out of tainted mode, we want to still have this route active so that
        users refreshing the page get redirected to the overview page.
        """
        return redirect(url_for("overview_page"))

    @app.route("/logout")
    @auth.require_login
    @headscale.key_check_guard
    async def logout_page():
        logout_url = auth.logout()
        if logout_url is not None:
            return redirect(logout_url)
        return redirect(url_for("overview_page"))


def register_api_endpoints(app: Flask, headscale: HeadscaleApi, auth: AuthManager):
    """Register Headscale WebUI API endpoints."""
    RequestT = TypeVar("RequestT", bound=Message)
    ResponseT = TypeVar("ResponseT", bound=Message)

    def api_passthrough(
        route: str,
        request_type: Type[RequestT],
        api_method: Callable[[RequestT], Awaitable[ResponseT | str]],
    ):
        """Passthrough the Headscale API in a concise form.

        Arguments:
            route -- Flask route to the API endpoint.
            request_type -- request model (from headscale_api.schema).
            api_method -- backend method to pass through the Flask request.
        """

        async def api_passthrough_page(body: RequestT) -> ResponseT | str:
            return await api_method(body)  # type: ignore

        api_passthrough_page.__name__ = route.replace("/", "_")
        api_passthrough_page.__annotations__ = {"body": request_type}

        return app.route(route, methods=["POST"])(
            auth.require_login(
                headscale.key_check_guard(
                    validate()(api_passthrough_page)  # type: ignore
                )
            )
        )

    class TestKeyRequest(BaseModel):
        """/api/test_key request."""

        api_key: str | None = Field(
            None, description="API key to test. If None test the current key."
        )

    @app.route("/api/test_key", methods=("GET", "POST"))
    @auth.require_login
    @validate()
    async def test_key_page(body: TestKeyRequest):
        if body.api_key == "":
            body.api_key = None

        async with headscale.session:
            if not await headscale.test_api_key(body.api_key):
                return "Unauthenticated", 401

            ret = await headscale.renew_api_key()
            match ret:
                case None:
                    return "Unauthenticated", 401
                case schema.ApiKey():
                    return ret
                case _:
                    new_key_info = await headscale.get_api_key_info()
                    if new_key_info is None:
                        return "Unauthenticated", 401
                    return new_key_info

    class SaveKeyRequest(BaseModel):
        """/api/save_key request."""

        api_key: str

    @app.route("/api/save_key", methods=["POST"])
    @auth.require_login
    @validate()
    async def save_key_page(body: SaveKeyRequest):
        async with headscale.session:
            # Test the new API key.
            if not await headscale.test_api_key(body.api_key):
                return "Key failed testing. Check your key.", 401

            try:
                headscale.api_key = body.api_key
            except OSError:
                return "Key did not save properly. Check logs.", 500

            key_info = await headscale.get_api_key_info()

        if key_info is None:
            return "Key saved but error occurred on key info retrieval."

        return (
            f'Key saved and tested: Key: "{key_info.prefix}", '
            f"expiration: {key_info.expiration}"
        )

    ####################################################################################
    # Machine API Endpoints
    ####################################################################################

    class UpdateRoutePageRequest(BaseModel):
        """/api/update_route request."""

        route_id: int
        current_state: bool

    @app.route("/api/update_route", methods=["POST"])
    @auth.require_login
    @validate()
    async def update_route_page(body: UpdateRoutePageRequest):
        if body.current_state:
            return await headscale.disable_route(
                schema.DisableRouteRequest(body.route_id)
            )
        return await headscale.enable_route(schema.EnableRouteRequest(body.route_id))

    api_passthrough(
        "/api/machine_information",
        schema.GetMachineRequest,
        headscale.get_machine,
    )
    api_passthrough(
        "/api/delete_machine",
        schema.DeleteMachineRequest,
        headscale.delete_machine,
    )
    api_passthrough(
        "/api/rename_machine",
        schema.RenameMachineRequest,
        headscale.rename_machine,
    )
    api_passthrough(
        "/api/move_user",
        schema.MoveMachineRequest,
        headscale.move_machine,
    )
    api_passthrough("/api/set_machine_tags", schema.SetTagsRequest, headscale.set_tags)
    api_passthrough(
        "/api/register_machine",
        schema.RegisterMachineRequest,
        headscale.register_machine,
    )

    ####################################################################################
    # User API Endpoints
    ####################################################################################

    api_passthrough("/api/rename_user", schema.RenameUserRequest, headscale.rename_user)
    api_passthrough("/api/add_user", schema.CreateUserRequest, headscale.create_user)
    api_passthrough("/api/delete_user", schema.DeleteUserRequest, headscale.delete_user)
    api_passthrough("/api/get_users", schema.ListUsersRequest, headscale.list_users)

    ####################################################################################
    # Pre-Auth Key API Endpoints
    ####################################################################################

    api_passthrough(
        "/api/add_preauth_key",
        schema.CreatePreAuthKeyRequest,
        headscale.create_pre_auth_key,
    )
    api_passthrough(
        "/api/expire_preauth_key",
        schema.ExpirePreAuthKeyRequest,
        headscale.expire_pre_auth_key,
    )
    api_passthrough(
        "/api/build_preauthkey_table",
        schema.ListPreAuthKeysRequest,
        functools.partial(renderer.build_preauth_key_table, headscale),
    )

    ####################################################################################
    # Route API Endpoints
    ####################################################################################

    api_passthrough("/api/get_routes", schema.GetRoutesRequest, headscale.get_routes)


scheduler_registered: bool = False
scheduler_lock = Lock()


def register_scheduler(app: Flask, headscale: HeadscaleApi):
    """Register background scheduler."""
    global scheduler_registered  # pylint: disable=global-statement

    with scheduler_lock:
        if scheduler_registered:
            # For multi-worker set-up, only a single scheduler needs to be enabled.
            return

        scheduler = BackgroundScheduler(
            logger=app.logger, timezone=headscale.app_config.timezone
        )
        scheduler.start()  # type: ignore

        def renew_api_key():
            """Renew API key in a background job."""
            app.logger.info("Key renewal schedule triggered...")
            try:
                if app.ensure_sync(headscale.renew_api_key)() is None:  # type: ignore
                    app.logger.error("Failed to renew the key. Check configuration.")
            except UnauthorizedError:
                app.logger.error("Current key is invalid. Check configuration.")

        scheduler.add_job(  # type: ignore
            renew_api_key,
            "interval",
            hours=1,
            id="renew_api_key",
            max_instances=1,
            next_run_time=datetime.datetime.now(),
        )

        atexit.register(scheduler.shutdown)  # type: ignore

        scheduler_registered = True


headscale_webui = asyncio.run(create_app())

if __name__ == "__main__":
    headscale_webui.run(host="0.0.0.0")
