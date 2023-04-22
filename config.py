"""Headscale WebUI configuration."""

import importlib.metadata
import itertools
import os
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from logging import getLevelNamesMapping
from pathlib import Path
from typing import Any, Type
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from aiohttp import ClientConnectionError
from flask import current_app
from pydantic import validator  # type: ignore
from pydantic import (
    AnyUrl,
    BaseModel,
    BaseSettings,
    ConstrainedStr,
    Field,
    ValidationError,
)

import helper


class OidcAuthConfig(BaseSettings):
    """OpenID Connect authentication configuration.

    Used only if "AUTH_TYPE" environment variable is set to "oidc".
    """

    auth_url: str = Field(
        ...,
        env="OIDC_AUTH_URL",
        description=(
            "URL to OIDC auth endpoint. Example: "
            '"https://example.com/.well-known/openid-configuration"'
        ),
    )
    client_id: str = Field(
        env="OIDC_CLIENT_ID",
        description="OIDC client ID.",
    )
    secret: str = Field(
        env="OIDC_CLIENT_SECRET",
        description="OIDC client secret.",
    )
    logout_redirect_uri: str | None = Field(
        None,
        env="OIDC_LOGOUT_REDIRECT_URI",
        description="Optional OIDC redirect URL to follow after logout.",
    )


class BasicAuthConfig(BaseSettings):
    """Basic auth authentication configuration.

    Used only if "AUTH_TYPE" environment variable is set to "basic".
    """

    username: str = Field(
        "headscale", env="BASIC_AUTH_USER", description="Username for basic auth."
    )
    password: str = Field(
        "headscale", env="BASIC_AUTH_PASS", description="Password for basic auth."
    )


class AuthType(StrEnum):
    """Authentication type."""

    BASIC = "basic"
    OIDC = "oidc"

    @property
    def config(self):
        """Get configuration depending on enum value."""
        match self:
            case self.BASIC:
                return BasicAuthConfig()  # type: ignore
            case self.OIDC:
                return OidcAuthConfig()  # type: ignore


class _LowerConstr(ConstrainedStr):
    """String with lowercase transformation."""

    to_lower = True


@dataclass
class InitCheckErrorModel:
    """Initialization check error model."""

    title: str
    details: str

    def print_to_logger(self):
        """Print the error information to logger."""
        current_app.logger.critical(self.title)

    def format_message(self) -> str:
        """Format message for the error page."""
        return helper.format_message(
            helper.MessageErrorType.ERROR, self.title, f"<p>{self.details}</p>"
        )


@dataclass
class InitCheckError(RuntimeError):
    """Initialization check error."""

    errors: list[InitCheckErrorModel] | InitCheckErrorModel | None = None

    def append_error(self, error: InitCheckErrorModel):
        """Append error to the errors collection."""
        match self.errors:
            case InitCheckErrorModel():
                self.errors = [self.errors, error]
            case list():
                self.errors.append(error)
            case _:
                self.errors = error

    def __iter__(self):  # noqa
        match self.errors:
            case InitCheckErrorModel():
                yield self.errors
            case list():
                for error in self.errors:
                    yield error
            case _:
                return

    @classmethod
    def from_validation_error(cls, error: ValidationError):
        """Create an InitCheckError from Pydantic's ValidationError."""
        current_app.logger.critical(
            "Following environment variables are required but are not declared or have "
            "an invalid value:"
        )

        new_error = cls()
        for sub_pydantic_error in error.errors():
            pydantic_name = sub_pydantic_error["loc"][0]
            assert isinstance(
                pydantic_name, str
            ), "Configuration class malformed. Raise issue on GitHub."

            model: Type[BaseModel] = error.model  # type: ignore
            field = model.__fields__[pydantic_name]
            assert (
                "env" in field.field_info.extra
            ), "Environment variable name not set. Raise issue on GitHub."

            current_app.logger.critical(
                "  %s with type %s: %s",
                field.field_info.extra["env"],
                field.type_.__name__,
                sub_pydantic_error["type"],
            )

            new_error.append_error(
                InitCheckErrorModel(
                    f"Environment error for {field.field_info.extra['env']}",
                    f"Required variable {field.field_info.extra['env']} with type "
                    f'"{field.type_.__name__}" validation error '
                    f"({sub_pydantic_error['type']}): {sub_pydantic_error['msg']}. "
                    f"Variable description: {field.field_info.description}",
                )
            )
        return new_error

    @classmethod
    def from_client_connection_error(cls, error: ClientConnectionError):
        """Create an InitCheckError from aiohttp's ClientConnectionError."""
        return InitCheckError(
            InitCheckErrorModel(
                "Headscale server API is unreachable.",
                "Your headscale server is either unreachable or not properly "
                "configured. Please ensure your configuration is correct. Error"
                f"details: {error}",
            )
        )

    @classmethod
    def from_exception(cls, error: Exception, print_to_logger: bool = True):
        """Create an InitCheckError from any error.

        Some special cases are handled separately.
        """
        if isinstance(error, InitCheckError):
            new_error = error
        elif isinstance(error, ValidationError):
            new_error = cls.from_validation_error(error)
        elif isinstance(error, ClientConnectionError):
            new_error = cls.from_client_connection_error(error)
        else:
            new_error = cls(
                InitCheckErrorModel(
                    f"Unexpected error occurred: {error.__class__.__name__}. Raise an "
                    "issue on GitHub.",
                    str(error),
                )
            )
        if print_to_logger:
            for sub_error in new_error:
                sub_error.print_to_logger()

        return new_error


