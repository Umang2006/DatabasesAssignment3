"""
Module B - Concurrent Workload & Stress Testing
"""

import json
import os
import threading
import time
from collections import Counter
from datetime import date, timedelta

import requests


BASE_URL = os.environ.get("DMS_BASE_URL", "http://localhost:5000")
SEED_FILE = ".test_seed.json"

RESULTS = []
RESULTS_LOCK = threading.Lock()


def load_seed():
    if os.path.exists(SEED_FILE):
        with open(SEED_FILE, "r", encoding="utf-8") as handle:
            return json.load(handle)
    return {}


SEED = load_seed()
ADMIN_USER = os.environ.get("DMS_ADMIN_USER", SEED.get("admin", {}).get("user", "admin"))
ADMIN_PASS = os.environ.get("DMS_ADMIN_PASS", SEED.get("admin", {}).get("password", "password123"))
PATIENT1 = {
    "user": os.environ.get("DMS_PATIENT1_USER", SEED.get("patients", {}).get("patient1", {}).get("username", "patient1")),
    "password": os.environ.get("DMS_PATIENT1_PASS", SEED.get("patients", {}).get("patient1", {}).get("password", "Patient1pass")),
}
PATIENT2 = {
    "user": os.environ.get("DMS_PATIENT2_USER", SEED.get("patients", {}).get("patient2", {}).get("username", "patient2")),
    "password": os.environ.get("DMS_PATIENT2_PASS", SEED.get("patients", {}).get("patient2", {}).get("password", "Patient2pass")),
}
RACE_DOCTOR_ID = int(os.environ.get("DMS_RACE_DOCTOR_ID", SEED.get("race_test", {}).get("doctor_id") or 1))
RACE_SLOT_ID = int(os.environ.get("DMS_RACE_SLOT_ID", SEED.get("race_test", {}).get("slot_id") or 1))
RACE_DATE = os.environ.get("DMS_RACE_DATE", SEED.get("race_test", {}).get("date") or str(date.today() + timedelta(days=1)))


def login(credentials):
    response = requests.post(f"{BASE_URL}/login", json=credentials, timeout=10)
    if response.status_code == 200:
        return response.json().get("session_token")
    return None


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def record(test_name, status_code, extra=""):
    with RESULTS_LOCK:
        RESULTS.append({
            "test": test_name,
            "status": status_code,
            "extra": extra,
            "ts": time.time(),
        })


def get_member_id_by_username(admin_token, username):
    response = requests.get(f"{BASE_URL}/members", headers=auth_headers(admin_token), timeout=10)
    response.raise_for_status()
    members = response.json().get("members", [])
    for member in members:
        if member.get("username") == username:
            return member.get("member_id")
    return None


def get_patient_id_from_seed(username):
    return SEED.get("patients", {}).get(username, {}).get("patient_id")


def book_appointment(token, patient_id, thread_id):
    payload = {
        "date": RACE_DATE,
        "doctor_id": RACE_DOCTOR_ID,
        "patient_id": patient_id,
        "slot_id": RACE_SLOT_ID,
    }
    try:
        response = requests.post(
            f"{BASE_URL}/add_appointment",
            json=payload,
            headers=auth_headers(token),
            timeout=10,
        )
        record("race_condition_booking", response.status_code, f"thread={thread_id} body={response.text[:120]}")
    except Exception as exc:
        record("race_condition_booking", -1, str(exc))


def test_race_condition(admin_token, patient_id, num_threads=15):
    print(f"\n[TEST 1] Race Condition - {num_threads} threads on doctor={RACE_DOCTOR_ID} slot={RACE_SLOT_ID} date={RACE_DATE}")
    threads = []
    barrier = threading.Barrier(num_threads)

    def run(tid):
        barrier.wait()
        book_appointment(admin_token, patient_id, tid)

    for idx in range(num_threads):
        thread = threading.Thread(target=run, args=(idx,))
        threads.append(thread)
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    race_results = [entry for entry in RESULTS if entry["test"] == "race_condition_booking"]
    successes = [entry for entry in race_results if entry["status"] == 201]
    conflicts = [entry for entry in race_results if entry["status"] == 409]

    print(f"  201 Created : {len(successes)}")
    print(f"  409 Conflict: {len(conflicts)}")
    print(f"  Other       : {len(race_results) - len(successes) - len(conflicts)}")
    assert len(successes) <= 1, f"FAIL - {len(successes)} bookings succeeded for the same slot"
    print("  PASS - at most 1 booking succeeded")


