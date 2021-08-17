from datetime import timedelta

import pytest
import pendulum
from pendulum import datetime, now
from pydantic import ValidationError

from prefect.orion.schemas.schedules import (
    CronSchedule,
    IntervalSchedule,
    ScheduleAdjustments,
    ScheduleFilters,
)


class TestCreateIntervalSchedule:
    def test_interval_is_required(self):
        with pytest.raises(ValidationError, match="(field required)"):
            IntervalSchedule()

    @pytest.mark.parametrize("minutes", [-1, 0])
    def test_interval_must_be_positive(self, minutes):
        with pytest.raises(ValidationError, match="(interval must be positive)"):
            IntervalSchedule(interval=timedelta(minutes=minutes))

    def test_default_anchor(self):
        schedule = IntervalSchedule(interval=timedelta(days=1))
        assert schedule.anchor_date == datetime(2020, 1, 1, tz="UTC")

    def test_default_anchor_respects_timezone(self):
        schedule = IntervalSchedule(interval=timedelta(days=1), timezone="EST")
        assert schedule.anchor_date == datetime(2020, 1, 1, tz="EST")

    def test_anchor(self):
        dt = now()
        schedule = IntervalSchedule(interval=timedelta(days=1), anchor_date=dt)
        assert schedule.anchor_date == dt

    def test_cant_supply_timezone_and_anchor(self):
        with pytest.raises(ValidationError, match="(anchor date or a timezone)"):
            IntervalSchedule(
                interval=timedelta(days=1), timezone="EST", anchor_date=now()
            )

    def test_invalid_timezone(self):
        with pytest.raises(ValidationError, match="(Invalid timezone)"):
            IntervalSchedule(interval=timedelta(days=1), timezone="fake")


class TestCreateScheduleFilters:
    @pytest.mark.parametrize("x", [[], [1], [3, 6, 9, 12]])
    def test_valid_months(self, x):
        schedule = ScheduleFilters(months=x)
        assert schedule.months == set(x)

    @pytest.mark.parametrize("x", [[-1], 1, [0], [3, 13]])
    def test_invalid_months(self, x):
        with pytest.raises(ValidationError):
            ScheduleFilters(months=x)

    @pytest.mark.parametrize("x", [[], [1], [15, 31], [-1], [-1, 1], [-28]])
    def test_valid_days_of_month(self, x):
        schedule = ScheduleFilters(days_of_month=x)
        assert schedule.days_of_month == set(x)

    @pytest.mark.parametrize("x", [1, [0], [-32, 1], [1, 32]])
    def test_invalid_days_of_month(self, x):
        with pytest.raises(ValidationError):
            ScheduleFilters(days_of_month=x)

    @pytest.mark.parametrize("x", [[], [0], [0, 1, 2, 3, 4]])
    def test_valid_days_of_week(self, x):
        schedule = ScheduleFilters(days_of_week=x)
        assert schedule.days_of_week == set(x)

    @pytest.mark.parametrize("x", [[-1], 1, [3, 7]])
    def test_invalid_days_of_week(self, x):
        with pytest.raises(ValidationError):
            ScheduleFilters(days_of_week=x)

    @pytest.mark.parametrize("x", [[], [0], [0, 1, 2, 3, 4]])
    def test_valid_hours_of_day(self, x):
        schedule = ScheduleFilters(hours_of_day=x)
        assert schedule.hours_of_day == set(x)

    @pytest.mark.parametrize("x", [[-1], 1, [1, 24]])
    def test_invalid_hours_of_day(self, x):
        with pytest.raises(ValidationError):
            ScheduleFilters(hours_of_day=x)

    @pytest.mark.parametrize("x", [[], [0], [0, 1, 2, 3, 4]])
    def test_valid_minutes_of_hour(self, x):
        schedule = ScheduleFilters(minutes_of_hour=x)
        assert schedule.minutes_of_hour == set(x)

    @pytest.mark.parametrize("x", [[-1], 1, [3, 60]])
    def test_invalid_minutes_of_hour(self, x):
        with pytest.raises(ValidationError):
            ScheduleFilters(minutes_of_hour=x)


