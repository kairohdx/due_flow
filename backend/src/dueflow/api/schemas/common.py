from math import ceil
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, Field, StringConstraints

NonEmptyName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=160),
]
NonEmptyDescription = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]

PageItem = TypeVar("PageItem")


class Page(BaseModel, Generic[PageItem]):
    items: list[PageItem]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=25)
    total: int = Field(ge=0)
    pages: int = Field(ge=0)

    @classmethod
    def create(
        cls,
        *,
        items: list[PageItem],
        page: int,
        page_size: int,
        total: int,
    ) -> "Page[PageItem]":
        return cls(
            items=items,
            page=page,
            page_size=page_size,
            total=total,
            pages=ceil(total / page_size) if total else 0,
        )
