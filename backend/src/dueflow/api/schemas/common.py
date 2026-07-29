from typing import Annotated

from pydantic import StringConstraints

NonEmptyName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=160),
]
NonEmptyDescription = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]