class TestIntervalSchedule:
    @pytest.mark.parametrize(
        "start_date",
        [datetime(2018, 1, 1), datetime(2021, 2, 2), datetime(2025, 3, 3)],
    )
    def test_get_dates_from_start_date(self, start_date):
        schedule = IntervalSchedule(
            interval=timedelta(days=1), anchor_date=datetime(2021, 1, 1)
        )
        dates = schedule.get_dates(n=5, start=start_date)
        assert dates == [start_date.add(days=i) for i in range(5)]

    @pytest.mark.parametrize(
        "start_date",
        [datetime(2018, 1, 1), datetime(2021, 2, 2), datetime(2025, 3, 3)],
    )
    def test_get_dates_from_start_date_with_timezone(self, start_date):
        schedule = IntervalSchedule(interval=timedelta(days=1), timezone="EST")
        dates = schedule.get_dates(n=5, start=start_date)
        assert dates == [start_date.add(days=i).set(tz="EST") for i in range(5)]

    @pytest.mark.parametrize("n", [1, 2, 5])
    def test_get_n_dates(self, n):
        schedule = IntervalSchedule(interval=timedelta(days=1))
        assert len(schedule.get_dates(n=n)) == n

    def test_get_dates_from_anchor(self):
        schedule = IntervalSchedule(
            interval=timedelta(days=1), anchor_date=datetime(2020, 2, 2, 23, 35)
        )
        dates = schedule.get_dates(n=5, start=datetime(2021, 7, 1))
        assert dates == [datetime(2021, 7, 1, 23, 35).add(days=i) for i in range(5)]

    def test_get_dates_from_future_anchor(self):
        schedule = IntervalSchedule(
            interval=timedelta(hours=17), anchor_date=datetime(2030, 2, 2, 5, 24)
        )
        dates = schedule.get_dates(n=5, start=datetime(2021, 7, 1))
        assert dates == [
            datetime(2021, 7, 1, 7, 24).add(hours=i * 17) for i in range(5)
        ]

    def test_months_filter(self):
        schedule = IntervalSchedule(
            interval=timedelta(days=10),
            filters=dict(months=[1, 3]),
        )
        dates = schedule.get_dates(n=10, start=datetime(2020, 1, 1))
        assert dates == [
            datetime(2020, 1, 1),
            datetime(2020, 1, 11),
            datetime(2020, 1, 21),
            datetime(2020, 1, 31),
            datetime(2020, 3, 1),
            datetime(2020, 3, 11),
            datetime(2020, 3, 21),
            datetime(2020, 3, 31),
            datetime(2021, 1, 5),
            datetime(2021, 1, 15),
        ]

    def test_days_of_month_filter(self):
        schedule = IntervalSchedule(
            interval=timedelta(days=1),
            filters=dict(
                months=[2, 4, 6, 8, 10, 12],
                days_of_month=[1, 5],
            ),
        )
        dates = schedule.get_dates(n=5, start=datetime(2021, 2, 2))
        assert dates == [
            datetime(2021, 2, 5),
            datetime(2021, 4, 1),
            datetime(2021, 4, 5),
            datetime(2021, 6, 1),
            datetime(2021, 6, 5),
        ]

    def test_negative_days_of_month_filter(self):
        schedule = IntervalSchedule(
            interval=timedelta(days=1),
            filters=dict(days_of_month=[1, -5]),
        )
        dates = schedule.get_dates(n=8, start=datetime(2021, 1, 1))
        assert dates == [
            datetime(2021, 1, 1),
            datetime(2021, 1, 27),
            datetime(2021, 2, 1),
            datetime(2021, 2, 24),
            datetime(2021, 3, 1),
            datetime(2021, 3, 27),
            datetime(2021, 4, 1),
            datetime(2021, 4, 26),
        ]

    def test_days_of_week_filter(self):
        schedule = IntervalSchedule(
            interval=timedelta(days=1),
            anchor_date=datetime(2021, 1, 1, 12),
            filters=dict(days_of_week=[2, 4]),
        )
        dates = schedule.get_dates(n=5, start=datetime(2021, 1, 1))
        assert dates == [
            datetime(2021, 1, 1, 12),
            datetime(2021, 1, 6, 12),
            datetime(2021, 1, 8, 12),
            datetime(2021, 1, 13, 12),
            datetime(2021, 1, 15, 12),
        ]

    def test_hours_of_day_filter(self):
        schedule = IntervalSchedule(
            interval=timedelta(hours=1),
            filters=dict(hours_of_day=[11, 12, 13]),
        )
        dates = schedule.get_dates(n=5, start=datetime(2021, 1, 1))
        assert dates == [
            datetime(2021, 1, 1, 11),
            datetime(2021, 1, 1, 12),
            datetime(2021, 1, 1, 13),
            datetime(2021, 1, 2, 11),
            datetime(2021, 1, 2, 12),
        ]

    def test_minutes_of_hour_filter(self):
        schedule = IntervalSchedule(
            interval=timedelta(minutes=5),
            filters=dict(minutes_of_hour=list(range(0, 15))),
        )
        dates = schedule.get_dates(n=5, start=datetime(2021, 1, 1))
        assert dates == [
            datetime(2021, 1, 1, 0),
            datetime(2021, 1, 1, 0, 5),
            datetime(2021, 1, 1, 0, 10),
            datetime(2021, 1, 1, 1, 0),
            datetime(2021, 1, 1, 1, 5),
        ]


