"""Headscale WebUI authentication abstraction."""

import secrets
from functools import wraps
from typing import Awaitable, Callable, Literal, ParamSpec, TypeVar

import requests
from flask import current_app
from flask.typing import ResponseReturnValue
from flask_basicauth import BasicAuth  # type: ignore
from flask_oidc import OpenIDConnect  # type: ignore
from pydantic import AnyHttpUrl, AnyUrl, BaseModel, Field

from config import BasicAuthConfig, Config, OidcAuthConfig


class OidcSecretsModel(BaseModel):
    """OIDC secrets model used by the flask_oidc module."""

    class OidcWebModel(BaseModel):
        """OIDC secrets web model."""

        issuer: AnyHttpUrl
        auth_uri: AnyHttpUrl
        client_id: str
        client_secret: str = Field(hidden=True)
        redirect_uris: list[AnyUrl]
        userinfo_uri: AnyHttpUrl | None
        token_uri: AnyHttpUrl

    web: OidcWebModel


class OpenIdProviderMetadata(BaseModel):
    """OIDC Provider Metadata model.

    From https://openid.net/specs/openid-connect-discovery-1_0.html#ProviderMetadata

    TODO: Add default factories for some fields and maybe descriptions.
    """

    class Config:
        """BaseModel configuration."""

        extra = "allow"
        """Used for logout_redirect_uri."""

    issuer: AnyHttpUrl
    authorization_endpoint: AnyHttpUrl
    token_endpoint: AnyHttpUrl
    userinfo_endpoint: AnyHttpUrl | None
    jwks_uri: AnyHttpUrl
    registration_endpoint: AnyHttpUrl | None
    scopes_supported: list[str]
    response_types_supported: list[
        Literal[
            "code",
            "id_token",
            "id_token token",
            "code id_token",
            "code token",
            "code id_token token",
            "none",
        ]
    ]
    response_modes_supported: list[Literal["query", "fragment"]] | None
    grant_types_supported: list[str] | None
    acr_values_supported: list[str] | None
    subject_types_supported: list[str]
    id_token_signing_alg_values_supported: list[str]
    id_token_encryption_alg_values_supported: list[str] | None
    id_token_encryption_enc_values_supported: list[str] | None
    userinfo_signing_alg_values_supported: list[str | None] | None
    userinfo_encryption_alg_values_supported: list[str] | None
    userinfo_encryption_enc_values_supported: list[str] | None
    request_object_signing_alg_values_supported: list[str] | None
    request_object_encryption_alg_values_supported: list[str] | None
    request_object_encryption_enc_values_supported: list[str] | None
    token_endpoint_auth_methods_supported: list[str] | None
    token_endpoint_auth_signing_alg_values_supported: list[str] | None
    display_values_supported: list[Literal["page", "popup", "touch", "wap"]] | None
    claim_types_supported: list[Literal["normal", "aggregated", "distributed"]] | None
    claims_supported: list[str] | None
    service_documentation: AnyUrl | None
    claims_locales_supported: list[str] | None
    ui_locales_supported: list[str] | None
    claims_parameter_supported: bool = Field(False)
    request_parameter_supported: bool = Field(False)
    request_uri_parameter_supported: bool = Field(True)
    require_request_uri_registration: bool = Field(False)
    op_policy_uri: AnyUrl | None
    op_tos_uri: AnyUrl | None


T = TypeVar("T")
P = ParamSpec("P")


