"""
Module B - Failure Simulation & Rollback Verification
"""

import json
import os
import time

import requests


BASE_URL = os.environ.get("DMS_BASE_URL", "http://localhost:5000")
SEED_FILE = ".test_seed.json"


def load_seed():
    if os.path.exists(SEED_FILE):
        with open(SEED_FILE, "r", encoding="utf-8") as handle:
            return json.load(handle)
    return {}


SEED = load_seed()
ADMIN_USER = os.environ.get("DMS_ADMIN_USER", SEED.get("admin", {}).get("user", "admin"))
ADMIN_PASS = os.environ.get("DMS_ADMIN_PASS", SEED.get("admin", {}).get("password", "password123"))
PATIENT1_USER = os.environ.get("DMS_PATIENT1_USER", SEED.get("patients", {}).get("patient1", {}).get("username", "patient1"))
PATIENT1_PASS = os.environ.get("DMS_PATIENT1_PASS", SEED.get("patients", {}).get("patient1", {}).get("password", "Patient1pass"))


def login(user, password):
    response = requests.post(f"{BASE_URL}/login", json={"user": user, "password": password}, timeout=10)
    if response.status_code == 200:
        return response.json()["session_token"]
    raise RuntimeError(f"Login failed for {user}: {response.text}")


def headers(token):
    return {"Authorization": f"Bearer {token}"}


PASS_COUNT = 0
FAIL_COUNT = 0


def check(name, condition, detail=""):
    global PASS_COUNT, FAIL_COUNT
    if condition:
        PASS_COUNT += 1
        print(f"  [PASS] {name}")
    else:
        FAIL_COUNT += 1
        print(f"  [FAIL] {name} -> {detail}")


def test_unauthenticated():
    print("\n1. Unauthenticated Access")
    endpoints = ["/members", "/medicines", "/my_appointments", "/add_member", "/audit_logs"]
    for endpoint in endpoints:
        method = requests.post if endpoint.startswith("/add") else requests.get
        response = method(f"{BASE_URL}{endpoint}", timeout=10)
        check(f"No token -> {endpoint} returns 401", response.status_code == 401, f"got {response.status_code}")


def test_invalid_login():
    print("\n2. Invalid Login")
    response = requests.post(f"{BASE_URL}/login", json={"user": "nobody", "password": "wrongpass"}, timeout=10)
    check("Wrong credentials -> 401", response.status_code == 401, response.text[:80])


def test_member_rollback(admin_token):
    print("\n3. Member Creation Rollback")
    before = len(requests.get(f"{BASE_URL}/members", headers=headers(admin_token), timeout=10).json().get("members", []))

    bad_cases = [
        ("missing_name", {"age": 25, "email": "x@y.com", "contact_no": "9000000000", "username": "noname", "password": "Pass1234", "member_type": "Patient", "role": "user", "gender": "Male", "address": "A"}),
        ("bad_email", {"name": "Bad", "age": 25, "email": "not-an-email", "contact_no": "9000000000", "username": f"bademail_{int(time.time())}", "password": "Pass1234", "member_type": "Patient", "role": "user", "gender": "Male", "address": "A"}),
        ("invalid_member_type", {"name": "Bad", "age": 25, "email": f"inv_{int(time.time())}@t.com", "contact_no": "9000000000", "username": f"invtype_{int(time.time())}", "password": "Pass1234", "member_type": "Ghost", "role": "user", "gender": "Male", "address": "A"}),
        ("weak_password", {"name": "Bad", "age": 25, "email": f"wp_{int(time.time())}@t.com", "contact_no": "9000000000", "username": f"weakpw_{int(time.time())}", "password": "abc", "member_type": "Patient", "role": "user", "gender": "Male", "address": "A"}),
    ]

    for case_name, payload in bad_cases:
        response = requests.post(f"{BASE_URL}/add_member", json=payload, headers=headers(admin_token), timeout=10)
        check(f"{case_name} -> 400", response.status_code == 400, f"got {response.status_code}: {response.text[:60]}")

    after = len(requests.get(f"{BASE_URL}/members", headers=headers(admin_token), timeout=10).json().get("members", []))
    check("Member count unchanged after bad inserts", before == after, f"before={before} after={after}")