class TestCreateCronSchedule:
    def test_create_cron_schedule(self):
        schedule = CronSchedule(cron="5 4 * * *")
        assert schedule.cron == "5 4 * * *"

    def test_create_cron_schedule_with_timezone(self):
        schedule = CronSchedule(cron="5 4 * * *", timezone="EST")
        assert schedule.timezone == "EST"

    def test_invalid_timezone(self):
        with pytest.raises(ValidationError, match="(Invalid timezone)"):
            CronSchedule(interval=timedelta(days=1), timezone="fake")


class TestCronSchedule:
    every_day = "0 0 * * *"
    every_hour = "0 * * * *"

    def test_every_day(self):
        schedule = CronSchedule(cron=self.every_day)
        dates = schedule.get_dates(n=5, start=datetime(2021, 1, 1))
        assert dates == [datetime(2021, 1, 1).add(days=i) for i in range(5)]
        assert all(d.tz.name == "UTC" for d in dates)

    def test_every_hour(self):
        schedule = CronSchedule(cron=self.every_hour)
        dates = schedule.get_dates(n=5, start=datetime(2021, 1, 1))
        assert dates == [datetime(2021, 1, 1).add(hours=i) for i in range(5)]
        assert all(d.tz.name == "UTC" for d in dates)

    def test_every_day_with_timezone(self):
        schedule = CronSchedule(cron=self.every_hour, timezone="EST")
        dates = schedule.get_dates(n=5, start=datetime(2021, 1, 1))
        assert dates == [datetime(2021, 1, 1).add(hours=i) for i in range(5)]
        assert all(d.tz.name == "EST" for d in dates)

    def test_every_day_with_timezone_start(self):
        schedule = CronSchedule(cron=self.every_hour)
        dates = schedule.get_dates(n=5, start=datetime(2021, 1, 1).in_tz("EST"))
        assert dates == [datetime(2021, 1, 1).add(hours=i) for i in range(5)]
        assert all(d.tz.name == "EST" for d in dates)

    def test_n(self):
        schedule = CronSchedule(cron=self.every_day)
        dates = schedule.get_dates(n=10, start=datetime(2021, 1, 1))
        assert dates == [datetime(2021, 1, 1).add(days=i) for i in range(10)]

    def test_start_date(self):
        start_date = datetime(2025, 5, 5)
        schedule = CronSchedule(cron=self.every_day)
        dates = schedule.get_dates(n=10, start=start_date)
        assert dates == [start_date.add(days=i) for i in range(10)]


