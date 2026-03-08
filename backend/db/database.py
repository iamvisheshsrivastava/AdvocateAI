import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

LEGAL_DEFAULT_ROLE = "client"


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
        port=int(os.getenv("DB_PORT", "5432")),
    )


def run_startup_migrations():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS password TEXT")
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT")
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'client'")
    cur.execute("UPDATE users SET password_hash = COALESCE(password_hash, password) WHERE password_hash IS NULL")
    cur.execute("UPDATE users SET role = 'client' WHERE role IS NULL")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS lawyer_profiles (
            lawyer_id INT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            city TEXT,
            practice_areas TEXT,
            languages TEXT,
            experience_years INT DEFAULT 0,
            rating FLOAT DEFAULT 0,
            bio TEXT,
            availability_status TEXT DEFAULT 'available',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute("ALTER TABLE lawyer_profiles ADD COLUMN IF NOT EXISTS availability_status TEXT DEFAULT 'available'")
    cur.execute("ALTER TABLE lawyer_profiles ADD COLUMN IF NOT EXISTS response_time_hours FLOAT DEFAULT 0")
    cur.execute("ALTER TABLE lawyer_profiles ADD COLUMN IF NOT EXISTS applications_sent INT DEFAULT 0")
    cur.execute("ALTER TABLE lawyer_profiles ADD COLUMN IF NOT EXISTS cases_accepted INT DEFAULT 0")
    cur.execute("ALTER TABLE lawyer_profiles ADD COLUMN IF NOT EXISTS responsiveness_score FLOAT DEFAULT 0")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS cases (
            case_id SERIAL PRIMARY KEY,
            client_id INT REFERENCES users(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            legal_area TEXT,
            issue_type TEXT,
            ai_summary TEXT,
            urgency TEXT,
            city TEXT,
            is_public BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'open' CHECK (status IN ('open', 'closed'))
        )
        """
    )
    cur.execute("ALTER TABLE cases ADD COLUMN IF NOT EXISTS legal_area TEXT")
    cur.execute("ALTER TABLE cases ADD COLUMN IF NOT EXISTS issue_type TEXT")
    cur.execute("ALTER TABLE cases ADD COLUMN IF NOT EXISTS ai_summary TEXT")
    cur.execute("ALTER TABLE cases ADD COLUMN IF NOT EXISTS urgency TEXT")
    cur.execute("ALTER TABLE cases ADD COLUMN IF NOT EXISTS case_brief JSONB DEFAULT '{}'::jsonb")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS case_applications (
            id SERIAL PRIMARY KEY,
            case_id INT REFERENCES cases(case_id) ON DELETE CASCADE,
            lawyer_id INT REFERENCES users(id) ON DELETE CASCADE,
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'submitted',
            UNIQUE (case_id, lawyer_id)
        )
        """
    )
    cur.execute("ALTER TABLE case_applications ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'submitted'")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            message_id SERIAL PRIMARY KEY,
            sender_id INT REFERENCES users(id) ON DELETE CASCADE,
            receiver_id INT REFERENCES users(id) ON DELETE CASCADE,
            case_id INT REFERENCES cases(case_id) ON DELETE SET NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS notifications (
            id SERIAL PRIMARY KEY,
            user_id INT REFERENCES users(id) ON DELETE CASCADE,
            message TEXT NOT NULL,
            type TEXT NOT NULL,
            is_read BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS case_events (
            id SERIAL PRIMARY KEY,
            case_id INT REFERENCES cases(case_id) ON DELETE CASCADE,
            description TEXT NOT NULL,
            event_date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cur.execute("CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cases_legal_area ON cases(legal_area)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cases_city ON cases(city)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cases_client_id ON cases(client_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_case_applications_case_id ON case_applications(case_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_case_applications_lawyer_id ON case_applications(lawyer_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_lawyer_profiles_city ON lawyer_profiles(city)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_lawyer_profiles_lawyer_id ON lawyer_profiles(lawyer_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_case_id ON messages(case_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_receiver_id ON messages(receiver_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_notifications_read_state ON notifications(user_id, is_read)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_case_events_case_id ON case_events(case_id)")

    conn.commit()
    cur.close()
    conn.close()
