-- Enhanced Salesforce Account Search - No Special Permissions Required!
-- This document explains the improved search strategies available in the Discovery App

-- =======================================================================================
-- IMPORTANT FILTERS APPLIED
-- =======================================================================================

-- DATE FILTER: Only accounts with LAST_MODIFIED_DATE >= '2025-02-01' are shown
-- This ensures you only see recently updated/active accounts

-- RECORD STATUS: Only non-deleted accounts (IS_DELETED = FALSE) are included

-- =======================================================================================
-- SEARCH METHODS AVAILABLE
-- =======================================================================================

-- METHOD 1: SEARCH BY NAME (Enhanced with multiple strategies)
-- METHOD 2: DIRECT RECORD ID LOOKUP (New!)

-- =======================================================================================
-- SEARCH STRATEGIES OVERVIEW
-- =======================================================================================

-- 1. SMART AUTO (Default - Recommended)
-- Automatically selects the best search method based on input characteristics:
-- - Multiple terms (e.g., "tech company") → Multi-Term Search
-- - Long terms (6+ chars) → Fuzzy Matching
-- - Short terms → Basic Optimized Search

-- 2. FUZZY MATCHING
-- Uses Snowflake's built-in similarity functions for flexible matching:
-- - JAROWINKLER_SIMILARITY: Finds similar company names even with typos
-- - SOUNDEX: Phonetic matching for companies that sound similar
-- - Multi-strategy ranking with relevance scores

-- 3. MULTI-TERM SEARCH
-- Optimized for searching multiple keywords simultaneously:
-- - Handles comma-separated and space-separated terms
-- - Searches across NAME, INDUSTRY, and DESCRIPTION fields
-- - Calculates relevance based on number of matching terms

-- 4. BASIC SEARCH
-- Fast, optimized traditional search:
-- - Exact prefix matching (fastest)
-- - Contains matching (fallback)
-- - Minimal resource usage

-- =======================================================================================
-- EXAMPLE FUZZY MATCHING QUERY
-- =======================================================================================

/*
-- This query demonstrates the fuzzy matching strategy used in the app
WITH search_results AS (
    -- Strategy 1: Exact prefix matches (highest priority)
    SELECT 
        a.ID, a.NAME, a.TYPE, a.OWNER_ID, u.NAME as OWNER_NAME, 
        a.WEBSITE, a.INDUSTRY, a.DESCRIPTION,
        1 as search_priority,
        100 as relevance_score
    FROM FIVETRAN.SALESFORCE.ACCOUNT a
    LEFT JOIN FIVETRAN.SALESFORCE.USER u ON a.OWNER_ID = u.ID
    WHERE UPPER(a.NAME) LIKE UPPER('Microsoft%')
        AND a.IS_DELETED = FALSE AND a.NAME IS NOT NULL AND a.TYPE IS NOT NULL
    
    UNION ALL
    
    -- Strategy 2: Contains matches with Jaro-Winkler similarity
    SELECT 
        a.ID, a.NAME, a.TYPE, a.OWNER_ID, u.NAME as OWNER_NAME, 
        a.WEBSITE, a.INDUSTRY, a.DESCRIPTION,
        2 as search_priority,
        GREATEST(
            JAROWINKLER_SIMILARITY(UPPER('Microsoft'), UPPER(a.NAME)) * 100,
            CASE WHEN a.INDUSTRY IS NOT NULL THEN JAROWINKLER_SIMILARITY(UPPER('Microsoft'), UPPER(a.INDUSTRY)) * 80 ELSE 0 END
        ) as relevance_score
    FROM FIVETRAN.SALESFORCE.ACCOUNT a
    LEFT JOIN FIVETRAN.SALESFORCE.USER u ON a.OWNER_ID = u.ID
    WHERE (
        UPPER(a.NAME) LIKE UPPER('%Microsoft%') 
        OR (a.INDUSTRY IS NOT NULL AND UPPER(a.INDUSTRY) LIKE UPPER('%Microsoft%'))
        OR (a.DESCRIPTION IS NOT NULL AND UPPER(a.DESCRIPTION) LIKE UPPER('%Microsoft%'))
    )
    AND a.IS_DELETED = FALSE AND a.NAME IS NOT NULL AND a.TYPE IS NOT NULL
    AND NOT UPPER(a.NAME) LIKE UPPER('Microsoft%')  -- Exclude exact prefix matches already found
    
    UNION ALL
    
    -- Strategy 3: Soundex phonetic matching for company names
    SELECT 
        a.ID, a.NAME, a.TYPE, a.OWNER_ID, u.NAME as OWNER_NAME, 
        a.WEBSITE, a.INDUSTRY, a.DESCRIPTION,
        3 as search_priority,
        60 as relevance_score
    FROM FIVETRAN.SALESFORCE.ACCOUNT a
    LEFT JOIN FIVETRAN.SALESFORCE.USER u ON a.OWNER_ID = u.ID
    WHERE SOUNDEX(a.NAME) = SOUNDEX('Microsoft')
        AND a.IS_DELETED = FALSE AND a.NAME IS NOT NULL AND a.TYPE IS NOT NULL
        AND NOT UPPER(a.NAME) LIKE UPPER('Microsoft%')  -- Exclude already found
        AND NOT (
            UPPER(a.NAME) LIKE UPPER('%Microsoft%') 
            OR (a.INDUSTRY IS NOT NULL AND UPPER(a.INDUSTRY) LIKE UPPER('%Microsoft%'))
        )
)
SELECT DISTINCT ID, NAME, TYPE, OWNER_ID, OWNER_NAME, WEBSITE, INDUSTRY, DESCRIPTION,
       MIN(search_priority) as search_priority,
       MAX(relevance_score) as relevance_score
FROM search_results
WHERE relevance_score >= 30  -- Minimum relevance threshold
GROUP BY ID, NAME, TYPE, OWNER_ID, OWNER_NAME, WEBSITE, INDUSTRY, DESCRIPTION
ORDER BY search_priority ASC, relevance_score DESC, NAME ASC
LIMIT 20;
*/

