import json
from datetime import date, datetime, timedelta

from db.database import get_db_connection, run_startup_migrations


DEMO_PASSWORD = "demo123"


def _case_brief(summary: str, legal_area: str, documents: list[str], next_steps: list[str]) -> dict:
    return {
        "case_summary": summary,
        "legal_area": legal_area,
        "key_entities": ["client", "counterparty"],
        "timeline": [
            "Issue first identified by the client.",
            "Client gathered preliminary records and communication.",
        ],
        "documents": documents,
        "recommended_next_steps": next_steps,
    }


def _ensure_user(cur, name: str, email: str, role: str, user_id: int | None = None) -> int:
    cur.execute("SELECT id FROM users WHERE LOWER(name) = LOWER(%s)", (name,))
    row = cur.fetchone()
    if row:
        cur.execute(
            """
            UPDATE users
            SET email = %s,
                password = %s,
                password_hash = %s,
                role = %s
            WHERE id = %s
            """,
            (email, DEMO_PASSWORD, DEMO_PASSWORD, role, row[0]),
        )
        return int(row[0])

    if user_id is None:
        cur.execute(
            """
            INSERT INTO users (name, email, password, password_hash, role)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (name, email, DEMO_PASSWORD, DEMO_PASSWORD, role),
        )
        return int(cur.fetchone()[0])

    cur.execute(
        """
        INSERT INTO users (id, name, email, password, password_hash, role)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (id)
        DO UPDATE SET
            name = EXCLUDED.name,
            email = EXCLUDED.email,
            password = EXCLUDED.password,
            password_hash = EXCLUDED.password_hash,
            role = EXCLUDED.role
        RETURNING id
        """,
        (user_id, name, email, DEMO_PASSWORD, DEMO_PASSWORD, role),
    )
    return int(cur.fetchone()[0])


def _select_seed_professionals(cur, required_count: int) -> list[tuple]:
    cur.execute(
        """
        SELECT p.id, p.name, COALESCE(p.city, 'Berlin'), COALESCE(p.category, 'General Legal')
        FROM professionals p
        LEFT JOIN users u ON u.id = p.id
        WHERE u.id IS NULL
        ORDER BY COALESCE(p.rating, 0) DESC, p.id ASC
        LIMIT %s
        """,
        (required_count,),
    )
    return cur.fetchall()


def _ensure_lawyer_profile(cur, lawyer_id: int, name: str, city: str, practice_areas: str, bio: str, availability_status: str, responsiveness_score: float) -> None:
    cur.execute(
        """
        INSERT INTO lawyer_profiles (
            lawyer_id, name, city, practice_areas, languages, experience_years, rating, bio,
            availability_status, response_time_hours, applications_sent, cases_accepted, responsiveness_score
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (lawyer_id)
        DO UPDATE SET
            name = EXCLUDED.name,
            city = EXCLUDED.city,
            practice_areas = EXCLUDED.practice_areas,
            languages = EXCLUDED.languages,
            experience_years = EXCLUDED.experience_years,
            rating = EXCLUDED.rating,
            bio = EXCLUDED.bio,
            availability_status = EXCLUDED.availability_status,
            response_time_hours = EXCLUDED.response_time_hours,
            applications_sent = EXCLUDED.applications_sent,
            cases_accepted = EXCLUDED.cases_accepted,
            responsiveness_score = EXCLUDED.responsiveness_score,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            lawyer_id,
            name,
            city,
            practice_areas,
            "English, German, Hindi",
            6,
            4.6,
            bio,
            availability_status,
            4.5,
            6,
            2,
            responsiveness_score,
        ),
    )


def _ensure_case(cur, client_id: int, title: str, description: str, legal_area: str, issue_type: str, city: str, urgency: str, brief: dict) -> int:
    cur.execute(
        "SELECT case_id FROM cases WHERE client_id = %s AND title = %s",
        (client_id, title),
    )
    row = cur.fetchone()
    if row:
        cur.execute(
            """
            UPDATE cases
            SET description = %s,
                legal_area = %s,
                issue_type = %s,
                ai_summary = %s,
                urgency = %s,
                city = %s,
                case_brief = %s::jsonb,
                status = 'open',
                is_public = TRUE
            WHERE case_id = %s
            """,
            (description, legal_area, issue_type, brief["case_summary"], urgency, city, json.dumps(brief), row[0]),
        )
        return int(row[0])

    cur.execute(
        """
        INSERT INTO cases (
            client_id, title, description, legal_area, issue_type, ai_summary, urgency, city, case_brief, is_public, status
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, TRUE, 'open')
        RETURNING case_id
        """,
        (client_id, title, description, legal_area, issue_type, brief["case_summary"], urgency, city, json.dumps(brief)),
    )
    return int(cur.fetchone()[0])


