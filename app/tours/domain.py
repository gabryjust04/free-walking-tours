from dataclasses import dataclass


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
    actual_partecipants: str
    evicende_photos: str
    created_at: str
    updated_at: str

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
            actual_partecipants=row["actual_partecipants"],
            evicende_photos=row["evicende_photos"],
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
            created_at=row["created_at"],
            label=row["label"]
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
    production_photos: list[TourPhoto] = None
    stops: list[TourStop] = None
    weekly_slots: list[TourWeeklySlot] = None

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
            is_deleted=bool(row["is_deleted"]),
            theme=Theme.from_row(row),
            language=Language.from_row(row),
            production_photos=[TourPhoto.from_row(r) for r in row.get("production_photos", [])],
            stops=[TourStop.from_row(r) for r in row.get("stops", [])],
            weekly_slots=[TourWeeklySlot.from_row(r) for r in row.get("weekly_slots", [])]
        )


