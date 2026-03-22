from flask import Blueprint, jsonify, request
from db import get_db_connection
from auth import token_required, admin_required
from logger import log_action

medicine_bp = Blueprint('medicine', __name__)


# READ all medicines with inventory info (all authenticated users)
@medicine_bp.route('/medicines', methods=['GET'])
@token_required
def get_medicines():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT
            m.medicine_id,
            m.medicine_name,
            m.manufacturer,
            m.price,
            m.category,
            i.inventory_id,
            i.quantity,
            i.manufacturing_date,
            i.expiry_date
        FROM medicine m
        LEFT JOIN inventory i ON m.medicine_id = i.medicine_id
        ORDER BY m.medicine_name
    """)
    medicines = cursor.fetchall()
    # Serialize date objects
    for med in medicines:
        if med.get('expiry_date') and hasattr(med['expiry_date'], 'isoformat'):
            med['expiry_date'] = med['expiry_date'].isoformat()
        if med.get('manufacturing_date') and hasattr(med['manufacturing_date'], 'isoformat'):
            med['manufacturing_date'] = med['manufacturing_date'].isoformat()
    cursor.close()
    conn.close()
    return jsonify({"medicines": medicines}), 200


# READ single medicine
@medicine_bp.route('/medicines/<int:id>', methods=['GET'])
@token_required
def get_medicine(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT m.*, i.quantity, i.manufacturing_date, i.expiry_date, i.inventory_id
        FROM medicine m
        LEFT JOIN inventory i ON m.medicine_id = i.medicine_id
        WHERE m.medicine_id = %s
    """, (id,))
    medicine = cursor.fetchone()
    cursor.close()
    conn.close()
    if not medicine:
        return jsonify({"error": "Medicine not found"}), 404
    if medicine.get('expiry_date') and hasattr(medicine['expiry_date'], 'isoformat'):
        medicine['expiry_date'] = medicine['expiry_date'].isoformat()
    if medicine.get('manufacturing_date') and hasattr(medicine['manufacturing_date'], 'isoformat'):
        medicine['manufacturing_date'] = medicine['manufacturing_date'].isoformat()
    return jsonify({"medicine": medicine}), 200


# CREATE medicine + inventory entry (admin only)
@medicine_bp.route('/add_medicine', methods=['POST'])
@admin_required
def add_medicine():
    data = request.get_json()
    required = ['medicine_name', 'manufacturer', 'price', 'category',
                'quantity', 'manufacturing_date', 'expiry_date']
    if not all(k in data for k in required):
        return jsonify({"error": "Missing required fields"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Insert into medicine table
        cursor.execute(
            "INSERT INTO medicine (medicine_name, manufacturer, price, category) VALUES (%s, %s, %s, %s)",
            (data['medicine_name'], data['manufacturer'], data['price'], data['category'])
        )
        med_id = cursor.lastrowid

        # Insert into inventory table
        cursor.execute(
            "INSERT INTO inventory (manufacturing_date, expiry_date, quantity, medicine_id) "
            "VALUES (%s, %s, %s, %s)",
            (data['manufacturing_date'], data['expiry_date'], data['quantity'], med_id)
        )
        conn.commit()
        log_action(request.user['username'],
                   f"CREATED MEDICINE {med_id} (name: {data['medicine_name']}, qty: {data['quantity']})")
        return jsonify({"message": "Medicine added successfully", "medicine_id": med_id}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"Failed to add medicine: {str(e)}"}), 400
    finally:
        cursor.close()
        conn.close()


# UPDATE medicine and/or inventory (admin only)
@medicine_bp.route('/update_medicine/<int:id>', methods=['PUT'])
@admin_required
def update_medicine(id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Update medicine table fields if provided
        med_fields = []
        med_vals = []
        for k, col in [('medicine_name', 'medicine_name'), ('manufacturer', 'manufacturer'),
                       ('price', 'price'), ('category', 'category')]:
            if k in data:
                med_fields.append(f"{col} = %s")
                med_vals.append(data[k])
        if med_fields:
            med_vals.append(id)
            cursor.execute(
                f"UPDATE medicine SET {', '.join(med_fields)} WHERE medicine_id = %s", med_vals
            )

        # Update inventory fields if provided
        inv_fields = []
        inv_vals = []
        for k, col in [('quantity', 'quantity'), ('expiry_date', 'expiry_date'),
                       ('manufacturing_date', 'manufacturing_date')]:
            if k in data:
                inv_fields.append(f"{col} = %s")
                inv_vals.append(data[k])
        if inv_fields:
            inv_vals.append(id)
            cursor.execute(
                f"UPDATE inventory SET {', '.join(inv_fields)} WHERE medicine_id = %s", inv_vals
            )

        conn.commit()
        log_action(request.user['username'], f"UPDATED MEDICINE {id}")
        return jsonify({"message": f"Medicine {id} updated successfully"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"Update failed: {str(e)}"}), 400
    finally:
        cursor.close()
        conn.close()


# DELETE medicine (admin only) — inventory deletes via FK cascade
@medicine_bp.route('/delete_medicine/<int:id>', methods=['DELETE'])
@admin_required
def delete_medicine(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT medicine_name FROM medicine WHERE medicine_id = %s", (id,))
        med = cursor.fetchone()
        if not med:
            cursor.close()
            conn.close()
            return jsonify({"error": "Medicine not found"}), 404

        # Delete inventory first (no ON DELETE CASCADE defined on inventory FK)
        cursor2 = conn.cursor()
        cursor2.execute("DELETE FROM inventory WHERE medicine_id = %s", (id,))
        cursor2.execute("DELETE FROM medicine WHERE medicine_id = %s", (id,))
        conn.commit()
        log_action(request.user['username'],
                   f"DELETED MEDICINE {id} (name: {med['medicine_name']})")
        cursor2.close()
        cursor.close()
        conn.close()
        return jsonify({"message": f"Medicine {id} deleted successfully"}), 200
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({"error": f"Deletion failed: {str(e)}"}), 400
