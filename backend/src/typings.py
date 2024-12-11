from typing import NotRequired, TypedDict


class UserInput(TypedDict):
    layers: NotRequired[str]
    connParams: NotRequired[str]
