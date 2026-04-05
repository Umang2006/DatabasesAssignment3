from flask import Blueprint, request, jsonify
try:
    from ..db import get_db_connection
    from ..auth import encode_token, token_required, admin_required
    from ..logger import get_recent_logs
    from ..validators import (
        ALLOWED_GENDERS,
        clean_string,
        validate_age,
        validate_email,
        validate_password,
        validate_phone,
        validate_username,
    )
except ImportError:
    from db import get_db_connection
    from auth import encode_token, token_required, admin_required
    from logger import get_recent_logs
    from validators import (
        ALLOWED_GENDERS,
        clean_string,
        validate_age,
        validate_email,
        validate_password,
        validate_phone,
        validate_username,
    )
import bcrypt

auth_bp = Blueprint('auth', __name__)


def _validation_error(message):
    return jsonify({"error": message}), 400


@auth_bp.route('/', methods=['GET'])
def welcome():
    return jsonify({"message": "Welcome to test APIs"})


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = clean_string(data.get('user') if data else "")
    password = data.get('password') if data else None

    if not username or not password:
        return jsonify({"error": "Missing parameters"}), 401

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()

    if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
        cursor.close()
        conn.close()
        return jsonify({"error": "Invalid credentials"}), 401

    member_type = 'User'
    doctor_id = None
    patient_id = None

    cursor.execute("SELECT member_type FROM member WHERE member_id = %s", (user['member_id'],))
    member_row = cursor.fetchone()
    if member_row:
        member_type = member_row['member_type']

    cursor.execute("SELECT patient_id FROM patient WHERE member_id = %s", (user['member_id'],))
    patient_row = cursor.fetchone()
    if patient_row:
        patient_id = patient_row['patient_id']

    cursor.execute("SELECT doctor_id FROM doctor WHERE member_id = %s", (user['member_id'],))
    doctor_row = cursor.fetchone()
    if doctor_row:
        doctor_id = doctor_row['doctor_id']

    cursor.close()
    conn.close()

    token = encode_token(
        user['username'],
        user['role'],
        user['member_id'],
        patient_id=patient_id,
        member_type=member_type,
        doctor_id=doctor_id,
    )
    return jsonify({
        "message": "Login successful",
        "session_token": token
    }), 200


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}

    name = clean_string(data.get('name'))
    age = data.get('age')
    email = clean_string(data.get('email'))
    contact_no = clean_string(data.get('contact_no'))
    username = clean_string(data.get('username'))
    password = data.get('password')
    gender = clean_string(data.get('gender', 'Other')) or 'Other'
    address = clean_string(data.get('address'))
    blood_group = clean_string(data.get('blood_group', 'Unknown')) or 'Unknown'

    if not all([name, age, email, contact_no, username, password]):
        return _validation_error("Missing required fields")
    if not validate_age(age):
        return _validation_error("Age must be between 1 and 120")
    if not validate_email(email):
        return _validation_error("Enter a valid email address")
    if not validate_phone(contact_no):
        return _validation_error("Enter a valid contact number")
    if not validate_username(username):
        return _validation_error("Username must be 3-30 characters and use only letters, numbers, or underscore")
    if not validate_password(password):
        return _validation_error("Password must be at least 8 characters and contain letters and numbers")
    if gender not in ALLOWED_GENDERS:
        return _validation_error("Invalid gender")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT user_id FROM users WHERE username = %s", (username,))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({"error": "Username already taken"}), 409

    cursor.execute("SELECT member_id FROM member WHERE email = %s", (email,))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({"error": "Email already registered"}), 409

    try:
        cursor2 = conn.cursor()
        cursor2.execute(
            "INSERT INTO member (name, age, email, contact_no, image, member_type) VALUES (%s, %s, %s, %s, %s, %s)",
            (name, int(age), email, contact_no, '', 'Patient')
        )
        new_member_id = cursor2.lastrowid

        cursor2.execute(
            "INSERT INTO patient (blood_group, gender, address, member_id) VALUES (%s, %s, %s, %s)",
            (blood_group, gender, address, new_member_id)
        )

        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor2.execute(
            "INSERT INTO users (member_id, username, password_hash, role) VALUES (%s, %s, %s, %s)",
            (new_member_id, username, password_hash, 'user')
        )
        cursor2.execute(
            "INSERT INTO member_group_mapping (member_id, group_name, assigned_role) VALUES (%s, %s, %s)",
            (new_member_id, 'Patients', 'Patient')
        )

        conn.commit()
        cursor2.close()
        cursor.close()
        conn.close()
        return jsonify({"message": "Registration successful! You can now log in."}), 201
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({"error": f"Registration failed: {str(e)}"}), 400


@auth_bp.route('/isAuth', methods=['GET'])
@token_required
def is_auth():
    return jsonify({
        "message": "User is authenticated",
        "username": request.user['username'],
        "role": request.user['role'],
        "member_type": request.user.get('member_type'),
        "expiry": request.user['exp']
    }), 200


@auth_bp.route('/audit_logs', methods=['GET'])
@admin_required
def get_audit_logs():
    return jsonify({"logs": get_recent_logs()}), 200