def _ensure_case_application(cur, case_id: int, lawyer_id: int, message: str) -> None:
    cur.execute(
        """
        INSERT INTO case_applications (case_id, lawyer_id, message, status)
        VALUES (%s, %s, %s, 'submitted')
        ON CONFLICT (case_id, lawyer_id)
        DO UPDATE SET
            message = EXCLUDED.message,
            status = EXCLUDED.status,
            created_at = CURRENT_TIMESTAMP
        """,
        (case_id, lawyer_id, message),
    )


def _ensure_message(cur, sender_id: int, receiver_id: int, case_id: int, content: str) -> None:
    cur.execute(
        """
        SELECT message_id
        FROM messages
        WHERE sender_id = %s AND receiver_id = %s AND case_id = %s AND content = %s
        """,
        (sender_id, receiver_id, case_id, content),
    )
    if cur.fetchone():
        return
    cur.execute(
        """
        INSERT INTO messages (sender_id, receiver_id, case_id, content, created_at)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (sender_id, receiver_id, case_id, content, datetime.now() - timedelta(hours=2)),
    )


def _ensure_notification(cur, user_id: int, message: str, notification_type: str, is_read: bool = False) -> None:
    cur.execute(
        """
        SELECT id FROM notifications
        WHERE user_id = %s AND message = %s AND type = %s
        """,
        (user_id, message, notification_type),
    )
    if cur.fetchone():
        return
    cur.execute(
        """
        INSERT INTO notifications (user_id, message, type, is_read, created_at)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (user_id, message, notification_type, is_read, datetime.now() - timedelta(hours=1)),
    )


def _ensure_case_event(cur, case_id: int, description: str, event_date: date) -> None:
    cur.execute(
        """
        SELECT id FROM case_events
        WHERE case_id = %s AND description = %s AND event_date = %s
        """,
        (case_id, description, event_date),
    )
    if cur.fetchone():
        return
    cur.execute(
        """
        INSERT INTO case_events (case_id, description, event_date, created_at)
        VALUES (%s, %s, %s, %s)
        """,
        (case_id, description, event_date, datetime.now() - timedelta(days=1)),
    )


def _ensure_watchlist(cur, user_id: int, professional_ids: list[int]) -> None:
    for professional_id in professional_ids:
        cur.execute(
            """
            INSERT INTO watchlist (user_id, professional_id)
            VALUES (%s, %s)
            ON CONFLICT (user_id, professional_id) DO NOTHING
            """,
            (user_id, professional_id),
        )


def _sync_user_sequence(cur) -> None:
    cur.execute(
        "SELECT setval(pg_get_serial_sequence('users', 'id'), COALESCE((SELECT MAX(id) FROM users), 1), true)"
    )


