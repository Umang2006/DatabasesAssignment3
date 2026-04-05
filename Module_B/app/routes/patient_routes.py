import datetime
from flask import Blueprint, jsonify, request
try:
    from ..db import get_db_connection
    from ..auth import token_required
    from ..logger import log_action
except ImportError:
    from db import get_db_connection
    from auth import token_required
    from logger import log_action

patient_bp = Blueprint('patient', __name__)


def _serialize_time_rows(rows, date_keys=None, time_keys=None):
    date_keys = date_keys or []
    time_keys = time_keys or []
    for row in rows:
        for key in date_keys:
            if row.get(key) and hasattr(row[key], 'isoformat'):
                row[key] = row[key].isoformat()
        for key in time_keys:
            if row.get(key) and hasattr(row[key], 'seconds'):
                total = row[key].seconds
                row[key] = f"{total//3600:02d}:{(total%3600)//60:02d}"


@patient_bp.route('/doctors', methods=['GET'])
@token_required
def get_doctors():
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
    selected_date = request.args.get('date')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if selected_date:
        cursor.execute(
            """
            SELECT s.slot_id, s.start_time, s.end_time, s.status
            FROM slots s
            WHERE s.doctor_id = %s
              AND NOT EXISTS (
                  SELECT 1
                  FROM appointment a
                  WHERE a.doctor_id = s.doctor_id
                    AND a.slot_id = s.slot_id
                    AND a.appointment_date = %s
              )
            ORDER BY s.start_time
            """,
            (doctor_id, selected_date)
        )
    else:
        cursor.execute(
            "SELECT slot_id, start_time, end_time, status FROM slots WHERE doctor_id = %s ORDER BY start_time",
            (doctor_id,)
        )

    slots = cursor.fetchall()
    _serialize_time_rows(slots, time_keys=['start_time', 'end_time'])
    cursor.close()
    conn.close()
    return jsonify({"slots": slots}), 200


@patient_bp.route('/doctor/slots', methods=['GET'])
@token_required
def get_my_doctor_slots():
    if request.user.get('member_type') != 'Doctor':
        log_action(request.user['username'], "UNAUTHORIZED ACCESS ATTEMPT: Doctor slots")
        return jsonify({"error": "Access denied"}), 403

    selected_date = request.args.get('date') or datetime.date.today().isoformat()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT doctor_id FROM doctor WHERE member_id = %s", (request.user['member_id'],))
    doctor = cursor.fetchone()
    if not doctor:
        cursor.close()
        conn.close()
        return jsonify({"slots": []}), 200

    cursor.execute(
        """
        SELECT s.slot_id, s.start_time, s.end_time, s.status
        FROM slots s
        WHERE s.doctor_id = %s
          AND NOT EXISTS (
              SELECT 1
              FROM appointment a
              WHERE a.doctor_id = s.doctor_id
                AND a.slot_id = s.slot_id
                AND a.appointment_date = %s
          )
        ORDER BY s.start_time
        """,
        (doctor['doctor_id'], selected_date)
    )
    slots = cursor.fetchall()
    _serialize_time_rows(slots, time_keys=['start_time', 'end_time'])
    cursor.close()
    conn.close()
    return jsonify({"slots": slots}), 200


@patient_bp.route('/doctor/appointments', methods=['GET'])
@token_required
def doctor_appointments():
    if request.user.get('member_type') != 'Doctor':
        log_action(request.user['username'], "UNAUTHORIZED ACCESS ATTEMPT: Doctor appointments")
        return jsonify({"error": "Access denied"}), 403

    selected_date = request.args.get('date') or datetime.date.today().isoformat()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT doctor_id FROM doctor WHERE member_id = %s", (request.user['member_id'],))
    doctor = cursor.fetchone()
    if not doctor:
        cursor.close()
        conn.close()
        return jsonify({"appointments": [], "date": selected_date}), 200

    cursor.execute(
        """
        SELECT
            a.appointment_id,
            a.appointment_date,
            a.appointment_time,
            a.slot_id,
            p.patient_id,
            m.name AS patient_name
        FROM appointment a
        JOIN patient p ON a.patient_id = p.patient_id
        JOIN member m ON p.member_id = m.member_id
        WHERE a.doctor_id = %s
          AND a.appointment_date = %s
        ORDER BY a.appointment_time ASC
        """,
        (doctor['doctor_id'], selected_date)
    )
    appointments = cursor.fetchall()
    _serialize_time_rows(appointments, date_keys=['appointment_date'], time_keys=['appointment_time'])
    cursor.close()
    conn.close()
    return jsonify({"appointments": appointments, "date": selected_date}), 200


@patient_bp.route('/doctor/patients', methods=['GET'])
@token_required
def doctor_patients():
    if request.user.get('member_type') != 'Doctor':
        log_action(request.user['username'], "UNAUTHORIZED ACCESS ATTEMPT: Doctor patients")
        return jsonify({"error": "Access denied"}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT p.patient_id, m.name, m.contact_no, m.email
        FROM patient p
        JOIN member m ON p.member_id = m.member_id
        ORDER BY m.name
        """
    )
    patients = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify({"patients": patients}), 200


@patient_bp.route('/my_appointments', methods=['GET'])
@token_required
def my_appointments():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT patient_id FROM patient WHERE member_id = %s", (request.user['member_id'],))
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
        JOIN doctor d ON a.doctor_id = d.doctor_id
        JOIN member m ON d.member_id = m.member_id
        WHERE a.patient_id = %s
        ORDER BY a.appointment_date DESC, a.appointment_time DESC
    """, (patient['patient_id'],))

    appointments = cursor.fetchall()
    _serialize_time_rows(appointments, date_keys=['appointment_date'], time_keys=['appointment_time'])
    cursor.close()
    conn.close()
    return jsonify({"appointments": appointments}), 200
