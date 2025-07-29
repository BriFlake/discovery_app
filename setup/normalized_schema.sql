-- NORMALIZED DISCOVERY APP SCHEMA
-- Replaces the monolithic JSON blob approach with efficient relational design
-- Run this in: snowpublic.streamlit schema

-- 1. CORE SESSION METADATA
CREATE OR REPLACE TABLE discovery_sessions (
    session_id VARCHAR(50) PRIMARY KEY,
    session_name VARCHAR(200) NOT NULL,
    user_email VARCHAR(100) NOT NULL,
    company_name VARCHAR(200),
    company_website VARCHAR(500),
    competitor VARCHAR(100),
    contact_name VARCHAR(100),
    contact_title VARCHAR(100),
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    status VARCHAR(20) DEFAULT 'active',
    notes TEXT
);

-- 2. INDIVIDUAL QUESTIONS (Normalized!)
CREATE OR REPLACE TABLE discovery_questions (
    question_id VARCHAR(50) PRIMARY KEY,
    session_id VARCHAR(50) NOT NULL,
    category VARCHAR(50) NOT NULL, -- Technical, Business, Competitive
    question_text TEXT NOT NULL,
    question_order INTEGER,
    importance VARCHAR(20) DEFAULT 'medium', -- high, medium, low
    explanation TEXT,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    
    -- Foreign key constraint
    CONSTRAINT fk_questions_session FOREIGN KEY (session_id) REFERENCES discovery_sessions(session_id)
);

-- 3. INDIVIDUAL ANSWERS (Normalized!)
CREATE OR REPLACE TABLE discovery_answers (
    answer_id VARCHAR(50) PRIMARY KEY,
    question_id VARCHAR(50) NOT NULL,
    session_id VARCHAR(50) NOT NULL,
    answer_text TEXT,
    confidence_level INTEGER, -- 1-5 scale
    answered_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    
    -- Foreign key constraints
    CONSTRAINT fk_answers_question FOREIGN KEY (question_id) REFERENCES discovery_questions(question_id),
    CONSTRAINT fk_answers_session FOREIGN KEY (session_id) REFERENCES discovery_sessions(session_id)
);

-- 4. STRATEGIC CONTENT (One row per content type)
CREATE OR REPLACE TABLE session_content (
    content_id VARCHAR(50) PRIMARY KEY,
    session_id VARCHAR(50) NOT NULL,
    content_type VARCHAR(50) NOT NULL, -- business_case, roadmap, competitive_strategy, value_hypothesis, etc.
    content_data VARIANT, -- For complex nested data (roadmap, emails)
    content_text TEXT, -- For simple text content
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    
    -- Foreign key constraint
    CONSTRAINT fk_content_session FOREIGN KEY (session_id) REFERENCES discovery_sessions(session_id),
    
    -- Unique constraint - one content type per session
    CONSTRAINT uk_session_content_type UNIQUE (session_id, content_type)
);

-- 5. PEOPLE RESEARCH (Normalized!)
CREATE OR REPLACE TABLE session_contacts (
    contact_id VARCHAR(50) PRIMARY KEY,
    session_id VARCHAR(50) NOT NULL,
    contact_name VARCHAR(200),
    contact_title VARCHAR(200),
    contact_linkedin VARCHAR(500),
    background_notes TEXT,
    contact_type VARCHAR(50) DEFAULT 'stakeholder', -- primary, stakeholder, technical, decision_maker, etc.
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    
    -- Foreign key constraint
    CONSTRAINT fk_contacts_session FOREIGN KEY (session_id) REFERENCES discovery_sessions(session_id)
);

-- 6. PERFORMANCE INDEXES
CREATE INDEX IF NOT EXISTS idx_discovery_sessions_user_email ON discovery_sessions (user_email);
CREATE INDEX IF NOT EXISTS idx_discovery_sessions_created_at ON discovery_sessions (created_at);
CREATE INDEX IF NOT EXISTS idx_discovery_sessions_company ON discovery_sessions (company_name);
CREATE INDEX IF NOT EXISTS idx_discovery_sessions_updated_at ON discovery_sessions (updated_at);

CREATE INDEX IF NOT EXISTS idx_discovery_questions_session ON discovery_questions (session_id);
CREATE INDEX IF NOT EXISTS idx_discovery_questions_category ON discovery_questions (category);

CREATE INDEX IF NOT EXISTS idx_discovery_answers_session ON discovery_answers (session_id);
CREATE INDEX IF NOT EXISTS idx_discovery_answers_question ON discovery_answers (question_id);

CREATE INDEX IF NOT EXISTS idx_session_content_session ON session_content (session_id);
CREATE INDEX IF NOT EXISTS idx_session_content_type ON session_content (content_type);

CREATE INDEX IF NOT EXISTS idx_session_contacts_session ON session_contacts (session_id);

