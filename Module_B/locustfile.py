"""
Locust Load-Test File - Module B
"""

import json
import os
from datetime import date, timedelta

from locust import HttpUser, between, task


SEED_FILE = ".test_seed.json"


def load_seed():
    if os.path.exists(SEED_FILE):
        with open(SEED_FILE, "r", encoding="utf-8") as handle:
            return json.load(handle)
    return {}


SEED = load_seed()
RACE_DATE = os.environ.get("DMS_RACE_DATE", SEED.get("race_test", {}).get("date") or str(date.today() + timedelta(days=1)))
RACE_DOCTOR_ID = int(os.environ.get("DMS_RACE_DOCTOR_ID", SEED.get("race_test", {}).get("doctor_id") or 1))
RACE_SLOT_ID = int(os.environ.get("DMS_RACE_SLOT_ID", SEED.get("race_test", {}).get("slot_id") or 1))


def _login(client, user, password):
    response = client.post("/login", json={"user": user, "password": password}, name="/login", catch_response=True)
    if response.status_code == 200:
        return response.json().get("session_token")
    response.failure(f"Login failed: {response.text}")
    return None


class AdminUser(HttpUser):
    weight = 1
    wait_time = between(1, 3)

    def on_start(self):
        admin = SEED.get("admin", {})
        self.token = _login(self.client, admin.get("user", "admin"), admin.get("password", "password123"))
        self.headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @task(3)
    def list_members(self):
        self.client.get("/members", headers=self.headers, name="/members")

    @task(2)
    def list_medicines(self):
        self.client.get("/medicines", headers=self.headers, name="/medicines")

    @task(1)
    def view_audit_logs(self):
        self.client.get("/audit_logs", headers=self.headers, name="/audit_logs")


class PatientUser(HttpUser):
    weight = 5
    wait_time = between(1, 4)

    def on_start(self):
        patient_values = list(SEED.get("patients", {}).values())
        creds = patient_values[0] if patient_values else {"username": "patient1", "password": "Patient1pass", "patient_id": 1}
        self.patient_id = creds.get("patient_id", 1)
        self.token = _login(self.client, creds.get("username", "patient1"), creds.get("password", "Patient1pass"))
        self.headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @task(5)
    def browse_doctors(self):
        self.client.get("/doctors", headers=self.headers, name="/doctors")

    @task(3)
    def get_slots(self):
        self.client.get(f"/slots/{RACE_DOCTOR_ID}?date={RACE_DATE}", headers=self.headers, name="/slots/[doctor_id]")

    @task(2)
    def my_appointments(self):
        self.client.get("/my_appointments", headers=self.headers, name="/my_appointments")

    @task(2)
    def list_medicines(self):
        self.client.get("/medicines", headers=self.headers, name="/medicines")

    @task(1)
    def race_book_appointment(self):
        payload = {
            "date": RACE_DATE,
            "doctor_id": RACE_DOCTOR_ID,
            "patient_id": self.patient_id,
            "slot_id": RACE_SLOT_ID,
        }
        with self.client.post("/add_appointment", json=payload, headers=self.headers, name="/add_appointment", catch_response=True) as response:
            if response.status_code in (201, 409):
                response.success()
            else:
                response.failure(f"Unexpected status {response.status_code}: {response.text[:80]}")


class DoctorUser(HttpUser):
    weight = 2
    wait_time = between(2, 5)

    def on_start(self):
        doctor = SEED.get("doctors", {}).get("doctor1", {})
        self.token = _login(self.client, doctor.get("username", "doctor1"), doctor.get("password", "Doctor1pass"))
        self.headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @task(3)
    def check_schedule(self):
        self.client.get(f"/doctor/appointments?date={RACE_DATE}", headers=self.headers, name="/doctor/appointments")

    @task(2)
    def available_slots(self):
        self.client.get(f"/doctor/slots?date={RACE_DATE}", headers=self.headers, name="/doctor/slots")

    @task(1)
    def list_patients(self):
        self.client.get("/doctor/patients", headers=self.headers, name="/doctor/patients")
