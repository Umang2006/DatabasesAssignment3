import jwt
import datetime
import os
from functools import wraps
from flask import request, jsonify

SECRET_KEY = os.environ.get("JWT_SECRET", "my_secret_key_123")


def encode_token(username, role, member_id, patient_id=None, member_type='User'):
    payload = {
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=2),
        'iat': datetime.datetime.utcnow(),
        'username': username,
        'role': role,
        'member_id': member_id,
        'patient_id': patient_id,
        'member_type': member_type
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'No session found'}), 401
        try:
            token = token.split(" ")[1]  # Remove 'Bearer '
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            request.user = data
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Session expired'}), 401
        except Exception:
            return jsonify({'error': 'Invalid session token'}), 401
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'No session found'}), 401
        try:
            token = token.split(" ")[1]
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            request.user = data
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Session expired'}), 401
        except Exception:
            return jsonify({'error': 'Invalid session token'}), 401

        if request.user.get('role') != 'admin':
            return jsonify({'error': 'Unauthorized: Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated
