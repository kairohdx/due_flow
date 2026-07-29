from datetime import date, datetime

from fastapi import HTTPException, status


def validate_range(
    start: date | datetime | None,
    end: date | datetime | None,
) -> None:
    if start is not None and end is not None and start > end:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="o início do período não pode ser posterior ao fim",
        )