def seed_demo_data() -> dict:
    run_startup_migrations()
    conn = get_db_connection()
    cur = conn.cursor()

    demo_client_id = _ensure_user(cur, "demo_client", "demo_client@advocateai.local", "client")
    _ensure_user(cur, "demo_client_two", "demo_client_two@advocateai.local", "client")

    selected_professionals = _select_seed_professionals(cur, 3)
    seeded_lawyers: list[int] = []
    lawyer_names = ["demo_lawyer", "demo_lawyer_berlin", "demo_lawyer_munich"]
    availability_cycle = ["available", "busy", "available"]
    practice_cycle = [
        "Tenant Law, Consumer Law",
        "Employment Law, Contract Law",
        "Consumer Law, Civil Litigation",
    ]

    for index, professional in enumerate(selected_professionals):
        professional_id, _, city, category = professional
        user_name = lawyer_names[index]
        lawyer_id = _ensure_user(
            cur,
            user_name,
            f"{user_name}@advocateai.local",
            "lawyer",
            user_id=professional_id,
        )
        _ensure_lawyer_profile(
            cur,
            lawyer_id,
            user_name.replace("_", " ").title(),
            city,
            practice_cycle[index],
            f"Demo lawyer profile aligned to professional record {professional_id} in {city}.",
            availability_cycle[index],
            0.72 - (index * 0.08),
        )
        seeded_lawyers.append(lawyer_id)

    if not seeded_lawyers:
        cur.execute("SELECT id FROM users WHERE LOWER(name) = 'demo_lawyer' LIMIT 1")
        row = cur.fetchone()
        if row:
            seeded_lawyers.append(int(row[0]))

    case_ids = []
    seeded_cases = [
        (
            "Lost phone during metro commute",
            "I lost my mobile phone while commuting and need to block the device and understand the official process.",
            "Consumer Protection",
            "Lost Mobile Phone",
            "Berlin",
            "High",
            _case_brief(
                "Client lost a phone during travel and needs official recovery and blocking guidance.",
                "Consumer Protection",
                ["purchase invoice", "ID proof", "IMEI note"],
                ["File complaint", "Use CEIR portal", "Contact telecom operator"],
            ),
        ),
        (
            "Landlord withholding security deposit",
            "My landlord is refusing to return the security deposit after I vacated the apartment.",
            "Tenant Law",
            "Deposit Dispute",
            "Munich",
            "Medium",
            _case_brief(
                "Client seeks recovery of apartment security deposit after move-out.",
                "Tenant Law",
                ["rent agreement", "move-out photos", "payment proof"],
                ["Organize evidence", "Track timeline", "Consider formal notice or legal consultation"],
            ),
        ),
        (
            "Salary withheld after resignation",
            "My employer has not paid my final month salary after I resigned and submitted all handover documents.",
            "Employment Law",
            "Unpaid Salary",
            "Hamburg",
            "High",
            _case_brief(
                "Client reports unpaid final salary after resignation.",
                "Employment Law",
                ["appointment letter", "salary slips", "resignation email"],
                ["Collect wage records", "Prepare grievance summary", "Use labour complaint process if unresolved"],
            ),
        ),
    ]

    for title, description, legal_area, issue_type, city, urgency, brief in seeded_cases:
        case_ids.append(
            _ensure_case(cur, demo_client_id, title, description, legal_area, issue_type, city, urgency, brief)
        )

    if seeded_lawyers and case_ids:
        _ensure_case_application(cur, case_ids[0], seeded_lawyers[0], "I can help you file the immediate complaint and device blocking sequence.")
        if len(seeded_lawyers) > 1 and len(case_ids) > 1:
            _ensure_case_application(cur, case_ids[1], seeded_lawyers[1], "I handle landlord deposit and rental disputes in your city.")
        if len(seeded_lawyers) > 2 and len(case_ids) > 2:
            _ensure_case_application(cur, case_ids[2], seeded_lawyers[2], "I can review your unpaid salary matter and the labour grievance path.")

        _ensure_message(cur, demo_client_id, seeded_lawyers[0], case_ids[0], "I have the IMEI number and the purchase invoice ready. What should I prepare next?")
        _ensure_message(cur, seeded_lawyers[0], demo_client_id, case_ids[0], "Start with the police complaint and keep the reference number before using the portal.")

        _ensure_notification(cur, demo_client_id, f"A lawyer applied to your case #{case_ids[0]}.", "application")
        _ensure_notification(cur, demo_client_id, f"New message received on case #{case_ids[0]}.", "message")
        _ensure_notification(cur, seeded_lawyers[0], f"New message received on case #{case_ids[0]}.", "message", is_read=True)
        _ensure_notification(cur, demo_client_id, f"New recommended lawyers are available for case #{case_ids[1]}.", "recommendation")

    if case_ids:
        _ensure_case_event(cur, case_ids[0], "Client reported the device loss and collected the IMEI number.", date.today() - timedelta(days=2))
        _ensure_case_event(cur, case_ids[0], "Client prepared documents for complaint filing.", date.today() - timedelta(days=1))
        if len(case_ids) > 1:
            _ensure_case_event(cur, case_ids[1], "Landlord declined deposit return in writing.", date.today() - timedelta(days=3))

    professional_ids_for_watchlist = [lawyer_id for lawyer_id in seeded_lawyers[:2]]
    if professional_ids_for_watchlist:
        _ensure_watchlist(cur, demo_client_id, professional_ids_for_watchlist)

    _sync_user_sequence(cur)
    conn.commit()

    summary = {}
    for table in ["users", "professionals", "lawyer_profiles", "cases", "case_applications", "messages", "notifications", "case_events", "watchlist"]:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        summary[table] = int(cur.fetchone()[0])

    cur.close()
    conn.close()
    return summary


if __name__ == "__main__":
    counts = seed_demo_data()
    print("Demo seed completed.")
    for key, value in counts.items():
        print(f"{key}: {value}")