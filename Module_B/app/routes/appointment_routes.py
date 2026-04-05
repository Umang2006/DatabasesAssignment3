from mysql.connector.errors import IntegrityError
from flask import Blueprint, jsonify, request
try:
    from ..db import get_db_connection
    from ..auth import token_required
    from ..logger import log_action
except ImportError:
    from db import get_db_connection
    from auth import token_required
    from logger import log_action

appointment_bp = Blueprint('appointment', __name__)


def _get_doctor_id_for_member(cursor, member_id):
    cursor.execute("SELECT doctor_id FROM doctor WHERE member_id = %s", (member_id,))
    doctor = cursor.fetchone()
    return doctor['doctor_id'] if doctor else None


def _get_patient_id_for_member(cursor, member_id):
    cursor.execute("SELECT patient_id FROM patient WHERE member_id = %s", (member_id,))
    patient = cursor.fetchone()
    return patient['patient_id'] if patient else None


def _get_slot_details(cursor, slot_id, doctor_id):
    cursor.execute(
        "SELECT slot_id, start_time FROM slots WHERE slot_id = %s AND doctor_id = %s FOR UPDATE",
        (slot_id, doctor_id)
    )
    return cursor.fetchone()


def _has_conflict(cursor, doctor_id, appointment_date, appointment_time, slot_id, exclude_id=None):
    query = """
        SELECT appointment_id
        FROM appointment
        WHERE doctor_id = %s
          AND appointment_date = %s
          AND (slot_id = %s OR appointment_time = %s)
    """
    params = [doctor_id, appointment_date, slot_id, appointment_time]
    if exclude_id is not None:
        query += " AND appointment_id <> %s"
        params.append(exclude_id)
    cursor.execute(query, tuple(params))
    return cursor.fetchone() is not None


def _serialize_appointments(appointments):
    for appt in appointments:
        if appt.get('appointment_date') and hasattr(appt['appointment_date'], 'isoformat'):
            appt['appointment_date'] = appt['appointment_date'].isoformat()
        if appt.get('appointment_time') and hasattr(appt['appointment_time'], 'seconds'):
            total = appt['appointment_time'].seconds
            appt['appointment_time'] = f"{total // 3600:02d}:{(total % 3600) // 60:02d}"


@appointment_bp.route('/appointments', methods=['GET'])
@token_required
def get_appointments():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT
            a.appointment_id,
            a.appointment_date,
            a.appointment_time,
            a.doctor_id,
            a.patient_id,
            a.slot_id,
            m_doc.name AS doctor_name,
            m_pat.name AS patient_name
        FROM appointment a
        JOIN doctor d ON a.doctor_id = d.doctor_id
        JOIN member m_doc ON d.member_id = m_doc.member_id
        JOIN patient p ON a.patient_id = p.patient_id
        JOIN member m_pat ON p.member_id = m_pat.member_id
        ORDER BY a.appointment_id DESC
        LIMIT 20
    """)
    appointments = cursor.fetchall()
    _serialize_appointments(appointments)
    cursor.close()
    conn.close()
    return jsonify({"appointments": appointments}), 200


@appointment_bp.route('/appointments/<int:id>', methods=['GET'])
@token_required
def get_appointment(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM appointment WHERE appointment_id = %s", (id,))
    appointment = cursor.fetchone()
    cursor.close()
    conn.close()
    if not appointment:
        return jsonify({"error": "Appointment not found"}), 404
    _serialize_appointments([appointment])
    return jsonify({"appointment": appointment}), 200


@appointment_bp.route('/add_appointment', methods=['POST'])
@token_required
def add_appointment():
    data = request.get_json()
    required = ['date', 'doctor_id', 'patient_id', 'slot_id']
    if not data or not all(k in data for k in required):
        return jsonify({"error": "Missing required fields"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        slot = _get_slot_details(cursor, data['slot_id'], data['doctor_id'])
        if not slot:
            return jsonify({"error": "Selected slot does not belong to this doctor"}), 400

        patient_id = _get_patient_id_for_member(cursor, request.user['member_id'])
        if request.user.get('role') != 'admin' and patient_id != data['patient_id']:
            log_action(request.user['username'], "UNAUTHORIZED CREATE ATTEMPT: Appointment for another patient")
            return jsonify({"error": "Access denied"}), 403

        if _has_conflict(cursor, data['doctor_id'], data['date'], slot['start_time'], data['slot_id']):
            return jsonify({"error": "This slot is already booked for the selected doctor and date"}), 409

        cursor2 = conn.cursor()
        cursor2.execute(
            """
            INSERT INTO appointment (appointment_date, appointment_time, doctor_id, patient_id, slot_id)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (data['date'], slot['start_time'], data['doctor_id'], data['patient_id'], data['slot_id'])
        )
        conn.commit()
        new_id = cursor2.lastrowid
        cursor2.close()
        log_action(request.user['username'], f"CREATED APPOINTMENT {new_id}")
        return jsonify({"message": "Appointment created successfully!", "appointment_id": new_id}), 201
    except IntegrityError:
        conn.rollback()
        return jsonify({"error": "This slot is already booked for the selected doctor and date"}), 409
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"Failed to create appointment: {str(e)}"}), 400
    finally:
        cursor.close()
        conn.close()


