from flask import Flask, render_template
from routes.auth_routes import auth_bp
from routes.member_routes import member_bp
from routes.appointment_routes import appointment_bp
from routes.admin_routes import admin_bp
from routes.patient_routes import patient_bp
from routes.medicine_routes import medicine_bp

app = Flask(__name__)

app.register_blueprint(auth_bp)
app.register_blueprint(member_bp)
app.register_blueprint(appointment_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(patient_bp)
app.register_blueprint(medicine_bp)


@app.route('/ui')
def ui():
    return render_template('index.html')


# Serve the UI at root too for convenience
@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True)