class TestIntervalClockDaylightSavingsTime:
    """
    Tests that DST boundaries are respected and also serialized appropriately

    If serialize = True, the schedule is serialized and deserialized to ensure that TZ info
    survives.
    """

    def test_interval_schedule_always_has_the_right_offset(self):
        """
        Tests the situation where a long duration has passed since the start date that crosses a DST boundary;
        for very short intervals this occasionally could result in "next" scheduled times that are in the past by one hour.
        """
        anchor_date = pendulum.from_timestamp(1582002945.964696).astimezone(
            pendulum.timezone("US/Pacific")
        )
        current_date = pendulum.from_timestamp(1593643144.233938).astimezone(
            pendulum.timezone("UTC")
        )
        s = IntervalSchedule(
            interval=timedelta(minutes=1, seconds=15), anchor_date=anchor_date
        )
        dates = s.get_dates(n=4, start=current_date)
        assert all(d > current_date for d in dates)

    def test_interval_schedule_hourly_daylight_savings_time_forward_with_UTC(self):
        """
        On 3/11/2018, at 2am, America/New_York switched clocks forward an hour.
        """
        dt = datetime(2018, 3, 10, 23, tz="America/New_York")
        s = IntervalSchedule(interval=timedelta(hours=1))
        dates = s.get_dates(n=5, start=dt)
        # skip 2am
        assert [d.in_tz("America/New_York").hour for d in dates] == [23, 0, 1, 3, 4]
        # constant hourly schedule in utc time
        assert [d.in_tz("UTC").hour for d in dates] == [4, 5, 6, 7, 8]

    def test_interval_schedule_hourly_daylight_savings_time_forward(self):
        """
        On 3/11/2018, at 2am, America/New_York switched clocks forward an hour.
        """
        dt = datetime(2018, 3, 10, 23, tz="America/New_York")
        s = IntervalSchedule(interval=timedelta(hours=1), timezone="America/New_York")
        dates = s.get_dates(n=5, start=dt)
        # skip 2am
        assert [d.in_tz("America/New_York").hour for d in dates] == [23, 0, 1, 3, 4]
        # constant hourly schedule in utc time
        assert [d.in_tz("UTC").hour for d in dates] == [4, 5, 6, 7, 8]

    def test_interval_schedule_hourly_daylight_savings_time_backward(self):
        """
        11/4/2018, at 2am, America/New_York switched clocks back an hour.
        """
        dt = datetime(2018, 11, 3, 23, tz="America/New_York")
        s = IntervalSchedule(interval=timedelta(hours=1), timezone="America/New_York")
        dates = s.get_dates(n=5, start=dt)
        # repeat the 1am run in local time
        assert [d.in_tz("America/New_York").hour for d in dates] == [23, 0, 1, 1, 2]
        # runs every hour UTC
        assert [d.in_tz("UTC").hour for d in dates] == [3, 4, 5, 6, 7]

    def test_interval_schedule_daily_start_daylight_savings_time_forward(self):
        """
        On 3/11/2018, at 2am, America/New_York switched clocks forward an hour.

        Confirm that a schedule for 9am America/New_York stays 9am through the switch.
        """
        dt = datetime(2018, 3, 8, 9, tz="America/New_York")
        s = IntervalSchedule(interval=timedelta(days=1), anchor_date=dt)
        dates = s.get_dates(n=5, start=dt)
        # constant 9am start
        assert [d.in_tz("America/New_York").hour for d in dates] == [9, 9, 9, 9, 9]
        # utc time shifts
        assert [d.in_tz("UTC").hour for d in dates] == [14, 14, 14, 13, 13]

    def test_interval_schedule_daily_start_daylight_savings_time_backward(self):
        """
        On 11/4/2018, at 2am, America/New_York switched clocks back an hour.

        Confirm that a schedule for 9am America/New_York stays 9am through the switch.
        """
        dt = datetime(2018, 11, 1, 9, tz="America/New_York")
        s = IntervalSchedule(interval=timedelta(days=1), anchor_date=dt)
        dates = s.get_dates(n=5, start=dt)
        # constant 9am start
        assert [d.in_tz("America/New_York").hour for d in dates] == [9, 9, 9, 9, 9]
        assert [d.in_tz("UTC").hour for d in dates] == [13, 13, 13, 14, 14]