@appointment_bp.route('/doctor/add_appointment', methods=['POST'])
@token_required
def doctor_add_appointment():
    if request.user.get('member_type') != 'Doctor':
        log_action(request.user['username'], "UNAUTHORIZED CREATE ATTEMPT: Doctor appointment")
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json()
    required = ['date', 'patient_id', 'slot_id']
    if not data or not all(k in data for k in required):
        return jsonify({"error": "Missing required fields"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        doctor_id = _get_doctor_id_for_member(cursor, request.user['member_id'])
        if not doctor_id:
            return jsonify({"error": "Doctor record not found"}), 404

        slot = _get_slot_details(cursor, data['slot_id'], doctor_id)
        if not slot:
            return jsonify({"error": "Selected slot does not belong to you"}), 400

        cursor.execute("SELECT patient_id FROM patient WHERE patient_id = %s", (data['patient_id'],))
        patient = cursor.fetchone()
        if not patient:
            return jsonify({"error": "Patient not found"}), 404

        if _has_conflict(cursor, doctor_id, data['date'], slot['start_time'], data['slot_id']):
            return jsonify({"error": "This slot is already booked for that date"}), 409

        cursor2 = conn.cursor()
        cursor2.execute(
            """
            INSERT INTO appointment (appointment_date, appointment_time, doctor_id, patient_id, slot_id)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (data['date'], slot['start_time'], doctor_id, data['patient_id'], data['slot_id'])
        )
        conn.commit()
        new_id = cursor2.lastrowid
        cursor2.close()
        log_action(request.user['username'], f"CREATED DOCTOR APPOINTMENT {new_id} FOR PATIENT {data['patient_id']}")
        return jsonify({"message": "Appointment slot added successfully", "appointment_id": new_id}), 201
    except IntegrityError:
        conn.rollback()
        return jsonify({"error": "This slot is already booked for that date"}), 409
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"Failed to add appointment slot: {str(e)}"}), 400
    finally:
        cursor.close()
        conn.close()


@appointment_bp.route('/update_appointment/<int:id>', methods=['PUT'])
@token_required
def update_appointment(id):
    data = request.get_json() or {}

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM appointment WHERE appointment_id = %s", (id,))
    appointment = cursor.fetchone()
    if not appointment:
        cursor.close()
        conn.close()
        return jsonify({"error": "Appointment not found"}), 404

    if request.user['role'] != 'admin':
        patient_id = _get_patient_id_for_member(cursor, request.user['member_id'])
        if appointment['patient_id'] != patient_id:
            log_action(request.user['username'], f"UNAUTHORIZED UPDATE ATTEMPT: Appointment {id}")
            cursor.close()
            conn.close()
            return jsonify({"error": "Access denied"}), 403

    new_date = data.get('date', appointment['appointment_date'])
    new_doctor_id = data.get('doctor_id', appointment['doctor_id'])
    new_patient_id = data.get('patient_id', appointment['patient_id'])
    new_slot_id = data.get('slot_id', appointment['slot_id'])

    slot = _get_slot_details(cursor, new_slot_id, new_doctor_id)
    if not slot:
        cursor.close()
        conn.close()
        return jsonify({"error": "Selected slot does not belong to this doctor"}), 400

    new_time = data.get('time', appointment['appointment_time'])
    if 'slot_id' in data or 'doctor_id' in data:
        new_time = slot['start_time']

    if _has_conflict(cursor, new_doctor_id, new_date, new_time, new_slot_id, exclude_id=id):
        cursor.close()
        conn.close()
        return jsonify({"error": "This slot is already booked for the selected doctor and date"}), 409

    try:
        cursor2 = conn.cursor()
        cursor2.execute(
            """
            UPDATE appointment
            SET appointment_date = %s,
                appointment_time = %s,
                doctor_id = %s,
                patient_id = %s,
                slot_id = %s
            WHERE appointment_id = %s
            """,
            (new_date, new_time, new_doctor_id, new_patient_id, new_slot_id, id)
        )
        conn.commit()
        cursor2.close()
        log_action(request.user['username'], f"UPDATED APPOINTMENT {id}")
        return jsonify({"message": f"Appointment {id} updated successfully"}), 200
    except IntegrityError:
        conn.rollback()
        return jsonify({"error": "This slot is already booked for the selected doctor and date"}), 409
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"Update failed: {str(e)}"}), 400
    finally:
        cursor.close()
        conn.close()


@appointment_bp.route('/delete_appointment/<int:id>', methods=['DELETE'])
@token_required
def delete_appointment(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM appointment WHERE appointment_id = %s", (id,))
    appointment = cursor.fetchone()
    if not appointment:
        cursor.close()
        conn.close()
        return jsonify({"error": "Appointment not found"}), 404

    if request.user['role'] != 'admin':
        patient_id = _get_patient_id_for_member(cursor, request.user['member_id'])
        if appointment['patient_id'] != patient_id:
            log_action(request.user['username'], f"UNAUTHORIZED DELETE ATTEMPT: Appointment {id}")
            cursor.close()
            conn.close()
            return jsonify({"error": "Access denied"}), 403

    cursor2 = conn.cursor()
    cursor2.execute("DELETE FROM appointment WHERE appointment_id = %s", (id,))
    conn.commit()
    cursor2.close()
    cursor.close()
    conn.close()
    log_action(request.user['username'], f"DELETED APPOINTMENT {id}")
    return jsonify({"message": "Appointment deleted successfully!"}), 200
