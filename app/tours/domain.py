from dataclasses import dataclass, field


@dataclass
class TourPhoto:
    id: str
    tour_id: str
    filename: str

    @staticmethod
    def from_row(row):
        if row is None:
            return None

        return TourPhoto(
            id=row["id"],
            tour_id=row["tour_id"],
            filename=row["filename"]
        )


@dataclass
class TourStop:
    id: str
    stop_name: str
    stop_order: int
    latitude: float
    longitude: float
    description: str

    @staticmethod
    def from_row(row):
        if row is None:
            return None

        return TourStop(
            id=row["id"],
            stop_name=row["stop_name"],
            stop_order=row["stop_order"],
            latitude=row["latitude"],
            longitude=row["longitude"],
            description=row["description"]
        )


@dataclass
class TourWeeklySlot:
    id: int
    day_of_week: str
    start_time: str

    @staticmethod
    def from_row(row):
        if row is None:
            return None

        return TourWeeklySlot(
            id=row["id"],
            day_of_week=row["day_of_week"],
            start_time=row["start_time"]
        )


@dataclass
class TourEvents:
    id: str
    tour_id: str
    event_date: str
    start_time: str
    status: str
    actual_participants: int
    evidence_photo: str
    created_at: str
    updated_at: str
    tour: object = None

    @staticmethod    
    def from_row(row):
        if row is None:
            return None

        return TourEvents(
            id=row["id"],
            tour_id=row["tour_id"],
            event_date=row["event_date"],
            start_time=row["start_time"],
            status=row["status"],
            actual_participants=row["actual_participants"],
            evidence_photo=row["evidence_photo"],
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )


@dataclass
class Theme:
    id: int
    name: str
    slug: str
    icon: str
    created_at: str

    @staticmethod
    def from_row(row):
        if row is None:
            return None

        return Theme(
            id=row["id"],
            name=row["name"],
            slug=row["slug"],
            icon=row["icon"],
            created_at=row["created_at"]
        )


@dataclass
class Language:
    id: int
    name: str
    label: str
    created_at: str

    @staticmethod
    def from_row(row):
        if row is None:
            return None

        return Language(
            id=row["id"],
            name=row["name"],
            label=row["label"],
            created_at=row["created_at"]
        )


@dataclass
class Tour:
    id: str
    guide_id: str
    theme_id: int
    language_id: int
    title: str
    description: str
    meeting_point: str
    duration: int
    max_participants: int
    is_deleted: bool = False

    theme: Theme = None
    language: Language = None
    production_photos: list[TourPhoto] = field(default_factory=list)
    stops: list[TourStop] = field(default_factory=list)
    weekly_slots: list[TourWeeklySlot] = field(default_factory=list)

    @staticmethod
    def from_row(row):
        if row is None:
            return None

        return Tour(
            id=row["id"],
            guide_id=row["guide_id"],
            theme_id=row["theme_id"],
            language_id=row["language_id"],
            title=row["title"],
            description=row["description"],
            meeting_point=row["meeting_point"],
            duration=row["duration"],
            max_participants=row["max_participants"],
            is_deleted=bool(row["is_deleted"])
        )
    

@dataclass
class TourReservation:
    id: str
    event_id: str = None
    participant_id: str = None
    idempotency_key: str = None
    total_people: int = 1
    additional_names: str = None
    reminder_sent: int = 0
    is_checked_in: int = 0
    status: str = "active"
    created_at: str = None
    updated_at: str = None

    def from_row(row):
        if row is None:
            return None

        keys = row.keys()

        event_id = None

        if "event_id" in keys:
            event_id = row["event_id"]
        elif "tour_event_id" in keys:
            event_id = row["tour_event_id"]

        return TourReservation(
            id=row["id"],
            event_id=event_id,
            participant_id=row["participant_id"] if "participant_id" in keys else None,
            idempotency_key=row["idempotency_key"] if "idempotency_key" in keys else None,
            total_people=row["total_people"] if "total_people" in keys else 1,
            additional_names=row["additional_names"] if "additional_names" in keys else None,
            reminder_sent=row["reminder_sent"] if "reminder_sent" in keys else 0,
            is_checked_in=row["is_checked_in"] if "is_checked_in" in keys else 0,
            status=row["status"] if "status" in keys else "active",
            created_at=row["created_at"] if "created_at" in keys else None,
            updated_at=row["updated_at"] if "updated_at" in keys else None,
        )