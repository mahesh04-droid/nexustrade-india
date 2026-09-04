"""
NexusTrade India Pro - Authentication & Email OTP Security Engine
Provides PBKDF2 Salted Password Hashing, Session Token Gating, and 6-Digit Email OTP (2FA) Verification.
"""

import os
import json
import uuid
import time
import hashlib
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

USERS_DB_FILE = os.path.join(os.path.dirname(__file__), "scratch", "users_db.json")

class AuthManager:
    def __init__(self):
        os.makedirs(os.path.dirname(USERS_DB_FILE), exist_ok=True)
        self.users = self._load_users()

    def _load_users(self):
        """Loads users database from disk or seeds default admin user."""
        if os.path.exists(USERS_DB_FILE):
            try:
                with open(USERS_DB_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and data:
                        return data
            except Exception as e:
                print("Error loading users DB:", e)

        # Seed default admin user: admin@nexustrade.in / Nexus@2026
        salt = secrets.token_hex(16)
        pwd_hash = self.hash_password("Nexus@2026", salt)
        
        default_users = {
            "admin@nexustrade.in": {
                "email": "admin@nexustrade.in",
                "name": "Platform Administrator",
                "hash": pwd_hash,
                "salt": salt,
                "created_at": time.time(),
                "active_sessions": {},
                "otp_code": None,
                "otp_expires": 0
            }
        }
        self._save_users(default_users)
        return default_users

    def _save_users(self, users_dict=None):
        """Saves users database to disk."""
        data_to_save = users_dict if users_dict is not None else self.users
        try:
            with open(USERS_DB_FILE, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, indent=2)
        except Exception as e:
            print("Error saving users DB:", e)

    def hash_password(self, password: str, salt: str) -> str:
        """Hashes password using PBKDF2 HMAC SHA256 with 100,000 iterations."""
        return hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        ).hex()

    def authenticate_user(self, email: str, password: str):
        """
        Step 1 Authentication: Validates email & password.
        Generates 6-digit OTP code and triggers email dispatch.
        """
        email = email.lower().strip()
        user = self.users.get(email)
        if not user:
            return {"status": "ERROR", "message": "Invalid Email / User ID or Password"}

        calc_hash = self.hash_password(password, user["salt"])
        if calc_hash != user["hash"]:
            return {"status": "ERROR", "message": "Invalid Email / User ID or Password"}

        # Password matches -> Generate 6-digit numeric OTP for 2FA verification
        otp_code = str(secrets.randbelow(899999) + 100000) # 100000 to 999999
        otp_expires = time.time() + 300 # 5 minutes validity
        
        user["otp_code"] = otp_code
        user["otp_expires"] = otp_expires
        self._save_users()

        # Send Email OTP via SMTP or log to console
        self._send_email_otp(email, otp_code)

        return {
            "status": "SUCCESS",
            "step": "REQUIRE_OTP",
            "email": email,
            "message": f"OTP Verification Code sent to {email}. Valid for 5 minutes."
        }

    def verify_otp(self, email: str, otp_code: str):
        """
        Step 2 Authentication: Verifies 6-digit Email OTP and issues 256-bit Session Token.
        """
        email = email.lower().strip()
        user = self.users.get(email)
        if not user:
            return {"status": "ERROR", "message": "User not found"}

        if not user.get("otp_code") or user.get("otp_code") != otp_code.strip():
            return {"status": "ERROR", "message": "Invalid 6-digit OTP code"}

        if time.time() > user.get("otp_expires", 0):
            return {"status": "ERROR", "message": "OTP code has expired. Please log in again."}

        # Clear OTP and create Session Token
        user["otp_code"] = None
        user["otp_expires"] = 0

        session_token = f"NEXUS-{uuid.uuid4().hex.upper()}"
        user["active_sessions"][session_token] = {
            "created_at": time.time(),
            "last_active": time.time()
        }
        self._save_users()

        return {
            "status": "SUCCESS",
            "token": session_token,
            "user": {
                "email": user["email"],
                "name": user["name"]
            },
            "message": "Authentication successful! Welcome to NexusTrade India Pro."
        }

    def validate_session(self, token: str):
        """Validates if a session token is active and valid."""
        if not token:
            return None
        
        for email, user in self.users.items():
            if token in user.get("active_sessions", {}):
                # Update last active timestamp
                user["active_sessions"][token]["last_active"] = time.time()
                return user
        return None

    def revoke_session(self, token: str):
        """Logs out user by revoking session token."""
        for email, user in self.users.items():
            if token in user.get("active_sessions", {}):
                del user["active_sessions"][token]
                self._save_users()
                return True
        return False

    def _send_email_otp(self, email: str, otp_code: str):
        """Sends OTP via SMTP if environment credentials exist, else logs prominently."""
        smtp_host = os.environ.get("SMTP_HOST")
        smtp_port = int(os.environ.get("SMTP_PORT", 587))
        smtp_user = os.environ.get("SMTP_USER")
        smtp_pass = os.environ.get("SMTP_PASS")

        msg_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #070a10; color: #ffffff; padding: 20px;">
          <div style="max-width: 500px; margin: auto; background: #101520; padding: 25px; border-radius: 10px; border: 1px solid #1e2840;">
            <h2 style="color: #10d982;">🔒 NexusTrade India Pro Security Verification</h2>
            <p>Your 6-digit OTP code for platform login is:</p>
            <div style="font-size: 32px; font-weight: bold; letter-spacing: 5px; color: #4f6ef7; background: #070a10; padding: 15px; text-align: center; border-radius: 6px; margin: 20px 0;">
              {otp_code}
            </div>
            <p style="font-size: 12px; color: #8a99ad;">This code will expire in 5 minutes. Do not share this code with anyone.</p>
          </div>
        </body>
        </html>
        """

        print("==================================================================")
        print(f"  SECURITY OTP DISPATCH FOR {email}: [ {otp_code} ]")
        print("==================================================================")

        if smtp_host and smtp_user and smtp_pass:
            try:
                msg = MIMEMultipart('alternative')
                msg['Subject'] = f"🔒 {otp_code} is your NexusTrade Security OTP Code"
                msg['From'] = smtp_user
                msg['To'] = email
                msg.attach(MIMEText(msg_body, 'html'))

                with smtplib.SMTP(smtp_host, smtp_port, timeout=5) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                    server.sendmail(smtp_user, [email], msg.as_string())
                print(f"Successfully sent OTP email to {email}")
            except Exception as e:
                print(f"SMTP Dispatch Error: {e}")

auth_manager = AuthManager()
