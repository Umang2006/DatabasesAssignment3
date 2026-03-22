from flask import Blueprint, jsonify, request
from db import get_db_connection
from auth import admin_required
from logger import log_action
import bcrypt

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/add_member', methods=['POST'])
@admin_required
def add_member():
    """
    Admin creates a new member + their login credentials + group mapping.
    Body: { name, age, email, contact_no, image, member_type, username, password, role }
    """
    data = request.get_json()
    required = ['name', 'age', 'email', 'contact_no', 'member_type', 'username', 'password', 'role']
    if not all(k in data for k in required):
        return jsonify({"error": "Missing required fields"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 1. Insert into member table
        cursor.execute(
            "INSERT INTO member (name, age, email, contact_no, image, member_type) VALUES (%s, %s, %s, %s, %s, %s)",
            (data['name'], data['age'], data['email'], data['contact_no'],
             data.get('image', ''), data['member_type'])
        )
        new_member_id = cursor.lastrowid

        # 2. Hash password and insert into users table
        password_hash = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute(
            "INSERT INTO users (member_id, username, password_hash, role) VALUES (%s, %s, %s, %s)",
            (new_member_id, data['username'], password_hash, data['role'])
        )

        # 3. Insert into member_group_mapping
        # member_type is 'Patient', 'Doctor', 'Staff' -> group is 'Patients', 'Doctors', 'Staff'
        group_name = data['member_type'] + 's' if not data['member_type'].endswith('s') else data['member_type']
        cursor.execute(
            "INSERT INTO member_group_mapping (member_id, group_name, assigned_role) VALUES (%s, %s, %s)",
            (new_member_id, group_name, data['member_type'])
        )

        conn.commit()
        log_action(request.user['username'], f"CREATED MEMBER {new_member_id} (username: {data['username']}, type: {data['member_type']})")
        return jsonify({"message": "Member created successfully", "member_id": new_member_id}), 201

    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"Failed to create member: {str(e)}"}), 400
    finally:
        cursor.close()
        conn.close()


@admin_bp.route('/delete_member/<int:id>', methods=['DELETE'])
@admin_required
def delete_member(id):
    """
    Admin deletes a member. Cascades to: users table (manual delete first),
    member_group_mapping (via ON DELETE CASCADE),
    and all FK-cascade tables (doctor, patient, nonmedicalstaff, appointment).
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Check member exists
        cursor.execute("SELECT member_id, name FROM member WHERE member_id = %s", (id,))
        member = cursor.fetchone()
        if not member:
            return jsonify({"error": "Member not found"}), 404

        # Manually delete from users first (no ON DELETE CASCADE on users FK)
        cursor.execute("DELETE FROM users WHERE member_id = %s", (id,))

        # Delete from member — cascades to:
        # doctor, patient, nonmedicalstaff, member_group_mapping
        cursor.execute("DELETE FROM member WHERE member_id = %s", (id,))

        conn.commit()
        log_action(request.user['username'], f"DELETED MEMBER {id} (name: {member[1]})")
        return jsonify({"message": f"Member {id} and all related records deleted successfully"}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"Deletion failed: {str(e)}"}), 400
    finally:
        cursor.close()
        conn.close()


@admin_bp.route('/members', methods=['GET'])
@admin_required
def list_members():
    """Admin views all members with their group mapping info."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT m.member_id, m.name, m.age, m.email, m.contact_no, m.member_type,
               u.username, u.role AS system_role,
               mgm.group_name
        FROM member m
        LEFT JOIN users u ON m.member_id = u.member_id
        LEFT JOIN member_group_mapping mgm ON m.member_id = mgm.member_id
        ORDER BY m.member_id
    """)
    members = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify({"members": members}), 200
