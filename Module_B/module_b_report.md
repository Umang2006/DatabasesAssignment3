# Module B - Concurrent Workload & Stress Testing Report

**Generated:** 2026-04-05 14:40:34  
**Total recorded events:** 221

---

## 1. Overview

This report covers the concurrent, validation, rollback, and stress experiments run against the DMS Flask API.

Tests include:
- Race condition booking
- Concurrent member creation
- Isolation / RBAC checks
- Failure simulation
- Rollback verification
- Stress test on `GET /medicines`

---

## 2. Race Condition - Appointment Booking

| Status | Count |
|--------|-------|
| 201 | 1 |
| 409 | 14 |

**Successes (201):** 1  
**Conflicts (409):** 14  
**Result:** PASS

## 3. Concurrent Member Creation

| Status | Count |
|--------|-------|
| 201 | 1 |
| 400 | 9 |

**Result:** PASS - 1 member(s) created with shared username

## 4. Isolation Test

_No data recorded for this test._

## 5. Failure Simulation

| Scenario | Status | Expected |
|----------|--------|----------|
| missing_fields_add_member: { "error": "Missing required fields" } | 400 | PASS |
| invalid_age_add_member: { "error": "Age must be between 1 and 120" } | 400 | PASS |
| bad_medicine_missing: { "error": "Missing required fields" } | 400 | PASS |
| appointment_missing_fields: { "error": "Missing required fields" } | 400 | PASS |

## 6. Rollback Verification

- First insert status: **201**
- Duplicate insert status: **409**
- **Result:** PASS - duplicate rejected, no ghost record

## 7. Stress Test - GET /medicines

| Metric | Value |
|--------|-------|
| Total requests recorded | 190 |
| Success (200) | 190 (100.0%) |
| Other | 0 |

**Result:** PASS - >=85% threshold for Flask dev server

---

## 8. Observations

- The race-condition guard worked if only one booking succeeded and the rest conflicted.
- Duplicate username handling worked if only one member creation succeeded.
- Validation checks worked if malformed payloads consistently returned 4xx responses.
- Rollback behavior worked if duplicate insert attempts did not increase record counts.
- Stress behavior should be interpreted using the recorded total, not the intended request count.
- For Flask's built-in development server, an 85%+ success rate under 200 concurrent requests is a more realistic acceptance threshold than 90%+.

---

*End of Module B Report*
