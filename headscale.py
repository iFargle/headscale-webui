"""Headscale API abstraction."""

from functools import wraps
from typing import Awaitable, Callable, ParamSpec, TypeVar

from cryptography.fernet import Fernet
from flask import current_app, redirect, url_for
from flask.typing import ResponseReturnValue
from headscale_api.config import HeadscaleConfig as HeadscaleConfigBase
from headscale_api.headscale import Headscale, UnauthorizedError
from pydantic import ValidationError

from config import Config

T = TypeVar("T")
P = ParamSpec("P")


class HeadscaleApi(Headscale):
    """Headscale API abstraction."""

    def __init__(self, config: Config, requests_timeout: float = 10):
        """Initialize the Headscale API abstraction.

        Arguments:
            config -- Headscale WebUI configuration.

        Keyword Arguments:
            requests_timeout -- timeout of API requests in seconds (default: {10})
        """
        self._config = config
        self._hs_config: HeadscaleConfigBase | None = None
        self._api_key: str | None = None
        self.logger = current_app.logger
        super().__init__(
            self.base_url,
            self.api_key,
            requests_timeout,
            raise_exception_on_error=False,
            logger=current_app.logger,
        )

    @property
    def app_config(self) -> Config:
        """Get Headscale WebUI configuration."""
        return self._config

    @property
    def hs_config(self) -> HeadscaleConfigBase | None:
        """Get Headscale configuration and cache on success.

        Returns:
            Headscale configuration if a valid configuration has been found.
        """
        if self._hs_config is not None:
            return self._hs_config

        try:
            return HeadscaleConfigBase.parse_file(self._config.hs_config_path)
        except ValidationError as error:
            self.logger.warning(
                "Following errors happened when tried to parse Headscale config:"
            )
            for sub_error in str(error).splitlines():
                self.logger.warning("  %s", sub_error)
            return None

    @property
    def base_url(self) -> str:
        """Get base URL of the Headscale server.

        Tries to load it from Headscale config, otherwise falls back to WebUI config.
        """
        if self.hs_config is None or self.hs_config.server_url is None:
            self.logger.warning(
                'Failed to find "server_url" in the Headscale config. Falling back to '
                "the environment variable."
            )
            return self._config.hs_server

        return self.hs_config.server_url

    @property
    def api_key(self) -> str | None:
        """Get API key from cache or from file."""
        if self._api_key is not None:
            return self._api_key

        if not self._config.key_file.exists():
            return None

        with open(self._config.key_file, "rb") as key_file:
            enc_api_key = key_file.read()
            if enc_api_key == b"":
                return None

            self._api_key = Fernet(self._config.key).decrypt(enc_api_key).decode()
            return self._api_key

    @api_key.setter
    def api_key(self, new_api_key: str):
        """Write the new API key to file and store in cache."""
        with open(self._config.key_file, "wb") as key_file:
            key_file.write(Fernet(self._config.key).encrypt(new_api_key.encode()))

        # Save to local cache only after successful file write.
        self._api_key = new_api_key

    def key_check_guard(
        self, func: Callable[P, T] | Callable[P, Awaitable[T]]
    ) -> Callable[P, T | ResponseReturnValue]:
        """Ensure the validity of a Headscale API key with decorator.

        Also, it checks if the key needs renewal and if it is invalid redirects to the
        settings page.
        """

        @wraps(func)
        def decorated(*args: P.args, **kwargs: P.kwargs) -> T | ResponseReturnValue:
            try:
                return current_app.ensure_sync(func)(*args, **kwargs)  # type: ignore
            except UnauthorizedError:
                current_app.logger.warning(
                    "Detected unauthorized error from Headscale API. "
                    "Redirecting to settings."
                )
                return redirect(url_for("settings_page"))

        return decorated