class TestCronClockDaylightSavingsTime:
    """
    Tests that DST boundaries are respected
    """

    def test_cron_schedule_hourly_daylight_savings_time_forward_ignored_with_UTC(self):
        """
        On 3/11/2018, at 2am, America/New_York switched clocks forward an hour.
        """
        dt = datetime(2018, 3, 10, 23, tz="America/New_York")
        s = CronSchedule(cron="0 * * * *", timezone="America/New_York")
        dates = s.get_dates(n=5, start=dt)

        # skip 2am
        assert [d.in_tz("America/New_York").hour for d in dates] == [23, 0, 1, 3, 4]
        # constant hourly schedule in utc time
        assert [d.in_tz("UTC").hour for d in dates] == [4, 5, 6, 7, 8]

    def test_cron_schedule_hourly_daylight_savings_time_forward(self):
        """
        On 3/11/2018, at 2am, America/New_York switched clocks forward an hour.
        """
        dt = datetime(2018, 3, 10, 23, tz="America/New_York")
        s = CronSchedule(cron="0 * * * *", timezone="America/New_York")
        dates = s.get_dates(n=5, start=dt)

        # skip 2am
        assert [d.in_tz("America/New_York").hour for d in dates] == [23, 0, 1, 3, 4]
        # constant hourly schedule in utc time
        assert [d.in_tz("UTC").hour for d in dates] == [4, 5, 6, 7, 8]

    def test_cron_schedule_hourly_daylight_savings_time_backward(self):
        """
        11/4/2018, at 2am, America/New_York switched clocks back an hour.
        """
        dt = datetime(2018, 11, 3, 23, tz="America/New_York")
        s = CronSchedule(cron="0 * * * *", timezone="America/New_York")
        dates = s.get_dates(n=5, start=dt)

        # repeat the 1am run in local time
        assert [d.in_tz("America/New_York").hour for d in dates] == [23, 0, 1, 2, 3]
        # runs every hour UTC
        assert [d.in_tz("UTC").hour for d in dates] == [3, 4, 6, 7, 8]

    def test_cron_schedule_daily_start_daylight_savings_time_forward(self):
        """
        On 3/11/2018, at 2am, America/New_York switched clocks forward an hour.

        Confirm that a schedule for 9am America/New_York stays 9am through the switch.
        """
        dt = datetime(2018, 3, 8, 9, tz="America/New_York")
        s = CronSchedule(cron="0 9 * * *", timezone="America/New_York")
        dates = s.get_dates(n=5, start=dt)

        # constant 9am start
        assert [d.in_tz("America/New_York").hour for d in dates] == [9, 9, 9, 9, 9]
        # utc time shifts
        assert [d.in_tz("UTC").hour for d in dates] == [14, 14, 14, 13, 13]

    def test_cron_schedule_daily_start_daylight_savings_time_backward(self):
        """
        On 11/4/2018, at 2am, America/New_York switched clocks back an hour.

        Confirm that a schedule for 9am America/New_York stays 9am through the switch.
        """
        dt = datetime(2018, 11, 1, 9, tz="America/New_York")
        s = CronSchedule(cron="0 9 * * *", timezone="America/New_York")
        dates = s.get_dates(n=5, start=dt)

        # constant 9am start
        assert [d.in_tz("America/New_York").hour for d in dates] == [9, 9, 9, 9, 9]
        assert [d.in_tz("UTC").hour for d in dates] == [13, 13, 13, 14, 14]