def _get_version_from_package():
    """Get package version from metadata if not given from environment."""
    return importlib.metadata.version("headscale-webui")


# Functions to get git-related information in development scenario, where no relevant
# environment variables are set. If not in git repository fall back to unknown values.
# GitPython is added as dev dependency, thus we need to have fallback in case of
# production environment.
try:
    from git.exc import GitError
    from git.repo import Repo

    def _get_default_git_branch() -> str:
        try:
            return Repo(search_parent_directories=True).head.ref.name
        except GitError as error:
            return f"Error getting branch name: {error}"

    def _get_default_git_commit() -> str:
        try:
            return Repo(search_parent_directories=True).head.ref.object.hexsha
        except GitError as error:
            return f"Error getting commit ID: {error}"

    def _get_default_git_repo_url_gitpython() -> str | None:
        try:
            return (
                Repo(search_parent_directories=True)
                .remotes[0]
                .url.replace("git@github.com:", "https://github.com/")
                .removesuffix(".git")
            )
        except (GitError, IndexError):
            return None

except ImportError:

    def _get_default_git_branch() -> str:
        return "UNKNOWN"

    def _get_default_git_commit() -> str:
        return "UNKNOWN"

    def _get_default_git_repo_url_gitpython() -> str | None:
        return None


def _get_default_git_repo_url():
    gitpython = _get_default_git_repo_url_gitpython()
    return (
        "https://github.com/iFargle/headscale-webui" if gitpython is None else gitpython
    )


