import sys

from dataclasses import dataclass
from .logger import logger


@dataclass(frozen=True)
class UpdateInfo:
    details: str
    state: str

    start: int = None
    party_size: list = None

    large_image: str = None
    large_text: str = None

    buttons: list[dict] = None


@dataclass(frozen=True)
class ActivityInfo:
    app_name: str
    method: str
    activity_priority: int
    # max_stays_idle
    data: UpdateInfo = None


class ActivitiesManager:
    current_activity_info = None

    ignore_activity_info = ActivityInfo(
        app_name="ActivitiesManager",
        method="ignore",
        activity_priority=-1,
    )

    # last_updated_at : datetime
    # thread check_last_apdated | while las_updated+current_activity_max_idle minute > now()
    def __init__(self, *raw_activities):
        self.activities = self.set_activities(*raw_activities)

    @staticmethod
    def set_activities(*raw_activities):
        activities = {}

        used_priorities = []
        for activity in raw_activities:
            if not isinstance(activity, Activity):
                logger.error(f"ActivitiesManager got wrong type: {type(activity)}. Must be Activity type")
                sys.exit(1)
            try:
                int(activity.priority)
            except ValueError:
                logger.error(f"Activity`s priority must be an integer")
                sys.exit(1)

            if activity.priority in used_priorities:
                logger.error(
                    f"ActivitiesManager already has priority {activity.priority}, Activity`s priority must be unique")
                sys.exit(1)

            used_priorities.append(activity.priority)
            activities[activity.activity_name] = activity

        logger.debug(f"Activities manager initialized with {len(activities)} activities")
        return activities

    def activity_handle(self, activity_name, method, info) -> ActivityInfo:
        new_activity_info = self.activities[activity_name].handle(method, info)

        result = self.process_activity_info(new_activity_info)
        return result

    def process_activity_info(self, activity_info) -> ActivityInfo:
        match activity_info.method:
            case "ignore":
                logger.debug("Got activity method 'ignore', proceed")
                response_activity_info = activity_info

            case "update":
                if not self.current_activity_info:
                    self.current_activity_info = activity_info
                    response_activity_info = activity_info

                    logger.debug("No current activity info, set new")

                elif activity_info.activity_priority <= self.current_activity_info.activity_priority:
                    self.current_activity_info = activity_info
                    response_activity_info = activity_info

                    logger.debug(
                        f"New activity has higher priority, updating current activity | activity_info : {activity_info}")

                else:
                    response_activity_info = self.ignore_activity_info
                    logger.debug("New activity info doesn't have higher priority, ignoring")

            case "clear":
                if not self.current_activity_info:
                    logger.warning("Attempt to clear, but no active activity, ignoring")
                    response_activity_info = self.ignore_activity_info

                elif activity_info.activity_priority == self.current_activity_info.activity_priority:
                    self.current_activity_info = None
                    response_activity_info = activity_info
                    logger.debug("Clearing current activity")

                else:
                    response_activity_info = self.ignore_activity_info
                    logger.debug("Can`t clear activity other than current, ignoring")

            case _:
                response_activity_info = self.ignore_activity_info
                logger.warning(
                    f"Wrong method '{activity_info.method}' in activity info, ignoring")

        return response_activity_info


class Activity:
    activity_name = NotImplemented
    start_stays_minutes = NotImplemented
    max_idle_minutes = NotImplemented
    main_rp_app_name = NotImplemented

    def __init__(self, priority=0):
        self.priority = priority

        self.started_at = None
        self.last_clean_call = None
        self.last_update_call = None

        self.handled_methods = {"clear": self._handle_clean,
                                "update": self._handle_update}

    def handle(self, method, data) -> ActivityInfo:
        logger.debug(f"Need to handle method : {method}")

        success, data = self.handled_methods[method](data)

        return ActivityInfo(
            activity_priority=self.priority,
            app_name=self.main_rp_app_name,

            method=method if success else "ignore",
            data=data
        )

    def _handle_update(self, data) -> (bool, UpdateInfo):
        raise NotImplementedError

    def _handle_clean(self, data) -> (bool, None):
        raise NotImplementedError