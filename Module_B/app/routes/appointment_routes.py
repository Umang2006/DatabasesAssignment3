from flask import Blueprint, jsonify, request
from db import get_db_connection
from auth import token_required, admin_required
from logger import log_action

appointment_bp = Blueprint('appointment', __name__)


# READ - all appointments with doctor & patient names (admin)
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
            m_doc.name  AS doctor_name,
            m_pat.name  AS patient_name
        FROM appointment a
        JOIN doctor  d     ON a.doctor_id  = d.doctor_id
        JOIN member  m_doc ON d.member_id  = m_doc.member_id
        JOIN patient p     ON a.patient_id = p.patient_id
        JOIN member  m_pat ON p.member_id  = m_pat.member_id
        ORDER BY a.appointment_id DESC
        LIMIT 20
    """)
    appointments = cursor.fetchall()
    # Serialize date / timedelta fields
    for appt in appointments:
        if hasattr(appt.get('appointment_date'), 'isoformat'):
            appt['appointment_date'] = appt['appointment_date'].isoformat()
        if hasattr(appt.get('appointment_time'), 'seconds'):
            total = appt['appointment_time'].seconds
            appt['appointment_time'] = f"{total // 3600:02d}:{(total % 3600) // 60:02d}"
    cursor.close()
    conn.close()
    return jsonify({"appointments": appointments}), 200


# READ - single appointment
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
    return jsonify({"appointment": appointment}), 200


# CREATE
@appointment_bp.route('/add_appointment', methods=['POST'])
@token_required
def add_appointment():
    data = request.get_json()
    required = ['date', 'time', 'doctor_id', 'patient_id', 'slot_id']
    if not all(k in data for k in required):
        return jsonify({"error": "Missing required fields"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO appointment (appointment_date, appointment_time, doctor_id, patient_id, slot_id) "
            "VALUES (%s, %s, %s, %s, %s)",
            (data['date'], data['time'], data['doctor_id'], data['patient_id'], data['slot_id'])
        )
        conn.commit()
        new_id = cursor.lastrowid
        log_action(request.user['username'], f"CREATED APPOINTMENT {new_id}")
        return jsonify({"message": "Appointment created successfully!", "appointment_id": new_id}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"Failed to create appointment: {str(e)}"}), 400
    finally:
        cursor.close()
        conn.close()


# UPDATE
@appointment_bp.route('/update_appointment/<int:id>', methods=['PUT'])
@token_required
def update_appointment(id):
    """
    Update appointment date, time, doctor, patient, or slot.
    Only admins OR the patient who owns the appointment can update it.
    """
    data = request.get_json()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Check appointment exists
    cursor.execute("SELECT * FROM appointment WHERE appointment_id = %s", (id,))
    appointment = cursor.fetchone()
    if not appointment:
        cursor.close()
        conn.close()
        return jsonify({"error": "Appointment not found"}), 404

    # RBAC: regular users can only update their own appointments
    if request.user['role'] != 'admin':
        cursor.execute(
            "SELECT patient_id FROM patient WHERE member_id = %s", (request.user['member_id'],)
        )
        patient = cursor.fetchone()
        if not patient or appointment['patient_id'] != patient['patient_id']:
            log_action(request.user['username'], f"UNAUTHORIZED UPDATE ATTEMPT: Appointment {id}")
            cursor.close()
            conn.close()
            return jsonify({"error": "Access denied"}), 403

    # Build dynamic update
    fields = []
    values = []
    allowed = {
        'date': 'appointment_date',
        'time': 'appointment_time',
        'doctor_id': 'doctor_id',
        'patient_id': 'patient_id',
        'slot_id': 'slot_id'
    }
    for key, col in allowed.items():
        if key in data:
            fields.append(f"{col} = %s")
            values.append(data[key])

    if not fields:
        cursor.close()
        conn.close()
        return jsonify({"error": "No valid fields to update"}), 400

    values.append(id)
    try:
        cursor2 = conn.cursor()
        cursor2.execute(f"UPDATE appointment SET {', '.join(fields)} WHERE appointment_id = %s", values)
        conn.commit()
        log_action(request.user['username'], f"UPDATED APPOINTMENT {id}")
        cursor2.close()
        cursor.close()
        conn.close()
        return jsonify({"message": f"Appointment {id} updated successfully"}), 200
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({"error": f"Update failed: {str(e)}"}), 400


# DELETE — with RBAC check
@appointment_bp.route('/delete_appointment/<int:id>', methods=['DELETE'])
@token_required
def delete_appointment(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Check appointment exists
    cursor.execute("SELECT * FROM appointment WHERE appointment_id = %s", (id,))
    appointment = cursor.fetchone()
    if not appointment:
        cursor.close()
        conn.close()
        return jsonify({"error": "Appointment not found"}), 404

    # RBAC: regular users can only delete their own appointments
    if request.user['role'] != 'admin':
        cursor.execute(
            "SELECT patient_id FROM patient WHERE member_id = %s", (request.user['member_id'],)
        )
        patient = cursor.fetchone()
        if not patient or appointment['patient_id'] != patient['patient_id']:
            log_action(request.user['username'], f"UNAUTHORIZED DELETE ATTEMPT: Appointment {id}")
            cursor.close()
            conn.close()
            return jsonify({"error": "Access denied"}), 403

    cursor2 = conn.cursor()
    cursor2.execute("DELETE FROM appointment WHERE appointment_id = %s", (id,))
    conn.commit()
    log_action(request.user['username'], f"DELETED APPOINTMENT {id}")
    cursor2.close()
    cursor.close()
    conn.close()
    return jsonify({"message": "Appointment deleted successfully!"}), 200