class Config(BaseSettings):
    """Headscale WebUI configuration.

    `env` arg means what is the environment variable called.
    """

    color: _LowerConstr = Field(
        "red",
        env="COLOR",
        description=(
            "Preferred color scheme. See the MaterializeCSS docs "
            "(https://materializecss.github.io/materialize/color.html#palette) for "
            'examples. Only set the "base" color, e.g., instead of `blue-gray '
            "darken-1` use `blue-gray`."
        ),
    )
    auth_type: AuthType = Field(
        AuthType.BASIC,
        env="AUTH_TYPE",
        description="Authentication type.",
    )
    log_level_name: str = Field(
        "INFO",
        env="LOG_LEVEL",
        description=(
            'Logger level. If "DEBUG", Flask debug mode is activated, so don\'t use it '
            "in production."
        ),
    )
    debug_mode: bool = Field(
        False,
        env="DEBUG_MODE",
        description="Enable Flask debug mode.",
    )
    # TODO: Use user's locale to present datetime, not from server-side constant.
    timezone: ZoneInfo = Field(
        "UTC",
        env="TZ",
        description='Default time zone in IANA format. Example: "Asia/Tokyo".',
    )
    key: str = Field(
        env="KEY",
        description=(
            "Encryption key. Set this to a random value generated from "
            "`openssl rand -base64 32`."
        ),
    )

    app_version: str = Field(
        default_factory=_get_version_from_package,
        env="APP_VERSION",
        description="Application version. Should be set by Docker.",
    )
    build_date: str = Field(
        default_factory=str(datetime.now),
        env="BUILD_DATE",
        description="Application build date. Should be set by Docker.",
    )
    git_branch: str = Field(
        default_factory=_get_default_git_branch,
        env="GIT_BRANCH",
        description="Application git branch. Should be set by Docker.",
    )
    git_commit: str = Field(
        default_factory=_get_default_git_commit,
        env="GIT_COMMIT",
        description="Application git commit. Should be set by Docker.",
    )
    git_repo_url: AnyUrl = Field(
        default_factory=_get_default_git_repo_url,
        env="GIT_REPO_URL",
        description=(
            "Application git repository URL. "
            "Set automatically either to local or default repository."
        ),
    )

    # TODO: Autogenerate in headscale_api.
    hs_version: str = Field(
        "UNKNOWN",
        env="HS_VERSION",
        description=(
            "Version of Headscale this is compatible with. Should be set by Docker."
        ),
    )
    hs_server: AnyUrl = Field(
        "http://localhost:5000",
        env="HS_SERVER",
        description="The URL of your Headscale control server.",
    )
    hs_config_path: Path = Field(
        None,
        env="HS_CONFIG_PATH",
        description=(
            "Path to the Headscale configuration. Default paths are tried if not set."
        ),
    )

    domain_name: AnyUrl = Field(
        "http://localhost:5000",
        env="DOMAIN_NAME",
        description="Base domain name of the Headscale WebUI.",
    )
    base_path: str = Field(
        "",
        env="SCRIPT_NAME",
        description=(
            'The "Base Path" for hosting. For example, if you want to host on '
            "http://example.com/admin, set this to `/admin`, otherwise remove this "
            "variable entirely."
        ),
    )

    app_data_dir: Path = Field(
        Path("/data"),
        env="APP_DATA_DIR",
        description="Application data path.",
    )

    @validator("auth_type", pre=True)
    @classmethod
    def validate_auth_type(cls, value: Any):
        """Validate AUTH_TYPE so that it accepts more valid values."""
        value = str(value).lower()
        if value == "":
            return AuthType.BASIC
        return AuthType(value)

    @validator("log_level_name")
    @classmethod
    def validate_log_level_name(cls, value: Any):
        """Validate log_level_name field.

        Check if matches allowed log level from logging Python module.
        """
        assert isinstance(value, str)
        value = value.upper()
        allowed_levels = getLevelNamesMapping()
        if value not in allowed_levels:
            raise ValueError(
                f'Unkown log level "{value}". Select from: '
                + ", ".join(allowed_levels.keys())
            )
        return value

    @validator("timezone", pre=True)
    @classmethod
    def validate_timezone(cls, value: Any):
        """Validate and parse timezone information."""
        try:
            return ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError(f"Timezone {value} is invalid: {error}") from error

    @validator("hs_config_path", pre=True)
    @classmethod
    def validate_hs_config_path(cls, value: Any):
        """Validate Headscale configuration path.

        If none is given, some default paths that Headscale itself is using for lookup
        are searched.
        """
        if value is None:
            search_base = ["/etc/headscale", Path.home() / ".headscale"]
            suffixes = ["yml", "yaml", "json"]
        else:
            assert isinstance(value, (str, Path))
            search_base = [value]
            suffixes = [""]

        for base, suffix in itertools.product(search_base, suffixes):
            cur_path = f"{base}/config.{suffix}"
            if os.access(cur_path, os.R_OK):
                return cur_path

        raise InitCheckError(
            InitCheckErrorModel(
                "Headscale configuration read failed.",
                "Please ensure your headscale configuration file resides in "
                '/etc/headscale or in ~/.headscale and is named "config.yaml", '
                '"config.yml" or "config.json".',
            )
        )

    @validator("base_path")
    @classmethod
    def validate_base_path(cls, value: Any):
        """Validate base path."""
        assert isinstance(value, str)
        if value == "/":
            return ""
        return value

    @validator("app_data_dir")
    @classmethod
    def validate_app_data_dir(cls, value: Path):
        """Validate application data format and basic filesystem access."""
        err = InitCheckError()

        if not os.access(value, os.R_OK):
            err.append_error(
                InitCheckErrorModel(
                    f"Data ({value}) folder not readable.",
                    f'"{value}" is not readable. Please ensure your permissions are '
                    "correct. Data should be readable by UID/GID 1000:1000.",
                )
            )

        if not os.access(value, os.W_OK):
            err.append_error(
                InitCheckErrorModel(
                    f"Data ({value}) folder not writable.",
                    f'"{value}" is not writable. Please ensure your permissions are '
                    "correct. Data should be writable by UID/GID 1000:1000.",
                )
            )

        if not os.access(value, os.X_OK):
            err.append_error(
                InitCheckErrorModel(
                    f"Data ({value}) folder not executable.",
                    f'"{value}" is not executable. Please ensure your permissions are '
                    "correct. Data should be executable by UID/GID 1000:1000.",
                )
            )

        key_file = value / "key.txt"
        if key_file.exists():
            if not os.access(key_file, os.R_OK):
                err.append_error(
                    InitCheckErrorModel(
                        f"Key file ({key_file}) not readable.",
                        f'"{key_file}" is not readable. Please ensure your permissions '
                        "are correct. It should be readable by UID/GID 1000:1000.",
                    )
                )

            if not os.access(key_file, os.W_OK):
                err.append_error(
                    InitCheckErrorModel(
                        f"Key file ({key_file}) not writable.",
                        f'"{key_file}" is not writable. Please ensure your permissions '
                        "are correct. It should be writable by UID/GID 1000:1000.",
                    )
                )

        if err.errors is not None:
            raise err

        return value

    @property
    def log_level(self) -> int:
        """Get integer log level."""
        return getLevelNamesMapping()[self.log_level_name]

    @property
    def color_nav(self):
        """Get navigation color."""
        return f"{self.color} darken-1"

    @property
    def color_btn(self):
        """Get button color."""
        return f"{self.color} darken-3"

    @property
    def key_file(self):
        """Get key file path."""
        return self.app_data_dir / "key.txt"
