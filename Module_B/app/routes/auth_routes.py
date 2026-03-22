from flask import Blueprint, request, jsonify
import os
from db import get_db_connection
from auth import encode_token, token_required, admin_required
import bcrypt

auth_bp = Blueprint('auth', __name__)


# Welcome Endpoint
@auth_bp.route('/', methods=['GET'])
def welcome():
    return jsonify({"message": "Welcome to test APIs"})


# Login Endpoint
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    if not data or not data.get('user') or not data.get('password'):
        return jsonify({"error": "Missing parameters"}), 401

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE username = %s", (data['user'],))
    user = cursor.fetchone()

    if not user or not bcrypt.checkpw(data['password'].encode('utf-8'), user['password_hash'].encode('utf-8')):
        cursor.close()
        conn.close()
        return jsonify({"error": "Invalid credentials"}), 401

    # Resolve member_type from the member table
    member_type = 'User'
    cursor.execute("SELECT member_type FROM member WHERE member_id = %s", (user['member_id'],))
    member_row = cursor.fetchone()
    if member_row:
        member_type = member_row['member_type']

    # Resolve patient_id if this member is a patient
    patient_id = None
    cursor.execute("SELECT patient_id FROM patient WHERE member_id = %s", (user['member_id'],))
    patient_row = cursor.fetchone()
    if patient_row:
        patient_id = patient_row['patient_id']

    cursor.close()
    conn.close()

    token = encode_token(user['username'], user['role'], user['member_id'], patient_id, member_type)
    return jsonify({
        "message": "Login successful",
        "session_token": token
    }), 200


# Patient Self-Registration Endpoint
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    required = ['name', 'age', 'email', 'contact_no', 'username', 'password']
    if not data or not all(k in data for k in required):
        return jsonify({"error": "Missing required fields"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Check username not already taken
    cursor.execute("SELECT user_id FROM users WHERE username = %s", (data['username'],))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({"error": "Username already taken"}), 409

    # Check email not already registered
    cursor.execute("SELECT member_id FROM member WHERE email = %s", (data['email'],))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({"error": "Email already registered"}), 409

    try:
        cursor2 = conn.cursor()

        # 1. Insert into member as Patient
        cursor2.execute(
            "INSERT INTO member (name, age, email, contact_no, image, member_type) VALUES (%s, %s, %s, %s, %s, %s)",
            (data['name'], int(data['age']), data['email'], data['contact_no'], '', 'Patient')
        )
        new_member_id = cursor2.lastrowid

        # 2. Insert into patient table
        cursor2.execute(
            "INSERT INTO patient (blood_group, gender, address, member_id) VALUES (%s, %s, %s, %s)",
            (data.get('blood_group', 'Unknown'), data.get('gender', 'Other'), data.get('address', ''), new_member_id)
        )

        # 3. Hash password and insert into users
        password_hash = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor2.execute(
            "INSERT INTO users (member_id, username, password_hash, role) VALUES (%s, %s, %s, %s)",
            (new_member_id, data['username'], password_hash, 'user')
        )

        # 4. Insert into member_group_mapping
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


# Session Validation Endpoint
@auth_bp.route('/isAuth', methods=['GET'])
@token_required
def is_auth():
    return jsonify({
        "message": "User is authenticated",
        "username": request.user['username'],
        "role": request.user['role'],
        "expiry": request.user['exp']
    }), 200


# Audit Log Viewer (Admin only)
@auth_bp.route('/audit_logs', methods=['GET'])
@admin_required
def get_audit_logs():
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs', 'audit.log')
    try:
        with open(log_path, 'r') as f:
            lines = f.readlines()
        logs = [line.strip() for line in reversed(lines) if line.strip()]
        return jsonify({"logs": logs}), 200
    except FileNotFoundError:
        return jsonify({"logs": [], "message": "No logs yet"}), 200