def test_duplicate_username_rollback(admin_token):
    print("\n4. Duplicate Username Rollback")
    timestamp = int(time.time())
    username = f"duptest_{timestamp}"

    def make_payload(email_suffix):
        return {
            "name": "Dup Test",
            "age": 28,
            "email": f"dup{email_suffix}_{timestamp}@test.com",
            "contact_no": "9000000001",
            "username": username,
            "password": "Dup12345",
            "member_type": "Staff",
            "role": "user",
            "staff_role": "Receptionist",
            "shift": "Morning",
            "salary": 30000,
        }

    first = requests.post(f"{BASE_URL}/add_member", json=make_payload("a"), headers=headers(admin_token), timeout=10)
    check("First insert with unique username -> 201", first.status_code == 201, first.text[:80])

    before = len(requests.get(f"{BASE_URL}/members", headers=headers(admin_token), timeout=10).json().get("members", []))
    duplicate = requests.post(f"{BASE_URL}/add_member", json=make_payload("b"), headers=headers(admin_token), timeout=10)
    check("Duplicate username -> 409", duplicate.status_code == 409, duplicate.text[:80])
    after = len(requests.get(f"{BASE_URL}/members", headers=headers(admin_token), timeout=10).json().get("members", []))
    check("No ghost record after duplicate attempt", before == after, f"before={before} after={after}")


def test_appointment_rollback(admin_token):
    print("\n5. Appointment Booking Rollback")
    response = requests.post(f"{BASE_URL}/add_appointment", json={"date": "2026-04-10"}, headers=headers(admin_token), timeout=10)
    check("Missing appointment fields -> 400", response.status_code == 400, response.text[:80])

    response2 = requests.post(
        f"{BASE_URL}/add_appointment",
        json={"date": "2026-04-10", "doctor_id": 99999, "patient_id": 1, "slot_id": 99999},
        headers=headers(admin_token),
        timeout=10,
    )
    check("Non-existent doctor/slot -> 400 or 404", response2.status_code in (400, 404), response2.text[:80])


def test_rbac(admin_token, patient_token):
    print("\n6. RBAC")
    response = requests.get(f"{BASE_URL}/members", headers=headers(patient_token), timeout=10)
    check("Patient GET /members -> 403", response.status_code == 403, response.text[:80])

    response2 = requests.get(f"{BASE_URL}/audit_logs", headers=headers(patient_token), timeout=10)
    check("Patient GET /audit_logs -> 403", response2.status_code == 403, response2.text[:80])

    response3 = requests.get(f"{BASE_URL}/members", headers=headers(admin_token), timeout=10)
    check("Admin GET /members -> 200", response3.status_code == 200, response3.text[:80])


def test_medicine_rollback(admin_token):
    print("\n7. Medicine Add Rollback")
    before = len(requests.get(f"{BASE_URL}/medicines", headers=headers(admin_token), timeout=10).json().get("medicines", []))
    response = requests.post(f"{BASE_URL}/add_medicine", json={"medicine_name": "Incomplete"}, headers=headers(admin_token), timeout=10)
    check("Incomplete medicine payload -> 400", response.status_code == 400, response.text[:80])
    after = len(requests.get(f"{BASE_URL}/medicines", headers=headers(admin_token), timeout=10).json().get("medicines", []))
    check("Medicine count unchanged after bad insert", before == after, f"before={before} after={after}")


def main():
    print("=" * 60)
    print("  Module B - Failure Simulation & Rollback Tests")
    print("=" * 60)

    admin_token = login(ADMIN_USER, ADMIN_PASS)
    try:
        patient_token = login(PATIENT1_USER, PATIENT1_PASS)
    except RuntimeError:
        patient_token = None
        print("[WARN] patient1 not found - RBAC test will be skipped")

    test_unauthenticated()
    test_invalid_login()
    test_member_rollback(admin_token)
    test_duplicate_username_rollback(admin_token)
    test_appointment_rollback(admin_token)
    if patient_token:
        test_rbac(admin_token, patient_token)
    else:
        print("\n6. RBAC - SKIPPED")
    test_medicine_rollback(admin_token)

    print("\n" + "=" * 60)
    print(f"  TOTAL PASS: {PASS_COUNT}   FAIL: {FAIL_COUNT}")
    print("=" * 60)


if __name__ == "__main__":
    main()
