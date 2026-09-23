from sqlalchemy import Enum

import app.models.catalog
import app.models.contract
import app.models.member
import app.models.organization
import app.models.reservation
import app.models.scheduling
import app.models.staff
import app.models.store
import app.models.user_account
from app.models.base import Base


def test_enum_columns_store_python_enum_values() -> None:
    enum_columns = [
        column
        for table in Base.metadata.tables.values()
        for column in table.columns
        if isinstance(column.type, Enum)
    ]

    assert enum_columns
    for column in enum_columns:
        assert column.type.enums == [
            member.value for member in column.type.enum_class
        ]
