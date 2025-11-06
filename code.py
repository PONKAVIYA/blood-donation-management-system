# Blood & Organ Donation Matching System - Single File Version
# Requirements: pip install flask pymongo flask-cors cryptography bcrypt
# Run: python blood_organ_system.py
# Access: http://localhost:5000

from flask import Flask, request, jsonify, render_template_string
from pymongo import MongoClient
import bcrypt
from cryptography.fernet import Fernet
import smtplib
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
client = MongoClient("mongodb://localhost:27017/")  # Use Atlas URI for cloud
db = client["blood_organ_donation_db"]

# Encryption setup (store key securely in production)
key = Fernet.generate_key()
cipher = Fernet(key)

# Embedded CSS
CSS = """
body {
    background-color: #f8f9fa;
    font-family: Arial, sans-serif;
}
.container {
    max-width: 800px;
    margin: auto;
    padding: 20px;
}
h1 {
    color: #dc3545;
    text-align: center;
    margin-bottom: 30px;
}
.form-control {
    border-radius: 5px;
}
.btn-primary {
    background-color: #dc3545;
    border: none;
}
.btn-secondary {
    background-color: #6c757d;
}
#matches {
    margin-top: 20px;
    padding: 10px;
    background-color: #e9ecef;
    border-radius: 5px;
}
"""

# Embedded JS
JS = """
$(document).ready(function() {
    $('#registerForm').submit(function(e) {
        e.preventDefault();
        const data = {
            name: $('#name').val(),
            email: $('#email').val(),
            password: $('#password').val(),
            blood_type: $('#blood_type').val(),
            organs: $('#organs').val().split(','),
            location: $('#location').val(),
            role: $('#role').val(),
            urgency: $('#urgency').val(),
            medical_history: $('#medical_history').val()
        };
        $.ajax({
            url: '/register',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(data),
            success: function(response) {
                alert(response.message);
                $('#registerForm')[0].reset();
            },
            error: function(xhr) {
                alert(xhr.responseJSON.error);
            }
        });
    });

    $('#searchMatches').click(function() {
        const blood_type = $('#searchBlood').val();
        const location = $('#searchLocation').val();
        const role = $('#searchRole').val();
        $.get('/match', { blood_type, location, role }, function(data) {
            if (data.length > 0) {
                $('#matches').html('<h4>Potential Matches:</h4>' + data.map(m => 
                    `<p><strong>${m.name}</strong> - Blood: ${m.blood_type}, Compatibility: ${m.compatibility}%<br>
                    <button class="notify-btn btn btn-sm btn-success" data-email="${m.email}">Notify</button></p>`
                ).join(''));
            } else {
                $('#matches').html('<p>No matches found.</p>');
            }
        });
    });

    $(document).on('click', '.notify-btn', function() {
        const email = $(this).data('email');
        $.post('/notify', JSON.stringify({ email: email, message: "You have a potential donation match! Please contact the system admin." }), function(response) {
            alert(response.message);
        });
    });
});
"""

# Embedded HTML Template
HTML_TEMPLATE = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Blood & Organ Donation Matching System</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>{CSS}</style>
</head>
<body>
    <div class="container">
        <h1 class="mt-5">Blood & Organ Donation Matching System</h1>
        <form id="registerForm" class="mb-4">
            <input type="text" id="name" placeholder="Name" class="form-control mb-2" required>
            <input type="email" id="email" placeholder="Email" class="form-control mb-2" required>
            <input type="password" id="password" placeholder="Password" class="form-control mb-2" required>
            <select id="blood_type" class="form-control mb-2" required>
                <option value="">Select Blood Type</option>
                <option>A+</option><option>A-</option><option>B+</option><option>B-</option>
                <option>O+</option><option>O-</option><option>AB+</option><option>AB-</option>
            </select>
            <input type="text" id="organs" placeholder="Organs (e.g., kidney,liver)" class="form-control mb-2">
            <input type="text" id="location" placeholder="Location (City)" class="form-control mb-2" required>
            <select id="role" class="form-control mb-2" required>
                <option value="">Select Role</option><option>donor</option><option>recipient</option>
            </select>
            <select id="urgency" class="form-control mb-2">
                <option value="low">Low Urgency</option><option value="high">High Urgency</option>
            </select>
            <textarea id="medical_history" placeholder="Medical History" class="form-control mb-2"></textarea>
            <button type="submit" class="btn btn-primary">Register</button>
        </form>
        <div class="mb-4">
            <h3>Find Matches</h3>
            <select id="searchBlood" class="form-control mb-2">
                <option value="">Select Blood Type</option>
                <option>A+</option><option>A-</option><option>B+</option><option>B-</option>
                <option>O+</option><option>O-</option><option>AB+</option><option>AB-</option>
            </select>
            <input type="text" id="searchLocation" placeholder="Location" class="form-control mb-2">
            <select id="searchRole" class="form-control mb-2">
                <option value="recipient">As Recipient</option>
            </select>
            <button id="searchMatches" class="btn btn-secondary">Search Matches</button>
        </div>
        <div id="matches"></div>
    </div>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script>{JS}</script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    if not data.get('email') or '@' not in data['email']:
        return jsonify({"error": "Invalid email"}), 400
    hashed_pw = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt())
    encrypted_history = cipher.encrypt(data.get('medical_history', '').encode())
    user = {
        "name": data['name'],
        "email": data['email'],
        "password": hashed_pw,
        "blood_type": data['blood_type'],
        "organs": data.get('organs', []),
        "location": data['location'],
        "role": data['role'],
        "medical_history": encrypted_history.decode(),
        "urgency": data.get('urgency', 'low')
    }
    db.users.insert_one(user)
    return jsonify({"message": "User registered successfully"})

@app.route('/match', methods=['GET'])
def match():
    blood_type = request.args.get('blood_type')
    location = request.args.get('location')
    role = request.args.get('role')
    if role == 'recipient':
        donors = list(db.users.find({"blood_type": blood_type, "location": location, "role": "donor"}))
        for donor in donors:
            donor['compatibility'] = 100 if donor['blood_type'] == blood_type else 50  # Expand logic
        donors.sort(key=lambda x: x['compatibility'], reverse=True)
        return jsonify(donors[:5])
    return jsonify([])

@app.route('/notify', methods=['POST'])
def notify():
    data = request.json
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login("your_email@gmail.com", "your_password")  # Secure this
        message = f"Subject: Donation Match\n\n{data['message']}"
        server.sendmail("your_email@gmail.com", data['email'], message)
        server.quit()
        return jsonify({"message": "Notification sent"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
