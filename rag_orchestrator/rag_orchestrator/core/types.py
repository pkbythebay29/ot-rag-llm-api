from typing import TypedDict, Any


class ChatMessage(TypedDict):
    role: str
    content: str


class ChatResult(TypedDict, total=False):
    text: str
    usage: dict[str, int]
    raw: Any