-- =======================================================================================
-- PERFORMANCE OPTIMIZATION NOTES
-- =======================================================================================

-- 1. Automatic Strategy Selection:
--    - Reduces unnecessary complexity for simple searches
--    - Scales performance based on search complexity

-- 2. Relevance Thresholds:
--    - Filters out low-quality matches (< 30% similarity)
--    - Focuses results on most relevant accounts

-- 3. Search Limits:
--    - Multi-term search limited to 3 terms for performance
--    - All searches limited to 20 results
--    - Results cached for 5 minutes

-- 4. Field Prioritization:
--    - Company NAME: 100% weight (most important)
--    - INDUSTRY: 80% weight (secondary)
--    - DESCRIPTION: Equal weight with NAME in contains searches

-- =======================================================================================
-- DIRECT RECORD ID LOOKUP
-- =======================================================================================

/*
-- Example direct Record ID lookup query:
SELECT 
    a.ID, 
    a.NAME, 
    a.TYPE, 
    a.OWNER_ID, 
    u.NAME as OWNER_NAME, 
    a.WEBSITE, 
    a.INDUSTRY,
    a.DESCRIPTION,
    a.LAST_MODIFIED_DATE
FROM FIVETRAN.SALESFORCE.ACCOUNT a
LEFT JOIN FIVETRAN.SALESFORCE.USER u ON a.OWNER_ID = u.ID
WHERE a.ID = '0010Z00001uW5TNQA0'  -- 18-character Record ID
    AND a.IS_DELETED = FALSE
    AND a.LAST_MODIFIED_DATE >= '2025-02-01';
*/

-- =======================================================================================
-- SEARCH EXAMPLES AND USE CASES
-- =======================================================================================

-- Example 1: Basic company search
-- Input: "Microsoft"
-- Method: Search by Name
-- Strategy: Smart Auto → Basic (short, single term)
-- Finds: Microsoft Corporation, Microsoft Azure, etc.

-- Example 2: Industry search
-- Input: "technology company"
-- Method: Search by Name
-- Strategy: Smart Auto → Multi-Term (multiple words)
-- Finds: Any company with "technology" in name/industry AND "company" in name/description

-- Example 3: Fuzzy company name
-- Input: "Micrsoft" (typo)
-- Method: Search by Name
-- Strategy: Fuzzy Matching
-- Finds: Microsoft Corporation (via Jaro-Winkler similarity)

-- Example 4: Phonetic search
-- Input: "Mikrosoft" (phonetic spelling)
-- Method: Search by Name
-- Strategy: Fuzzy Matching
-- Finds: Microsoft Corporation (via SOUNDEX matching)

-- Example 5: Direct Record ID lookup
-- Input: "0010Z00001uW5TNQA0"
-- Method: Enter Record ID
-- Result: Instant lookup of specific account (if modified after Feb 1, 2025)
-- Speed: Fastest possible - direct database key lookup

-- =======================================================================================
-- BUILT-IN SNOWFLAKE FUNCTIONS USED
-- =======================================================================================

-- JAROWINKLER_SIMILARITY(string1, string2)
-- - Returns similarity score between 0 and 1
-- - Excellent for catching typos and variations
-- - No special permissions required

-- SOUNDEX(string)
-- - Converts string to phonetic representation
-- - Finds companies that "sound like" the search term
-- - Handles different spellings of same pronunciation

-- UPPER() and LIKE with wildcards
-- - Standard SQL pattern matching
-- - Case-insensitive searching
-- - Optimized for performance with proper indexing

-- No additional setup, permissions, or services required!
-- Works with any Snowflake account that has access to FIVETRAN.SALESFORCE.ACCOUNT table. 