def create_member_thread(admin_token, username, thread_id):
    payload = {
        "name": f"Test User {thread_id}",
        "age": 25,
        "email": f"testuser{thread_id}_{int(time.time())}@test.com",
        "contact_no": f"9{thread_id:09d}",
        "username": username,
        "password": "Test1234",
        "member_type": "Patient",
        "role": "user",
        "gender": "Male",
        "address": "Test Street",
        "blood_group": "O+",
    }
    try:
        response = requests.post(
            f"{BASE_URL}/add_member",
            json=payload,
            headers=auth_headers(admin_token),
            timeout=10,
        )
        record("concurrent_member_create", response.status_code, f"thread={thread_id} user={username} body={response.text[:120]}")
    except Exception as exc:
        record("concurrent_member_create", -1, str(exc))


def test_concurrent_member_creation(admin_token, num_threads=10):
    print(f"\n[TEST 2] Concurrent Member Creation - {num_threads} threads")
    shared_username = f"concuser_{int(time.time())}"
    threads = []
    barrier = threading.Barrier(num_threads)

    def run(tid):
        barrier.wait()
        create_member_thread(admin_token, shared_username, tid)

    for idx in range(num_threads):
        thread = threading.Thread(target=run, args=(idx,))
        threads.append(thread)
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    results = [entry for entry in RESULTS if entry["test"] == "concurrent_member_create"]
    successes = [entry for entry in results if entry["status"] == 201]
    conflicts = [entry for entry in results if entry["status"] in (400, 409)]

    print(f"  201 Created : {len(successes)}")
    print(f"  409/400     : {len(conflicts)}")
    assert len(successes) <= 1, f"FAIL - {len(successes)} members created with same username"
    print("  PASS - username uniqueness enforced")


def test_isolation(token1, patient2_member_id):
    print("\n[TEST 3] Isolation - Patient cannot access another patient's portfolio")
    response = requests.get(
        f"{BASE_URL}/portfolio/{patient2_member_id}",
        headers=auth_headers(token1),
        timeout=10,
    )
    record("isolation_portfolio", response.status_code, f"patient1 accessing patient2 portfolio: {response.text[:120]}")
    print(f"  Status: {response.status_code}")
    assert response.status_code == 403, f"FAIL - expected 403, got {response.status_code}"
    print("  PASS - 403 returned correctly")


def test_failure_simulation(admin_token):
    print("\n[TEST 4] Failure Simulation - Invalid / partial payloads")
    cases = [
        ("missing_fields_add_member", "/add_member", {"name": "Incomplete"}),
        ("invalid_age_add_member", "/add_member", {
            "name": "Bad",
            "age": -5,
            "email": "a@b.com",
            "contact_no": "9000000000",
            "username": "baduser1",
            "password": "Pass1234",
            "member_type": "Patient",
            "role": "user",
            "gender": "Male",
            "address": "X",
        }),
        ("bad_medicine_missing", "/add_medicine", {"medicine_name": "OnlyName"}),
        ("appointment_missing_fields", "/add_appointment", {"date": RACE_DATE}),
    ]
    for desc, endpoint, payload in cases:
        response = requests.post(
            f"{BASE_URL}{endpoint}",
            json=payload,
            headers=auth_headers(admin_token),
            timeout=10,
        )
        record("failure_simulation", response.status_code, f"{desc}: {response.text[:100]}")
        ok = response.status_code in (400, 401, 403, 404, 409, 422)
        print(f"  {desc}: status={response.status_code} {'PASS' if ok else 'FAIL'}")


