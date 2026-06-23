import uuid
from app.core.db import get_db
from .domain import Language, Theme, Tour, TourEvents, TourPhoto, TourStop, TourWeeklySlot, TourReservation

class ToursDAO:

    @staticmethod
    def get_tour_by_id(tour_id: str):
        db = get_db()

        row = db.execute(
            "SELECT * FROM tours WHERE id = ?",
            (tour_id,)
        ).fetchone()

        return Tour.from_row(row)
    
    def get_public_tour_by_id(tour_id: str):
        db = get_db()

        row = db.execute(
            """
            SELECT *
            FROM tours
            WHERE id = ?
            AND is_deleted = 0
            """,
            (tour_id,)
        ).fetchone()

        return Tour.from_row(row)
    
    @staticmethod
    def add_tour(tour: Tour):
        db = get_db()

        tour_id = str(uuid.uuid4())
        db.execute(
            """
            INSERT INTO tours (id, guide_id, theme_id, language_id, title, description, meeting_point, duration, max_participants, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """,
            (tour_id, tour.guide_id, tour.theme_id, tour.language_id, tour.title, tour.description, tour.meeting_point, tour.duration, tour.max_participants)
        )
        db.commit()
        return tour_id
    
    @staticmethod
    def update_tour(tour: Tour):
        db = get_db()

        db.execute(
            """
            UPDATE tours
            SET theme_id = ?, language_id = ?, title = ?, description = ?, meeting_point = ?, duration = ?, max_participants = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (tour.theme_id, tour.language_id, tour.title, tour.description, tour.meeting_point, tour.duration, tour.max_participants, tour.id)
        )
        db.commit()
    
    @staticmethod
    def soft_delete_tour(tour_id: str):
        db = get_db()

        db.execute(
            """
            UPDATE tours
            SET is_deleted = 1, updated_at = datetime('now')
            WHERE id = ?
            """,
            (tour_id,)
        )
        db.commit()

    @staticmethod
    def list_tours_by_guide(guide_id: str):
        db = get_db()

        rows = db.execute(
            "SELECT * FROM tours WHERE guide_id = ? AND is_deleted = 0",
            (guide_id,)
        ).fetchall()

        return [Tour.from_row(row) for row in rows]
    
    @staticmethod
    def list_all_tours(limit: int = 20, offset: int = 0):
        db = get_db()

        rows = db.execute(
            "SELECT * FROM tours WHERE is_deleted = 0 ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        ).fetchall()
        return [Tour.from_row(row) for row in rows]
    
    @staticmethod
    def count_all_active_tours():
        db = get_db()

        row = db.execute(
            """
            SELECT COUNT(*) AS total
            FROM tours
            WHERE is_deleted = 0
            """
        ).fetchone()

        return int(row["total"])


    @staticmethod
    def count_tours_by_guide(guide_id: str):
        db = get_db()

        row = db.execute(
            """
            SELECT COUNT(*) AS total
            FROM tours
            WHERE guide_id = ?
            AND is_deleted = 0
            """,
            (guide_id,)
        ).fetchone()

        return int(row["total"])
    


class TourPhotosDAO:

    @staticmethod
    def get_photo_by_id(photo_id: str):
        db = get_db()

        row = db.execute(
            "SELECT * FROM tour_photos WHERE id = ?",
            (photo_id,)
        ).fetchone()

        return TourPhoto.from_row(row)

    @staticmethod
    def add_photo(tour_id: str, filename: str):
        db = get_db()

        photo_id = str(uuid.uuid4())
        db.execute(
            """
            INSERT INTO tour_photos (id, tour_id, filename, created_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (photo_id, tour_id, filename)
        )
        db.commit()
        return photo_id

    @staticmethod
    def delete_photo(photo_id: str):
        db = get_db()

        db.execute(
            "DELETE FROM tour_photos WHERE id = ?",
            (photo_id,)
        )
        db.commit()

    @staticmethod
    def list_photos_by_tour(tour_id: str):
        db = get_db()

        rows = db.execute(
            "SELECT * FROM tour_photos WHERE tour_id = ? ORDER BY created_at DESC",
            (tour_id,)
        ).fetchall()

        return [TourPhoto.from_row(row) for row in rows]
    
    


class TourStopsDAO:

    @staticmethod
    def get_stop_by_id(stop_id: str):
        db = get_db()

        row = db.execute(
            "SELECT * FROM tour_stops WHERE id = ?",
            (stop_id,)
        ).fetchone()

        return TourStop.from_row(row)

    @staticmethod
    def add_stop(tour_id: str, stop: TourStop):
        db = get_db()

        stop_id = str(uuid.uuid4())
        db.execute(
            """
            INSERT INTO tour_stops (id, tour_id, stop_name, stop_order, latitude, longitude, description, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (stop_id, tour_id, stop.stop_name, stop.stop_order, stop.latitude, stop.longitude, stop.description)
        )
        db.commit()
        return stop_id

    @staticmethod
    def update_stop(stop: TourStop):
        db = get_db()

        db.execute(
            """
            UPDATE tour_stops
            SET stop_name = ?, stop_order = ?, latitude = ?, longitude = ?, description = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (stop.stop_name, stop.stop_order, stop.latitude, stop.longitude, stop.description, stop.id)
        )
        db.commit()

    @staticmethod
    def delete_stop(stop_id: str):
        db = get_db()

        db.execute(
            "DELETE FROM tour_stops WHERE id = ?",
            (stop_id,)
        )
        db.commit()

    @staticmethod
    def list_stops_by_tour(tour_id: str):
        db = get_db()

        rows = db.execute(
            "SELECT * FROM tour_stops WHERE tour_id = ? ORDER BY stop_order ASC",
            (tour_id,)
        ).fetchall()

        return [TourStop.from_row(row) for row in rows]

    @staticmethod
    def replace_stops_for_tour(tour_id: str, stop_items: list[dict]) -> bool:
        db = get_db()

        try:
            db.execute(
                "DELETE FROM tour_stops WHERE tour_id = ?",
                (tour_id,)
            )

            for item in stop_items:
                stop_id = str(uuid.uuid4())

                db.execute(
                    """
                    INSERT INTO tour_stops
                    (id, tour_id, stop_name, stop_order, latitude, longitude, description, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """,
                    (
                        stop_id,
                        tour_id,
                        item["stop_name"],
                        item["stop_order"],
                        None,
                        None,
                        item["description"]
                    )
                )

            db.commit()
            return True

        except Exception as e:
            print(f"Errore DB durante aggiornamento stops: {e}")
            db.rollback()
            return False
    

class TourWeeklySlotsDAO:

    @staticmethod
    def get_slot_by_id(slot_id: int):
        db = get_db()

        row = db.execute(
            "SELECT * FROM tour_weekly_slots WHERE id = ?",
            (slot_id,)
        ).fetchone()

        return TourWeeklySlot.from_row(row)

    @staticmethod
    def add_slot(tour_id: str, slot: TourWeeklySlot):
        db = get_db()

        cursor = db.execute(
            """
            INSERT INTO tour_weekly_slots (tour_id, day_of_week, start_time, created_at, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (tour_id, slot.day_of_week, slot.start_time)
        )
        db.commit()
        return cursor.lastrowid

    @staticmethod
    def update_slot(slot: TourWeeklySlot):
        db = get_db()

        db.execute(
            """
            UPDATE tour_weekly_slots
            SET day_of_week = ?, start_time = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (slot.day_of_week, slot.start_time, slot.id)
        )
        db.commit()

    @staticmethod
    def delete_slot(slot_id: int):
        db = get_db()

        db.execute(
            "DELETE FROM tour_weekly_slots WHERE id = ?",
            (slot_id,)
        )
        db.commit()

    @staticmethod
    def list_slots_by_tour(tour_id: str):
        db = get_db()

        rows = db.execute(
            """
            SELECT *
            FROM tour_weekly_slots
            WHERE tour_id = ?
            ORDER BY day_of_week ASC, start_time ASC
            """,
            (tour_id,)
        ).fetchall()

        return [TourWeeklySlot.from_row(row) for row in rows]

    @staticmethod
    def delete_slots_by_tour(tour_id: str):
        db = get_db()

        db.execute(
            "DELETE FROM tour_weekly_slots WHERE tour_id = ?",
            (tour_id,)
        )

        db.commit()


    @staticmethod
    def replace_slots_for_tour(tour_id: str, schedule_items: list[dict]):
        db = get_db()
        try:
            db.execute(
                "DELETE FROM tour_weekly_slots WHERE tour_id = ?",
                (tour_id,)
            )

            for item in schedule_items:
                db.execute(
                    """
                    INSERT INTO tour_weekly_slots 
                    (tour_id, day_of_week, start_time, created_at, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """,
                    (
                        tour_id,
                        item["day_of_week"],
                        item["start_time"]
                    )
                )

            db.commit()
            return True
        except Exception as e:
            print(f"Errore DB durante aggiornamento schedule: {e}")
            db.rollback()
            return False
        
    

class TourEventsDAO:

    @staticmethod
    def get_event_by_id(event_id: str):
        db = get_db()

        row = db.execute(
            "SELECT * FROM tour_events WHERE id = ?",
            (event_id,)
        ).fetchone()

        return TourEvents.from_row(row)

    @staticmethod
    def get_event_by_occurrence(tour_id: str, event_date: str, start_time: str):
        db = get_db()

        row = db.execute(
            """
            SELECT *
            FROM tour_events
            WHERE tour_id = ?
              AND event_date = ?
              AND start_time = ?
            """,
            (tour_id, event_date, start_time)
        ).fetchone()

        return TourEvents.from_row(row)

    @staticmethod
    def create_event_for_booking(tour_id: str, event_date: str, start_time: str):
        db = get_db()

        event_id = str(uuid.uuid4())

        db.execute(
            """
            INSERT INTO tour_events
            (
                id,
                tour_id,
                event_date,
                start_time,
                status,
                actual_participants,
                evidence_photo,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                event_id,
                tour_id,
                event_date,
                start_time,
                "scheduled",
                0,
                None
            )
        )

        return event_id

    @staticmethod
    def list_events_by_tour(tour_id: str):
        db = get_db()

        rows = db.execute(
            """
            SELECT *
            FROM tour_events
            WHERE tour_id = ?
            ORDER BY event_date ASC, start_time ASC
            """,
            (tour_id,)
        ).fetchall()

        return [TourEvents.from_row(row) for row in rows]

    @staticmethod
    def add_event(event: TourEvents):
        db = get_db()

        event_id = str(uuid.uuid4())

        actual_participants = getattr(event, "actual_participants", 0)
        evidence_photo = getattr(event, "evidence_photo", None)

        db.execute(
            """
            INSERT INTO tour_events
            (
                id,
                tour_id,
                event_date,
                start_time,
                status,
                actual_participants,
                evidence_photo,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                event_id,
                event.tour_id,
                event.event_date,
                event.start_time,
                event.status,
                actual_participants,
                evidence_photo
            )
        )

        db.commit()
        return event_id

    @staticmethod
    def update_event(event: TourEvents):
        db = get_db()

        actual_participants = getattr(event, "actual_participants", 0)
        evidence_photo = getattr(event, "evidence_photo", None)

        db.execute(
            """
            UPDATE tour_events
            SET event_date = ?,
                start_time = ?,
                status = ?,
                actual_participants = ?,
                evidence_photo = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                event.event_date,
                event.start_time,
                event.status,
                actual_participants,
                evidence_photo,
                event.id
            )
        )

        db.commit()

    @staticmethod
    def update_actual_participants(event_id: str):
        db = get_db()

        db.execute(
            """
            UPDATE tour_events
            SET actual_participants = (
                SELECT COALESCE(SUM(total_people), 0)
                FROM tour_reservations
                WHERE event_id = ?
                  AND status = 'active'
            ),
            updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (event_id, event_id)
        )

    @staticmethod
    def delete_event(event_id: str):
        db = get_db()

        db.execute(
            "DELETE FROM tour_events WHERE id = ?",
            (event_id,)
        )

        db.commit()

    @staticmethod
    def list_events_by_guide(guide_id: str):
        db = get_db()

        rows = db.execute(
            """
            SELECT te.*
            FROM tour_events te
            JOIN tours t ON te.tour_id = t.id
            WHERE t.guide_id = ?
            ORDER BY te.event_date DESC, te.start_time DESC
            """,
            (guide_id,)
        ).fetchall()

        return [TourEvents.from_row(row) for row in rows]
    

    @staticmethod
    def complete_event_with_evidence_photo(event_id: str, evidence_photo: str):
        db = get_db()

        db.execute(
            """
            UPDATE tour_events
            SET status = 'completed',
                evidence_photo = ?,
                actual_participants = (
                    SELECT COALESCE(SUM(total_people), 0)
                    FROM tour_reservations
                    WHERE event_id = ?
                    AND status = 'active'
                ),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (evidence_photo, event_id, event_id)
        )

        db.commit()

    
class ThemesDao:

    @staticmethod
    def list_all_themes():
        db = get_db()

        rows = db.execute(
            "SELECT * FROM themes ORDER BY name ASC"
        ).fetchall()

        return [Theme.from_row(row) for row in rows]
    
    @staticmethod
    def get_theme_by_id(theme_id: int):
        db = get_db()

        row = db.execute(
            "SELECT * FROM themes WHERE id = ?",
            (theme_id,)
        ).fetchone()

        return Theme.from_row(row)
    

class LanguagesDAO:   
    @staticmethod
    def list_all_languages():
        db = get_db()

        rows = db.execute(
            "SELECT * FROM languages ORDER BY name ASC"
        ).fetchall()

        return [Language.from_row(row) for row in rows]
    
    @staticmethod
    def get_language_by_id(language_id: int):
        db = get_db()

        row = db.execute(
            "SELECT * FROM languages WHERE id = ?",
            (language_id,)
        ).fetchone()

        return Language.from_row(row)
    
    @staticmethod
    def list_languages_by_guide(guide_id: str):
        db = get_db()

        rows = db.execute(
            """
            SELECT l.*
            FROM languages l
            JOIN guide_languages gl ON gl.language_id = l.id
            WHERE gl.guide_id = ?
            ORDER BY l.name ASC
            """,
            (guide_id,)
        ).fetchall()

        return [Language.from_row(row) for row in rows]

class ThemesDAO:

    @staticmethod
    def list_all_themes():
        db = get_db()

        rows = db.execute(
            "SELECT * FROM themes ORDER BY name ASC"
        ).fetchall()

        return [Theme.from_row(row) for row in rows]
    
    @staticmethod
    def get_theme_by_id(theme_id: int):
        db = get_db()

        row = db.execute(
            "SELECT * FROM themes WHERE id = ?",
            (theme_id,)
        ).fetchone()

        return Theme.from_row(row)
    

class TourReservationsDAO:

    @staticmethod
    def get_reservation_by_id(reservation_id: str):
        db = get_db()

        row = db.execute(
            """
            SELECT *
            FROM tour_reservations
            WHERE id = ?
            """,
            (reservation_id,)
        ).fetchone()

        return TourReservation.from_row(row)
    
    @staticmethod
    def has_active_reservation_by_event_and_participant(event_id: str, participant_id: str):
        db = get_db()

        row = db.execute(
            """
            SELECT id
            FROM tour_reservations
            WHERE event_id = ?
            AND participant_id = ?
            AND status = 'active'
            LIMIT 1
            """,
            (event_id, participant_id)
        ).fetchone()

        return row is not None

    @staticmethod
    def get_reservation_by_idempotency_key(idempotency_key: str):
        db = get_db()

        row = db.execute(
            """
            SELECT *
            FROM tour_reservations
            WHERE idempotency_key = ?
            """,
            (idempotency_key,)
        ).fetchone()

        return TourReservation.from_row(row)

    @staticmethod
    def get_active_reservation_by_event_and_participant(event_id: str, participant_id: str):
        db = get_db()

        row = db.execute(
            """
            SELECT *
            FROM tour_reservations
            WHERE event_id = ?
              AND participant_id = ?
              AND status = 'active'
            """,
            (event_id, participant_id)
        ).fetchone()

        return TourReservation.from_row(row)

    @staticmethod
    def count_reserved_people(event_id: str):
        db = get_db()

        row = db.execute(
            """
            SELECT COALESCE(SUM(total_people), 0) AS total
            FROM tour_reservations
            WHERE event_id = ?
              AND status = 'active'
            """,
            (event_id,)
        ).fetchone()

        return int(row["total"])

    @staticmethod
    def list_reservations_by_event(event_id: str):
        db = get_db()

        rows = db.execute(
            """
            SELECT *
            FROM tour_reservations
            WHERE event_id = ?
            ORDER BY created_at ASC
            """,
            (event_id,)
        ).fetchall()

        return [TourReservation.from_row(row) for row in rows]

    @staticmethod
    def add_reservation(
        event_id: str,
        participant_id: str,
        total_people: int,
        additional_names: str,
        idempotency_key: str
    ):
        db = get_db()

        reservation_id = str(uuid.uuid4())

        db.execute(
            """
            INSERT INTO tour_reservations
            (
                id,
                event_id,
                participant_id,
                idempotency_key,
                total_people,
                additional_names,
                reminder_sent,
                is_checked_in,
                status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 0, 0, 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                reservation_id,
                event_id,
                participant_id,
                idempotency_key,
                total_people,
                additional_names
            )
        )

        return reservation_id

    @staticmethod
    def cancel_reservation(reservation_id: str):
        db = get_db()

        db.execute(
            """
            UPDATE tour_reservations
            SET status = 'cancelled',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (reservation_id,)
        )

    @staticmethod
    def list_reservations_by_participant(participant_id: str):
        db = get_db()

        rows = db.execute(
            """
            SELECT *
            FROM tour_reservations
            WHERE participant_id = ?
            ORDER BY created_at DESC
            """,
            (participant_id,)
        ).fetchall()

        return [TourReservation.from_row(row) for row in rows]
    

    @staticmethod
    def count_all_reservations():
        db = get_db()

        row = db.execute(
            """
            SELECT COUNT(*) AS total
            FROM tour_reservations
            """
        ).fetchone()

        return int(row["total"])


    @staticmethod
    def count_reservations_by_tour(tour_id: str):
        db = get_db()

        row = db.execute(
            """
            SELECT COUNT(tr.id) AS total
            FROM tour_reservations tr
            JOIN tour_events te ON tr.event_id = te.id
            WHERE te.tour_id = ?
            """,
            (tour_id,)
        ).fetchone()

        return int(row["total"])


    @staticmethod
    def count_reservations_by_language():
        db = get_db()

        rows = db.execute(
            """
            SELECT
                l.id AS language_id,
                l.name AS language_name,
                COUNT(tr.id) AS reservations_count
            FROM languages l
            LEFT JOIN tours t
                ON t.language_id = l.id
                AND t.is_deleted = 0
            LEFT JOIN tour_events te
                ON te.tour_id = t.id
            LEFT JOIN tour_reservations tr
                ON tr.event_id = te.id
            GROUP BY l.id, l.name
            ORDER BY reservations_count DESC, l.name ASC
            """
        ).fetchall()

        return rows
    

