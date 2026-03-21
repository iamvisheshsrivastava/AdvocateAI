-- ==============================
-- USERS TABLE
-- ==============================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name TEXT,
    email TEXT UNIQUE,
    password TEXT,
    password_hash TEXT,
    role TEXT DEFAULT 'client' CHECK (role IN ('client', 'lawyer', 'admin')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE users ADD COLUMN IF NOT EXISTS password TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'client';
UPDATE users SET password_hash = COALESCE(password_hash, password) WHERE password_hash IS NULL;
UPDATE users SET role = 'client' WHERE role IS NULL;

-- ==============================
-- PROFESSIONALS TABLE
-- ==============================
CREATE TABLE IF NOT EXISTS professionals (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    address TEXT NOT NULL,
    city TEXT,
    rating FLOAT,
    review_count INT,
    category TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_professional UNIQUE (name, address)
);

CREATE INDEX IF NOT EXISTS idx_professionals_city ON professionals(city);
CREATE INDEX IF NOT EXISTS idx_professionals_category ON professionals(category);

-- ==============================
-- AGENTS TABLE
-- ==============================
CREATE TABLE IF NOT EXISTS agents (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==============================
-- RATINGS TABLE
-- ==============================
CREATE TABLE IF NOT EXISTS ratings (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    professional_id INT REFERENCES professionals(id) ON DELETE CASCADE,
    rating INT CHECK (rating BETWEEN 1 AND 5),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==============================
-- WATCHLIST TABLE
-- ==============================
CREATE TABLE IF NOT EXISTS watchlist (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    professional_id INT REFERENCES professionals(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, professional_id)
);

CREATE INDEX IF NOT EXISTS idx_watchlist_user ON watchlist(user_id);
CREATE INDEX IF NOT EXISTS idx_watchlist_professional ON watchlist(professional_id);

-- ==============================
-- LAWYER PROFILES TABLE
-- ==============================
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
    response_time_hours FLOAT DEFAULT 0,
    applications_sent INT DEFAULT 0,
    cases_accepted INT DEFAULT 0,
    responsiveness_score FLOAT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE lawyer_profiles ADD COLUMN IF NOT EXISTS availability_status TEXT DEFAULT 'available';
ALTER TABLE lawyer_profiles ADD COLUMN IF NOT EXISTS response_time_hours FLOAT DEFAULT 0;
ALTER TABLE lawyer_profiles ADD COLUMN IF NOT EXISTS applications_sent INT DEFAULT 0;
ALTER TABLE lawyer_profiles ADD COLUMN IF NOT EXISTS cases_accepted INT DEFAULT 0;
ALTER TABLE lawyer_profiles ADD COLUMN IF NOT EXISTS responsiveness_score FLOAT DEFAULT 0;

-- ==============================
-- CASES TABLE
-- ==============================
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
    case_brief JSONB DEFAULT '{}'::jsonb,
    is_public BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'open' CHECK (status IN ('open', 'closed'))
);

ALTER TABLE cases ADD COLUMN IF NOT EXISTS issue_type TEXT;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS ai_summary TEXT;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS urgency TEXT;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS case_brief JSONB DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status);
CREATE INDEX IF NOT EXISTS idx_cases_legal_area ON cases(legal_area);
CREATE INDEX IF NOT EXISTS idx_cases_city ON cases(city);
CREATE INDEX IF NOT EXISTS idx_cases_client_id ON cases(client_id);

-- ==============================
-- CASE APPLICATIONS TABLE
-- ==============================
CREATE TABLE IF NOT EXISTS case_applications (
    id SERIAL PRIMARY KEY,
    case_id INT REFERENCES cases(case_id) ON DELETE CASCADE,
    lawyer_id INT REFERENCES users(id) ON DELETE CASCADE,
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'submitted',
    UNIQUE (case_id, lawyer_id)
);

ALTER TABLE case_applications ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'submitted';

CREATE INDEX IF NOT EXISTS idx_case_applications_case_id ON case_applications(case_id);
CREATE INDEX IF NOT EXISTS idx_case_applications_lawyer_id ON case_applications(lawyer_id);

-- ==============================
-- MESSAGES TABLE (OPTIONAL)
-- ==============================
CREATE TABLE IF NOT EXISTS messages (
    message_id SERIAL PRIMARY KEY,
    sender_id INT REFERENCES users(id) ON DELETE CASCADE,
    receiver_id INT REFERENCES users(id) ON DELETE CASCADE,
    case_id INT REFERENCES cases(case_id) ON DELETE SET NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_messages_case_id ON messages(case_id);
CREATE INDEX IF NOT EXISTS idx_messages_sender_id ON messages(sender_id);
CREATE INDEX IF NOT EXISTS idx_messages_receiver_id ON messages(receiver_id);

-- ==============================
-- NOTIFICATIONS TABLE
-- ==============================
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    type TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_read_state ON notifications(user_id, is_read);

-- ==============================
-- CASE EVENTS TABLE
-- ==============================
CREATE TABLE IF NOT EXISTS case_events (
    id SERIAL PRIMARY KEY,
    case_id INT REFERENCES cases(case_id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    event_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_case_events_case_id ON case_events(case_id);

-- ==============================
-- CASE DOCUMENTS TABLE
-- ==============================
CREATE TABLE IF NOT EXISTS case_documents (
    id SERIAL PRIMARY KEY,
    batch_id TEXT NOT NULL,
    user_id INT REFERENCES users(id) ON DELETE SET NULL,
    case_id INT REFERENCES cases(case_id) ON DELETE SET NULL,
    file_name TEXT NOT NULL,
    content_type TEXT,
    page_count INT,
    document_type TEXT,
    legal_area TEXT,
    extracted_text TEXT,
    structured_json JSONB DEFAULT '{}'::jsonb,
    summary TEXT,
    potential_issue TEXT,
    recommended_action TEXT,
    confidence_level TEXT,
    citations JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_case_documents_batch_id ON case_documents(batch_id);
CREATE INDEX IF NOT EXISTS idx_case_documents_user_id ON case_documents(user_id);
CREATE INDEX IF NOT EXISTS idx_case_documents_case_id ON case_documents(case_id);

-- ==============================
-- AUDIT LOGS TABLE
-- ==============================
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INT,
    action_type TEXT,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
