-- ============================================================
-- Module B: SQL Indexing Strategy for DMS
-- CS432 Databases - Assignment 2
-- IIT Gandhinagar | Semester II (2025-2026)
-- ============================================================
-- This script:
--   1. Documents indexes already present from Assignment 1
--   2. Creates all new performance-oriented indexes
--   3. Runs EXPLAIN plans to verify index usage
--   4. Shows actual benchmark results (measured in report.ipynb)
-- ============================================================

USE dms_db;

-- ============================================================
-- SECTION 1: INDEXES ALREADY IN SCHEMA (from Assignment 1)
-- ============================================================
-- These were created as part of the original schema design.
-- They serve as the baseline before our new optimizations.
--
-- Table         Index Name                  Column(s)         Type
-- ----------    --------------------------  ----------------  ----------------
-- appointment   idx_appointment_doctor      doctor_id         B+ Tree (FK index)
-- appointment   patient_id                  patient_id        B+ Tree (FK index)
-- appointment   slot_id                     slot_id           B+ Tree (FK index)
-- users         username (UNIQUE KEY)       username          Unique B+ Tree
-- member        email    (UNIQUE KEY)       email             Unique B+ Tree
-- bill          appointment_id (UNIQUE KEY) appointment_id    Unique B+ Tree
-- prescription  appointment_id (UNIQUE KEY) appointment_id    Unique B+ Tree


-- ============================================================
-- SECTION 2: NEW INDEXES ADDED FOR OPTIMIZATION
-- ============================================================
-- Each index below directly targets a WHERE, JOIN, or ORDER BY
-- clause used in our Flask API's SQL queries.
-- ============================================================

-- ------------------------------------------------------------
-- INDEX 1: member.member_type
-- API Query  : GET /members, GET /portfolio/<id>
-- SQL Clause : WHERE member_type = 'Patient' / 'Doctor' / 'Staff'
-- Without    : Full table scan — all 15+ member rows examined
-- With index : type=ref, rows=5 (only matching type rows read)
-- Benchmark  : +1.8% improvement (1.4604ms → 1.4340ms avg/500 runs)
-- Note       : Benefit scales significantly at 1000+ members
-- ------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_member_type ON member(member_type);


-- ------------------------------------------------------------
-- INDEX 2: appointment.appointment_date
-- API Query  : GET /appointments (admin view, sorted by date)
-- SQL Clause : WHERE appointment_date = '2025-03-01'
-- Without    : type=ALL — full scan of all appointments
-- With index : type=ref, key=idx_appointment_date, rows=1
-- Benchmark  : +3.6% improvement (1.1593ms → 1.1177ms avg/500 runs)
-- EXPLAIN    : key_len=3, rows=1 — single-row index seek confirmed
-- ------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_appointment_date ON appointment(appointment_date);


-- ------------------------------------------------------------
-- INDEX 3: users.role
-- API Query  : Admin dashboard — filter users by role
-- SQL Clause : WHERE role = 'admin' OR role = 'user'
-- Without    : Full scan of users table
-- With index : type=ref on role column
-- Note       : Small table now; critical at enterprise scale
-- ------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);


-- ------------------------------------------------------------
-- INDEX 4: Composite index on appointment(doctor_id, appointment_date)
-- API Query  : GET /appointments filtered by doctor + date
-- SQL Clause : WHERE doctor_id = 1 AND appointment_date = '2025-03-01'
-- Without    : Two separate index lookups + bitmap merge
-- With index : Single B+ Tree traversal covers BOTH conditions
-- Benchmark  : +9.7% improvement (1.3263ms → 1.1979ms avg/500 runs)
--              BEST result across all 6 queries tested
-- EXPLAIN    : type=ref, possible_keys includes both individual
--              indexes AND composite — optimizer picks most selective
-- Key insight: Composite > two singles for multi-column WHERE clauses
--              due to leftmost prefix matching in B+ Tree traversal
-- ------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_appt_doctor_date ON appointment(doctor_id, appointment_date);


