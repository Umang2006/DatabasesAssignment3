"""
Module B - Test Data Seeder
===========================
Creates test patient / doctor accounts and inserts slots directly in DB.

Run:
    python seed_test_data.py

Outputs:
    .test_seed.json
"""

import json
import os
from datetime import date, timedelta

import requests

from app.db import get_db_connection


BASE_URL = os.environ.get("DMS_BASE_URL", "http://localhost:5000")
ADMIN_CREDS = {
    "user": os.environ.get("DMS_ADMIN_USER", "admin"),
    "password": os.environ.get("DMS_ADMIN_PASS", "password123"),
}
SEED_FILE = ".test_seed.json"


def login(creds):
    response = requests.post(f"{BASE_URL}/login", json=creds, timeout=10)
    response.raise_for_status()
    return response.json()["session_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def create_member(token, payload):
    response = requests.post(
        f"{BASE_URL}/add_member",
        json=payload,
        headers=auth(token),
        timeout=10,
    )
    if response.status_code == 201:
        body = response.json()
        print(f"  [CREATED] {payload['username']} (member_id={body['member_id']})")
        return body["member_id"]
    if response.status_code == 409:
        print(f"  [EXISTS]  {payload['username']}")
        return None
    raise RuntimeError(f"Failed to create {payload['username']}: {response.status_code} {response.text}")


def fetch_member_map(token):
    response = requests.get(f"{BASE_URL}/members", headers=auth(token), timeout=10)
    response.raise_for_status()
    members = response.json().get("members", [])
    return {member.get("username"): member for member in members if member.get("username")}


def fetch_doctor_id_by_username(username):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT d.doctor_id
        FROM doctor d
        JOIN users u ON d.member_id = u.member_id
        WHERE u.username = %s
        """,
        (username,),
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row["doctor_id"] if row else None


def fetch_patient_id_by_username(username):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT p.patient_id
        FROM patient p
        JOIN users u ON p.member_id = u.member_id
        WHERE u.username = %s
        """,
        (username,),
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row["patient_id"] if row else None


def ensure_slots(doctor_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    desired = [
        ("09:00:00", "09:30:00"),
        ("09:30:00", "10:00:00"),
        ("10:00:00", "10:30:00"),
    ]
    slot_ids = []
    for start_time, end_time in desired:
        cursor.execute(
            """
            SELECT slot_id
            FROM slots
            WHERE doctor_id = %s AND start_time = %s AND end_time = %s
            """,
            (doctor_id, start_time, end_time),
        )
        existing = cursor.fetchone()
        if existing:
            slot_ids.append(existing["slot_id"])
            continue

        cursor2 = conn.cursor()
        cursor2.execute(
            """
            INSERT INTO slots (start_time, end_time, status, doctor_id)
            VALUES (%s, %s, %s, %s)
            """,
            (start_time, end_time, "Available", doctor_id),
        )
        conn.commit()
        slot_ids.append(cursor2.lastrowid)
        cursor2.close()
        print(f"  [SLOT]    Added {start_time}-{end_time} for doctor_id={doctor_id}")

    cursor.close()
    conn.close()
    return slot_ids


def write_seed_file(data):
    with open(SEED_FILE, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)


def main():
    print("=" * 50)
    print("  Module B - Seeding Test Accounts")
    print("=" * 50)

    token = login(ADMIN_CREDS)
    print("[OK] Logged in as admin\n")

    patients = [
        {
            "name": "Test Patient One",
            "age": 25,
            "email": "patient1@moduleb.test",
            "contact_no": "9000000001",
            "username": "patient1",
            "password": "Patient1pass",
            "member_type": "Patient",
            "role": "user",
            "gender": "Male",
            "address": "1 Test Street, Gandhinagar",
            "blood_group": "O+",
        },
        {
            "name": "Test Patient Two",
            "age": 30,
            "email": "patient2@moduleb.test",
            "contact_no": "9000000002",
            "username": "patient2",
            "password": "Patient2pass",
            "member_type": "Patient",
            "role": "user",
            "gender": "Female",
            "address": "2 Test Street, Gandhinagar",
            "blood_group": "A+",
        },
    ]

    doctors = [
        {
            "name": "Dr Load Test",
            "age": 40,
            "email": "doctor1@moduleb.test",
            "contact_no": "9000000010",
            "username": "doctor1",
            "password": "Doctor1pass",
            "member_type": "Doctor",
            "role": "user",
            "specialization": "General Medicine",
            "qualification": "MBBS",
            "shift": "Morning",
            "consultation_fee": 300,
            "salary": 80000,
        },
    ]

    print("Creating patient accounts...")
    for payload in patients:
        create_member(token, payload)

    print("\nCreating doctor accounts...")
    for payload in doctors:
        create_member(token, payload)

    member_map = fetch_member_map(token)
    doctor_id = fetch_doctor_id_by_username("doctor1")
    patient1_id = fetch_patient_id_by_username("patient1")
    patient2_id = fetch_patient_id_by_username("patient2")
    slot_ids = ensure_slots(doctor_id) if doctor_id else []
    race_date = str(date.today() + timedelta(days=1))

    seed_data = {
        "base_url": BASE_URL,
        "admin": ADMIN_CREDS,
        "patients": {
            "patient1": {
                "username": "patient1",
                "password": "Patient1pass",
                "member_id": member_map.get("patient1", {}).get("member_id"),
                "patient_id": patient1_id,
            },
            "patient2": {
                "username": "patient2",
                "password": "Patient2pass",
                "member_id": member_map.get("patient2", {}).get("member_id"),
                "patient_id": patient2_id,
            },
        },
        "doctors": {
            "doctor1": {
                "username": "doctor1",
                "password": "Doctor1pass",
                "member_id": member_map.get("doctor1", {}).get("member_id"),
                "doctor_id": doctor_id,
                "slot_ids": slot_ids,
            }
        },
        "race_test": {
            "doctor_id": doctor_id,
            "slot_id": slot_ids[0] if slot_ids else None,
            "date": race_date,
        },
    }
    write_seed_file(seed_data)

    print("\n[DONE] Test seed written to .test_seed.json")
    print(json.dumps(seed_data, indent=2))


if __name__ == "__main__":
    main()