def test_rollback(admin_token):
    print("\n[TEST 5] Rollback Verification - duplicate email")
    timestamp = int(time.time())
    email = f"rollback_{timestamp}@test.com"
    payload_good = {
        "name": "Rollback Test",
        "age": 30,
        "email": email,
        "contact_no": "9876543210",
        "username": f"rbtest_{timestamp}",
        "password": "Test1234",
        "member_type": "Patient",
        "role": "user",
        "gender": "Female",
        "address": "123 Rollback Lane",
        "blood_group": "A+",
    }
    first = requests.post(f"{BASE_URL}/add_member", json=payload_good, headers=auth_headers(admin_token), timeout=10)
    record("rollback_first_insert", first.status_code, first.text[:100])
    print(f"  First insert status: {first.status_code}")
    if first.status_code != 201:
        print("  SKIP - first insert failed")
        return

    before = len(requests.get(f"{BASE_URL}/members", headers=auth_headers(admin_token), timeout=10).json().get("members", []))
    payload_dup = {**payload_good, "username": f"rbtest2_{timestamp}"}
    duplicate = requests.post(f"{BASE_URL}/add_member", json=payload_dup, headers=auth_headers(admin_token), timeout=10)
    record("rollback_dup_insert", duplicate.status_code, duplicate.text[:100])
    print(f"  Duplicate insert status: {duplicate.status_code}")

    after = len(requests.get(f"{BASE_URL}/members", headers=auth_headers(admin_token), timeout=10).json().get("members", []))
    print(f"  Members before: {before}, after: {after}")
    assert before == after, "FAIL - member count changed after failed duplicate insert"
    print("  PASS - rollback confirmed")


def stress_test(token, num_requests=200, min_success_rate=85):
    print(f"\n[TEST 6] Stress Test - {num_requests} GET /medicines requests")
    start = time.time()
    status_counts = Counter()

    def do_request():
        try:
            response = requests.get(f"{BASE_URL}/medicines", headers=auth_headers(token), timeout=10)
            record("stress_get_medicines", response.status_code)
            status_counts[response.status_code] += 1
        except Exception as exc:
            record("stress_get_medicines", -1, str(exc))
            status_counts[-1] += 1

    threads = [threading.Thread(target=do_request) for _ in range(num_requests)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    elapsed = time.time() - start
    rps = num_requests / elapsed if elapsed else 0
    success_rate = (status_counts.get(200, 0) / num_requests) * 100

    print(f"  Total time : {elapsed:.2f}s")
    print(f"  Throughput : {rps:.1f} req/s")
    print(f"  Status dist: {dict(status_counts)}")
    print(f"  Success rate: {success_rate:.1f}%")
    assert success_rate >= min_success_rate, (
        f"FAIL - success rate {success_rate:.1f}% is below {min_success_rate}%"
    )
    print(f"  PASS - >={min_success_rate}% requests succeeded")


def main():
    print("=" * 60)
    print("  Module B: Multi-User Behaviour & Stress Testing")
    print("=" * 60)

    admin_token = login({"user": ADMIN_USER, "password": ADMIN_PASS})
    assert admin_token, "Could not log in as admin - check credentials"
    print("[OK] Admin logged in")

    token1 = login(PATIENT1)
    token2 = login(PATIENT2)
    patient1_member_id = get_member_id_by_username(admin_token, PATIENT1["user"])
    patient2_member_id = get_member_id_by_username(admin_token, PATIENT2["user"])
    race_patient_id = get_patient_id_from_seed("patient1") or 1

    test_race_condition(admin_token, patient_id=race_patient_id)
    test_concurrent_member_creation(admin_token)
    if token1 and token2 and patient2_member_id:
        test_isolation(token1, patient2_member_id)
    else:
        reason = f"token1={bool(token1)} token2={bool(token2)} patient2_member_id={patient2_member_id}"
        record("isolation_skipped", 0, reason)
        print("\n[TEST 3] SKIPPED - patient accounts not found")
    test_failure_simulation(admin_token)
    test_rollback(admin_token)
    stress_test(admin_token, num_requests=200)

    print("\n" + "=" * 60)
    print("  RESULTS SUMMARY")
    print("=" * 60)
    grouped = {}
    for result in RESULTS:
        grouped.setdefault(result["test"], []).append(result["status"])
    for test_name, statuses in grouped.items():
        print(f"  {test_name}: {dict(Counter(statuses))}")

    with open("test_results.json", "w", encoding="utf-8") as handle:
        json.dump(RESULTS, handle, indent=2, default=str)
    print("\n  Raw results saved to test_results.json")


if __name__ == "__main__":
    main()