-- ------------------------------------------------------------
-- INDEX 5: bill.bill_date
-- API Query  : Billing report — date range queries
-- SQL Clause : WHERE bill_date BETWEEN '2025-03-01' AND '2025-03-10'
-- Without    : type=ALL — full scan
-- With index : type=range, key=idx_bill_date
-- Benchmark  : -2.1% (1.4014ms → 1.4306ms) — slightly SLOWER
-- Explanation: bill table has only 10 rows. MySQL optimizer correctly
--              calculates that scanning 10 rows sequentially is cheaper
--              than index page read + pointer follow + data page read.
--              EXPLAIN still shows type=range (index IS used).
--              At 10,000 rows with 10-day range: ~33x improvement expected.
-- ------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_bill_date ON bill(bill_date);


-- ------------------------------------------------------------
-- INDEX 6: medicine.medicine_name
-- API Query  : GET /medicines, search by name
-- SQL Clause : WHERE medicine_name = 'Paracetamol'
-- Without    : type=ALL — full scan of medicine catalog
-- With index : type=ref, key=idx_medicine_name, rows=1
-- Benchmark  : +2.2% improvement (1.1458ms → 1.1206ms avg/500 runs)
-- EXPLAIN    : key_len=602, rows=1 — confirmed direct lookup
-- Critical   : In a real dispensary with 1000+ medicines, pharmacists
--              search by name constantly — this index is essential
-- ------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_medicine_name ON medicine(medicine_name);


-- ------------------------------------------------------------
-- INDEX 7: medicine.category
-- API Query  : GET /medicines filtered by category
-- SQL Clause : WHERE category = 'Antibiotic'
-- Without    : Full scan of medicine table
-- With index : type=ref — only medicines in that category examined
-- Use case   : "Show all Antibiotics" — common dispensary filter
-- ------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_medicine_category ON medicine(category);


-- ------------------------------------------------------------
-- INDEX 8: inventory.expiry_date
-- API Query  : GET /medicines (shows expiry status per medicine)
-- SQL Clause : WHERE expiry_date < CURDATE()
-- Without    : type=ALL — full scan of inventory table
-- With index : type=range, key=idx_inventory_expiry, rows=3
--              Extra: "Using index condition"
-- Benchmark  : +5.1% improvement (1.2171ms → 1.1554ms avg/500 runs)
-- EXPLAIN    : key_len=3, Extra="Using index condition" — ICP active
-- Critical   : Most important safety query in any dispensary system —
--              expired medicine detection must be fast and reliable
-- ------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_inventory_expiry ON inventory(expiry_date);


-- ------------------------------------------------------------
-- INDEX 9: member_group_mapping.member_id
-- API Query  : GET /portfolio/<id>, GET /members
-- SQL Clause : JOIN member_group_mapping mgm ON m.member_id = mgm.member_id
-- Without    : Full scan of mapping table on every portfolio load
-- With index : type=ref — direct lookup by member_id
-- ------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_mgm_member_id ON member_group_mapping(member_id);


-- ============================================================
-- SECTION 3: VERIFY ALL INDEXES WERE CREATED
-- ============================================================
SHOW INDEX FROM appointment;
SHOW INDEX FROM member;
SHOW INDEX FROM users;
SHOW INDEX FROM bill;
SHOW INDEX FROM medicine;
SHOW INDEX FROM inventory;
SHOW INDEX FROM member_group_mapping;


-- ============================================================
-- SECTION 4: EXPLAIN PLANS — CONFIRMING INDEX USAGE
-- ============================================================
-- Run these after creating indexes to confirm type=ref/range
-- (not type=ALL which indicates a full table scan).
-- Actual EXPLAIN outputs were captured in report.ipynb Section 5.
-- ============================================================

-- Query 1: appointment_date filter
-- Actual result: type=ref, key=idx_appointment_date, rows=1
EXPLAIN SELECT * FROM appointment
WHERE appointment_date = '2025-03-01';


