"""Helper functions used for formatting."""

from datetime import timedelta
from enum import StrEnum
from typing import Literal


def pretty_print_duration(
    duration: timedelta, delta_type: Literal["expiry", ""] = ""
):  # pylint: disable=too-many-return-statements
    """Print a duration in human-readable format."""
    days, seconds = duration.days, duration.seconds
    hours = days * 24 + seconds // 3600
    mins = (seconds % 3600) // 60
    secs = seconds % 60
    if delta_type == "expiry":
        if days > 730:
            return "in more than two years"
        if days > 365:
            return "in more than a year"
        if days > 0:
            return f"in {days} days" if days > 1 else f"in {days} day"
        if hours > 0:
            return f"in {hours} hours" if hours > 1 else f"in {hours} hour"
        if mins > 0:
            return f"in {mins} minutes" if mins > 1 else f"in {mins} minute"
        return f"in {secs} seconds" if secs >= 1 or secs == 0 else f"in {secs} second"

    if days > 730:
        return "over two years ago"
    if days > 365:
        return "over a year ago"
    if days > 0:
        return f"{days} days ago" if days > 1 else f"{days} day ago"
    if hours > 0:
        return f"{hours} hours ago" if hours > 1 else f"{hours} hour ago"
    if mins > 0:
        return f"{mins} minutes ago" if mins > 1 else f"{mins} minute ago"
    return f"{secs} seconds ago" if secs >= 1 or secs == 0 else f"{secs} second ago"


def text_color_duration(
    duration: timedelta,
):  # pylint: disable=too-many-return-statements
    """Print a color based on duration (imported as seconds)."""
    days, seconds = duration.days, duration.seconds
    hours = days * 24 + seconds // 3600
    mins = (seconds % 3600) // 60
    secs = seconds % 60
    if days > 30:
        return "grey-text                      "
    if days > 14:
        return "red-text         text-darken-2 "
    if days > 5:
        return "deep-orange-text text-lighten-1"
    if days > 1:
        return "deep-orange-text text-lighten-1"
    if hours > 12:
        return "orange-text                    "
    if hours > 1:
        return "orange-text      text-lighten-2"
    if hours == 1:
        return "yellow-text                    "
    if mins > 15:
        return "yellow-text      text-lighten-2"
    if mins > 5:
        return "green-text       text-lighten-3"
    if secs > 30:
        return "green-text       text-lighten-2"
    return "green-text                     "


def get_color(import_id: int, item_type: Literal["failover", "text", ""] = ""):
    """Get color for users/namespaces."""
    # Define the colors... Seems like a good number to start with
    match item_type:
        case "failover":
            colors = [
                "teal        lighten-1",
                "blue        lighten-1",
                "blue-grey   lighten-1",
                "indigo      lighten-2",
                "brown       lighten-1",
                "grey        lighten-1",
                "indigo      lighten-2",
                "deep-orange lighten-1",
                "yellow      lighten-2",
                "purple      lighten-2",
            ]
        case "text":
            colors = [
                "red-text         text-lighten-1",
                "teal-text        text-lighten-1",
                "blue-text        text-lighten-1",
                "blue-grey-text   text-lighten-1",
                "indigo-text      text-lighten-2",
                "green-text       text-lighten-1",
                "deep-orange-text text-lighten-1",
                "yellow-text      text-lighten-2",
                "purple-text      text-lighten-2",
                "indigo-text      text-lighten-2",
                "brown-text       text-lighten-1",
                "grey-text        text-lighten-1",
            ]
        case _:
            colors = [
                "red         lighten-1",
                "teal        lighten-1",
                "blue        lighten-1",
                "blue-grey   lighten-1",
                "indigo      lighten-2",
                "green       lighten-1",
                "deep-orange lighten-1",
                "yellow      lighten-2",
                "purple      lighten-2",
                "indigo      lighten-2",
                "brown       lighten-1",
                "grey        lighten-1",
            ]
    return colors[import_id % len(colors)]


class MessageErrorType(StrEnum):
    """Error type for `format_message()."""

    WARNING = "warning"
    SUCCESS = "success"
    ERROR = "error"
    INFORMATION = "information"


def format_message(error_type: MessageErrorType, title: str, message: str):
    """Render a "collection" as error/warning/info message."""
    content = '<ul class="collection"><li class="collection-item avatar">'

    match error_type:
        case MessageErrorType.WARNING:
            icon = '<i class="material-icons circle yellow">priority_high</i>'
            title = f'<span class="title">Warning - {title}</span>'
        case MessageErrorType.SUCCESS:
            icon = '<i class="material-icons circle green">check</i>'
            title = f'<span class="title">Success - {title}</span>'
        case MessageErrorType.ERROR:
            icon = '<i class="material-icons circle red">warning</i>'
            title = f'<span class="title">Error - {title}</span>'
        case MessageErrorType.INFORMATION:
            icon = '<i class="material-icons circle grey">help</i>'
            title = f'<span class="title">Information - {title}</span>'

    content += icon + title + message + "</li></ul>"

    return content
