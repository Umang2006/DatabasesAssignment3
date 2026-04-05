from flask import Blueprint, jsonify, request
try:
    from ..db import get_db_connection
    from ..auth import token_required
    from ..logger import log_action
except ImportError:
    from db import get_db_connection
    from auth import token_required
    from logger import log_action

member_bp = Blueprint('member', __name__)


@member_bp.route('/portfolio/<int:id>', methods=['GET'])
@token_required
def get_portfolio(id):
    # RBAC Check: Regular users can only see their own portfolio
    if request.user['role'] != 'admin' and request.user['member_id'] != id:
        log_action(request.user['username'], f"UNAUTHORIZED ACCESS ATTEMPT: Portfolio {id}")
        return jsonify({"error": "Access denied"}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT m.member_id, m.name, m.age, m.email, m.contact_no, m.member_type,
               u.username, u.role AS system_role,
               mgm.group_name
        FROM member m
        LEFT JOIN users u ON m.member_id = u.member_id
        LEFT JOIN member_group_mapping mgm ON m.member_id = mgm.member_id
        WHERE m.member_id = %s
    """, (id,))
    member = cursor.fetchone()

    cursor.close()
    conn.close()

    if not member:
        return jsonify({"error": "Member not found"}), 404

    return jsonify({"member": member}), 200