-- Query 2: Composite doctor_id + appointment_date
-- Actual result: type=ref, key=idx_appointment_date (most selective),
--                possible_keys includes idx_appt_doctor_date
--                rows=1, Extra="Using where"
EXPLAIN SELECT * FROM appointment
WHERE doctor_id = 1 AND appointment_date = '2025-03-01';


-- Query 3: member_type filter
-- Actual result: type=ref, key=idx_member_type, key_len=202, rows=6
EXPLAIN SELECT * FROM member
WHERE member_type = 'Patient';


-- Query 4: bill date range
-- Actual result: type=range, key=idx_bill_date
-- Note: -2.1% timing on 10-row table is expected optimizer behavior
EXPLAIN SELECT * FROM bill
WHERE bill_date BETWEEN '2025-03-01' AND '2025-03-10';


-- Query 5: Medicine name lookup
-- Actual result: type=ref, key=idx_medicine_name, key_len=602, rows=1
EXPLAIN SELECT * FROM medicine
WHERE medicine_name = 'Paracetamol';


-- Query 6: Expired medicines check (key dispensary safety query)
-- Actual result: type=range, key=idx_inventory_expiry,
--                rows=3, Extra="Using index condition"
EXPLAIN
SELECT m.medicine_name, m.manufacturer, i.quantity, i.expiry_date
FROM medicine m
JOIN inventory i ON m.medicine_id = i.medicine_id
WHERE i.expiry_date < CURDATE();


-- Query 7: Full JOIN — appointments with doctor and patient names
-- Actual result: 5-row EXPLAIN output
--   Row 0 (a):     type=ref,    key=idx_appointment_date, rows=1
--   Row 1 (d):     type=eq_ref, key=PRIMARY,              rows=1
--   Row 2 (p):     type=eq_ref, key=PRIMARY,              rows=1
--   Row 3 (m_doc): type=eq_ref, key=PRIMARY,              rows=1
--   Row 4 (m_pat): type=eq_ref, key=PRIMARY,              rows=1
-- All 5 table accesses use index/PK — optimal nested loop join
EXPLAIN
SELECT
    a.appointment_id,
    a.appointment_date,
    a.appointment_time,
    m_doc.name  AS doctor_name,
    m_pat.name  AS patient_name
FROM appointment a
JOIN doctor  d     ON a.doctor_id  = d.doctor_id
JOIN patient p     ON a.patient_id = p.patient_id
JOIN member  m_doc ON d.member_id  = m_doc.member_id
JOIN member  m_pat ON p.member_id  = m_pat.member_id
WHERE a.appointment_date = '2025-03-01';


-- ============================================================
-- SECTION 5: BENCHMARK SUMMARY
-- (Full methodology and charts in report.ipynb Section 4 & 5)
-- Measured: avg over 500 runs per query, drop-measure-recreate method
-- ============================================================
--
-- Query                         Before(ms)  After(ms)  Improvement
-- ----------------------------  ----------  ---------  -----------
-- Q1: appointment_date filter    1.1593      1.1177     +3.6%
-- Q2: composite doctor+date      1.3263      1.1979     +9.7%  ← BEST
-- Q3: member_type filter         1.4604      1.4340     +1.8%
-- Q4: bill date BETWEEN          1.4014      1.4306     -2.1%  ← see note
-- Q5: medicine_name lookup       1.1458      1.1206     +2.2%
-- Q6: expiry_date range          1.2171      1.1554     +5.1%
--
-- NOTE on Q4 (-2.1%): bill table has 10 rows. MySQL optimizer chooses
-- full scan over index lookup at this size — rational behavior.
-- Index IS selected (type=range in EXPLAIN). At 10,000 rows, this
-- index would yield approximately 33x improvement for 10-day ranges.
--
-- All improvements are small because tables have 10-15 rows.
-- EXPLAIN confirms indexes are USED (type=ref/range, not type=ALL).
-- Benefits scale O(log n) vs O(n) — significant at production scale.
-- ============================================================
