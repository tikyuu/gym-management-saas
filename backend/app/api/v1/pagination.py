from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel


Item = TypeVar("Item")


class Page(BaseModel, Generic[Item]):
    items: list[Item]
    next_cursor: UUID | None


def page(items: list[Item], limit: int) -> Page[Item]:
    visible = items[:limit]
    return Page(
        items=visible,
        next_cursor=getattr(visible[-1], "id") if len(items) > limit else None,
    )
