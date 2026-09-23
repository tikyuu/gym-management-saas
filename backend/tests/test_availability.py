from datetime import date, datetime, time, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.api.v1.availability import available_slots
from app.models.reservation import Reservation
from app.models.scheduling import UnavailablePeriod, WorkShift


JAPAN_TIMEZONE = ZoneInfo("Asia/Tokyo")


def japanese_time(hour: int, minute: int = 0) -> datetime:
    return datetime(2030, 10, 10, hour, minute, tzinfo=JAPAN_TIMEZONE)


def slot_starts(slots) -> list[str]:
    return [slot.starts_at.strftime("%H:%M") for slot in slots]


def test_available_slots_require_a_free_trainer_and_member() -> None:
    member_id = uuid4()
    first_trainer_id = uuid4()
    second_trainer_id = uuid4()
    first_shift = WorkShift(
        id=uuid4(),
        staff_id=first_trainer_id,
        starts_at=japanese_time(9).astimezone(timezone.utc),
        ends_at=japanese_time(12).astimezone(timezone.utc),
    )
    second_shift = WorkShift(
        id=uuid4(),
        staff_id=second_trainer_id,
        starts_at=japanese_time(9).astimezone(timezone.utc),
        ends_at=japanese_time(12).astimezone(timezone.utc),
    )
    break_period = UnavailablePeriod(
        work_shift_id=first_shift.id,
        starts_at=japanese_time(10).astimezone(timezone.utc),
        ends_at=japanese_time(11).astimezone(timezone.utc),
    )
    booking = Reservation(
        member_id=uuid4(),
        staff_id=second_trainer_id,
        starts_at=japanese_time(10).astimezone(timezone.utc),
        ends_at=japanese_time(11).astimezone(timezone.utc),
    )
    arguments = {
        "business_hours": [(time(9), time(12))],
        "booking_interval_minutes": 30,
        "duration_minutes": 60,
        "target_date": date(2030, 10, 10),
        "shifts": [first_shift, second_shift],
        "unavailable_periods": [break_period],
        "member_id": member_id,
        "now": japanese_time(8),
    }

    assert slot_starts(available_slots(reservations=[booking], **arguments)) == [
        "09:00",
        "11:00",
    ]
    assert slot_starts(available_slots(reservations=[], **arguments)) == [
        "09:00",
        "09:30",
        "10:00",
        "10:30",
        "11:00",
    ]

    booking.member_id = member_id
    assert slot_starts(available_slots(reservations=[booking], **arguments)) == [
        "09:00",
        "11:00",
    ]


def test_available_slots_respect_opening_hours_and_current_time() -> None:
    shift = WorkShift(
        id=uuid4(),
        staff_id=uuid4(),
        starts_at=japanese_time(9).astimezone(timezone.utc).replace(tzinfo=None),
        ends_at=japanese_time(12).astimezone(timezone.utc).replace(tzinfo=None),
    )
    slots = available_slots(
        business_hours=[(time(9), time(10, 30)), (time(11), time(12))],
        booking_interval_minutes=30,
        duration_minutes=60,
        target_date=date(2030, 10, 10),
        shifts=[shift],
        unavailable_periods=[],
        reservations=[],
        member_id=uuid4(),
        now=japanese_time(9, 30),
    )
    assert slot_starts(slots) == ["11:00"]
