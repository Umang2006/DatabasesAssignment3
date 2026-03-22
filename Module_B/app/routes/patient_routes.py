from flask import Blueprint, jsonify, request
from db import get_db_connection
from auth import token_required
from logger import log_action

patient_bp = Blueprint('patient', __name__)


@patient_bp.route('/doctors', methods=['GET'])
@token_required
def get_doctors():
    """
    Returns all doctors with their name and specialization.
    Used by the patient UI to populate the doctor dropdown.
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT d.doctor_id, m.name, d.specialization, d.consultation_fee, d.shift
        FROM doctor d
        JOIN member m ON d.member_id = m.member_id
        ORDER BY m.name
    """)
    doctors = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify({"doctors": doctors}), 200


@patient_bp.route('/slots/<int:doctor_id>', methods=['GET'])
@token_required
def get_slots(doctor_id):
    """
    Returns all slots for a given doctor.
    Patient picks a slot to book an appointment.
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT slot_id, start_time, end_time, status FROM slots WHERE doctor_id = %s ORDER BY start_time",
        (doctor_id,)
    )
    slots = cursor.fetchall()
    # Convert timedelta to string for JSON serialization
    for s in slots:
        if hasattr(s['start_time'], 'seconds'):
            total = s['start_time'].seconds
            s['start_time'] = f"{total//3600:02d}:{(total%3600)//60:02d}"
        if hasattr(s['end_time'], 'seconds'):
            total = s['end_time'].seconds
            s['end_time'] = f"{total//3600:02d}:{(total%3600)//60:02d}"
    cursor.close()
    conn.close()
    return jsonify({"slots": slots}), 200


@patient_bp.route('/my_appointments', methods=['GET'])
@token_required
def my_appointments():
    """
    Returns appointments belonging to the currently logged-in patient.
    Joins with doctor/member to show doctor name instead of just an ID.
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Resolve member_id → patient_id
    cursor.execute(
        "SELECT patient_id FROM patient WHERE member_id = %s", (request.user['member_id'],)
    )
    patient = cursor.fetchone()
    if not patient:
        cursor.close()
        conn.close()
        return jsonify({"appointments": []}), 200

    cursor.execute("""
        SELECT
            a.appointment_id,
            a.appointment_date,
            a.appointment_time,
            a.slot_id,
            a.doctor_id,
            m.name AS doctor_name
        FROM appointment a
        JOIN doctor d  ON a.doctor_id  = d.doctor_id
        JOIN member m  ON d.member_id  = m.member_id
        WHERE a.patient_id = %s
        ORDER BY a.appointment_date DESC, a.appointment_time DESC
    """, (patient['patient_id'],))

    appointments = cursor.fetchall()

    # Serialize date/time objects
    for appt in appointments:
        if hasattr(appt['appointment_date'], 'isoformat'):
            appt['appointment_date'] = appt['appointment_date'].isoformat()
        if hasattr(appt['appointment_time'], 'seconds'):
            total = appt['appointment_time'].seconds
            appt['appointment_time'] = f"{total//3600:02d}:{(total%3600)//60:02d}"

    cursor.close()
    conn.close()
    return jsonify({"appointments": appointments}), 200