-- 7. FAST PROGRESS VIEW (Pre-calculated!)
CREATE OR REPLACE VIEW session_progress AS
SELECT 
    s.session_id,
    s.session_name,
    s.user_email,
    s.company_name,
    s.company_website,
    s.competitor,
    s.contact_name,
    s.contact_title,
    s.created_at,
    s.updated_at,
    s.status,
    COUNT(DISTINCT q.question_id) as total_questions,
    COUNT(DISTINCT CASE WHEN a.answer_text IS NOT NULL AND TRIM(a.answer_text) != '' THEN a.answer_id END) as answered_questions,
    CASE 
        WHEN COUNT(DISTINCT q.question_id) = 0 THEN 0.0
        ELSE ROUND((COUNT(DISTINCT CASE WHEN a.answer_text IS NOT NULL AND TRIM(a.answer_text) != '' THEN a.answer_id END) / COUNT(DISTINCT q.question_id)) * 100, 1)
    END as completion_percentage,
    COUNT(DISTINCT sc.content_type) as content_types_count,
    ARRAY_AGG(DISTINCT sc.content_type) WITHIN GROUP (ORDER BY sc.content_type) as available_content,
    COUNT(DISTINCT contacts.contact_id) as contacts_count
FROM discovery_sessions s
LEFT JOIN discovery_questions q ON s.session_id = q.session_id
LEFT JOIN discovery_answers a ON q.question_id = a.question_id
LEFT JOIN session_content sc ON s.session_id = sc.session_id
LEFT JOIN session_contacts contacts ON s.session_id = contacts.session_id
GROUP BY s.session_id, s.session_name, s.user_email, s.company_name, s.company_website, 
         s.competitor, s.contact_name, s.contact_title, s.created_at, s.updated_at, s.status;

-- 8. ANALYTICS VIEWS FOR INSIGHTS
CREATE OR REPLACE VIEW question_analytics AS
SELECT 
    q.category,
    q.question_text,
    COUNT(a.answer_id) as times_answered,
    COUNT(DISTINCT a.session_id) as unique_sessions,
    AVG(a.confidence_level) as avg_confidence,
    COUNT(DISTINCT a.session_id) / (SELECT COUNT(DISTINCT session_id) FROM discovery_sessions) * 100 as answer_rate_percentage
FROM discovery_questions q
LEFT JOIN discovery_answers a ON q.question_id = a.question_id
GROUP BY q.category, q.question_text
ORDER BY times_answered DESC;

CREATE OR REPLACE VIEW content_usage_analytics AS
SELECT 
    content_type,
    COUNT(*) as usage_count,
    COUNT(*) / (SELECT COUNT(DISTINCT session_id) FROM discovery_sessions) * 100 as usage_percentage,
    AVG(LENGTH(content_text)) as avg_content_length
FROM session_content
GROUP BY content_type
ORDER BY usage_count DESC;

-- 9. SAMPLE DATA (Optional - for testing)
/*
INSERT INTO discovery_sessions (session_id, session_name, user_email, company_name, company_website, competitor)
VALUES ('test-session-1', 'Acme Corp Discovery', 'test@company.com', 'Acme Corporation', 'https://acme.com', 'Databricks');

INSERT INTO discovery_questions (question_id, session_id, category, question_text, question_order, importance)
VALUES 
    ('q1', 'test-session-1', 'Technical', 'What data platforms do you currently use?', 1, 'high'),
    ('q2', 'test-session-1', 'Business', 'What are your main business challenges?', 2, 'high'),
    ('q3', 'test-session-1', 'Competitive', 'How do you evaluate new technology vendors?', 3, 'medium');

INSERT INTO discovery_answers (answer_id, question_id, session_id, answer_text, confidence_level)
VALUES 
    ('a1', 'q1', 'test-session-1', 'We use Hadoop and some legacy systems', 4),
    ('a2', 'q2', 'test-session-1', 'Data silos and slow analytics are major issues', 5);
*/

-- 10. MIGRATION HELPER VIEWS (for data migration from old schema)
CREATE OR REPLACE VIEW migration_session_summary AS
SELECT 
    old.SESSION_ID,
    old.SESSION_NAME,
    old.USER_EMAIL,
    old.COMPANY_NAME,
    old.COMPANY_WEBSITE,
    old.COMPETITOR,
    old.CONTACT_NAME,
    old.CONTACT_TITLE,
    old.CREATED_AT,
    old.UPDATED_AT,
    old.DISCOVERY_QUESTIONS,
    old.BUSINESS_CASE,
    old.ROADMAP_DATA,
    old.COMPETITOR_STRATEGY,
    old.VALUE_HYPOTHESIS,
    old.OUTREACH_EMAILS,
    old.LINKEDIN_MESSAGES,
    old.PEOPLE_RESEARCH,
    old.FULL_SESSION_STATE
FROM snowpublic.streamlit.discovery_sessions old
WHERE old.SESSION_ID IS NOT NULL;

-- Success message
SELECT 'Normalized schema created successfully! Ready for migration.' as status; 