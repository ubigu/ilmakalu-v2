from typing import Any

responses: dict[int | str, dict[str, Any]] = {
    400: {"description": "Bad Request"},
    500: {"description": "Internal Server Error"},
}