class AuthManager:
    """Authentication manager."""

    def __init__(self, config: Config, request_timeout: float = 10) -> None:
        """Initialize the authentication manager.

        Arguments:
            config -- main application configuration.

        Keyword Arguments:
            request_timeout -- timeout for OIDC request (default: {10})
        """
        self._gui_url = config.domain_name + config.base_path
        self._auth_type = config.auth_type
        self._auth_config = config.auth_type.config
        self._logout_url: str | None = None
        self._request_timeout = request_timeout

        match self._auth_config:
            case BasicAuthConfig():
                current_app.logger.info(
                    "Loading basic auth libraries and configuring app..."
                )

                current_app.config["BASIC_AUTH_USERNAME"] = self._auth_config.username
                current_app.config["BASIC_AUTH_PASSWORD"] = self._auth_config.password
                current_app.config["BASIC_AUTH_FORCE"] = True

                # TODO: Change for flask-httpauth – flask_basicauth is not maintained.
                self._auth_handler = BasicAuth(current_app)
            case OidcAuthConfig():
                current_app.logger.info("Loading OIDC libraries and configuring app...")

                oidc_info = OpenIdProviderMetadata.parse_obj(
                    requests.get(
                        self._auth_config.auth_url, timeout=request_timeout
                    ).json()
                )
                current_app.logger.debug(
                    "JSON dump for OIDC_INFO: %s", oidc_info.json()
                )

                client_secrets = OidcSecretsModel(
                    web=OidcSecretsModel.OidcWebModel(
                        issuer=oidc_info.issuer,
                        auth_uri=oidc_info.authorization_endpoint,
                        client_id=self._auth_config.client_id,
                        client_secret=self._auth_config.secret,
                        redirect_uris=[
                            AnyUrl(
                                f"{config.domain_name}{config.base_path}/oidc_callback",
                                scheme="",
                            )
                        ],
                        userinfo_uri=oidc_info.userinfo_endpoint,
                        token_uri=oidc_info.token_endpoint,
                    )
                )

                # Make the best effort to create the data directory.
                try:
                    config.app_data_dir.mkdir(parents=True, exist_ok=True)
                except PermissionError:
                    current_app.logger.warning(
                        "Tried and failed to create data directory %s.",
                        config.app_data_dir,
                    )

                oidc_secrets_path = config.app_data_dir / "secrets.json"
                with open(oidc_secrets_path, "w+", encoding="utf-8") as secrets_file:
                    secrets_file.write(client_secrets.json())

                current_app.config.update(  # type: ignore
                    {
                        "SECRET_KEY": secrets.token_urlsafe(32),
                        "TESTING": config.debug_mode,
                        "DEBUG": config.debug_mode,
                        "OIDC_CLIENT_SECRETS": oidc_secrets_path,
                        "OIDC_ID_TOKEN_COOKIE_SECURE": True,
                        "OIDC_REQUIRE_VERIFIED_EMAIL": False,
                        "OIDC_USER_INFO_ENABLED": True,
                        "OIDC_OPENID_REALM": "Headscale-WebUI",
                        "OIDC_SCOPES": ["openid", "profile", "email"],
                        "OIDC_INTROSPECTION_AUTH_METHOD": "client_secret_post",
                    }
                )

                self._logout_url = getattr(oidc_info, "end_session_endpoint", None)

                self._auth_handler = OpenIDConnect(current_app)

    def require_login(
        self,
        func: Callable[P, ResponseReturnValue]
        | Callable[P, Awaitable[ResponseReturnValue]],
    ) -> Callable[P, ResponseReturnValue]:
        """Guard decorator used for restricting access to the Flask page.

        Uses OIDC or Basic auth depending on configuration.
        """

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> ResponseReturnValue:
            sync_func = current_app.ensure_sync(func)  # type: ignore
            sync_func.__name__ = f"{func.__name__}"

            # OIDC
            # TODO: Add user group restrictions.
            if isinstance(self._auth_handler, OpenIDConnect):
                return self._auth_handler.require_login(sync_func)(  # type: ignore
                    *args, **kwargs
                )

            # Basic auth
            return self._auth_handler.required(sync_func)(  # type: ignore
                *args, **kwargs
            )

        return wrapper

    def logout(self) -> str | None:
        """Execute logout with the auth provider."""
        # Logout is only applicable for OIDC.
        if isinstance(self._auth_handler, OpenIDConnect):
            self._auth_handler.logout()

        if isinstance(self._auth_config, OidcAuthConfig):
            if self._logout_url is not None:
                logout_url = self._logout_url
                if self._auth_config.logout_redirect_uri is not None:
                    logout_url += (
                        "?post_logout_redirect_uri="
                        + self._auth_config.logout_redirect_uri
                    )
                return logout_url

        return None

    @property
    def oidc_handler(self) -> OpenIDConnect | None:
        """Get the OIDC handler if exists."""
        if isinstance(self._auth_handler, OpenIDConnect):
            return self._auth_handler
        return None
