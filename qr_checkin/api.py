import frappe
import qrcode
import base64
from io import BytesIO
from datetime import datetime, timedelta
import secrets
import time
import hashlib
from frappe.utils import get_url, now_datetime, get_datetime
from frappe.utils.password import get_decrypted_password

# Generate and Display QR Code
@frappe.whitelist(allow_guest=True)
def generate_qr_code():
    try:
        # Generate a unique token
        token = secrets.token_urlsafe(32)
        expiry = now_datetime() + timedelta(minutes=5)
        
        # Store token in a new QR Session DocType
        qr_session = frappe.get_doc({
            "doctype": "QR CheckIn Session",
            "token": token,
            "expiry": expiry,
            "is_used": 0
        })
        qr_session.insert(ignore_permissions=True)
        frappe.db.commit()
        
        # Create QR code with check-in URL
        checkin_url = get_url(f"/checkin/member?token={token}")
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(checkin_url)
        qr.make(fit=True)
        
        # Convert QR code to base64 string
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return {
            "qr_image": f"data:image/png;base64,{img_str}",
            "token": token,
            "expiry": expiry.strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        frappe.log_error(f"Error in generate_qr_code: {str(e)}", "QR CheckIn Error")
        return {"status": "error", "message": f"Failed to generate QR code: {str(e)}"}

# Handle QR Code Scans
@frappe.whitelist(allow_guest=True)
def validate_qr_token(token):
    try:
        if not token:
            return {"status": "error", "message": "No token provided"}
        
        qr_session = frappe.get_all(
            "QR CheckIn Session",
            filters={"token": token, "is_used": 0},
            fields=["name", "expiry"]
        )
        
        if not qr_session:
            return {"status": "error", "message": "Invalid or used token"}
        
        session = qr_session[0]
        if get_datetime(session.expiry) < now_datetime():
            return {"status": "error", "message": "Token has expired"}
        
        return {"status": "success", "token": token}
    except Exception as e:
        frappe.log_error(f"Error in validate_qr_token: {str(e)}", "QR CheckIn Error")
        return {"status": "error", "message": f"Token validation failed: {str(e)}"}

# Send OTP after Member ID validation
@frappe.whitelist(allow_guest=True)
def send_otp(member_id, token):
    try:
        # Validate token
        token_status = validate_qr_token(token)
        if token_status["status"] != "success":
            return token_status
        
        # Validate Member ID
        member = frappe.get_all(
            "Member",
            filters={"member_id": member_id},
            fields=["name", "email_address"]
        )
        
        if not member:
            return {"status": "error", "message": "Invalid Member ID"}
        
        # Generate OTP
        otp = str(secrets.randbelow(999999)).zfill(6)
        otp_expiry = now_datetime() + timedelta(minutes=5)
        
        # Store OTP
        otp_doc = frappe.get_doc({
            "doctype": "OTP Record",
            "member_id": member_id,
            "otp": hashlib.sha256(otp.encode()).hexdigest(),
            "token": token,
            "expiry": otp_expiry,
            "attempts": 0
        })
        otp_doc.insert(ignore_permissions=True)
        frappe.db.commit()
        
        # Send OTP via Email
        frappe.sendmail(
            recipients=member[0].email_address,
            subject="Your OTP for Check-In",
            message=f"Your one-time password is: {otp}. It expires in 5 minutes.",
            sender="franciskamande2001@gmail.com"
        )
        
        return {"status": "success", "message": "OTP sent successfully"}
    except Exception as e:
        frappe.log_error(f"Error in send_otp: {str(e)}", "QR CheckIn Error")
        return {"status": "error", "message": f"Failed to send OTP: {str(e)}"}

# Verify OTP
@frappe.whitelist(allow_guest=True)
def verify_otp(member_id, token, otp):
    try:
        # Validate token
        token_status = validate_qr_token(token)
        if token_status["status"] != "success":
            return token_status
        
        # Find OTP record
        otp_records = frappe.get_all(
            "OTP Record",
            filters={
                "member_id": member_id,
                "token": token,
                "attempts": ["<", 3]
            },
            fields=["name", "otp", "expiry", "attempts"]
        )
        
        if not otp_records:
            return {"status": "error", "message": "No valid OTP found"}
        
        otp_doc = frappe.get_doc("OTP Record", otp_records[0].name)
        
        if get_datetime(otp_doc.expiry) < now_datetime():
            return {"status": "error", "message": "OTP has expired"}
        
        # Verify OTP
        if hashlib.sha256(otp.encode()).hexdigest() != otp_doc.otp:
            otp_doc.attempts += 1
            otp_doc.save(ignore_permissions=True)
            frappe.db.commit()
            remaining = 2 - otp_doc.attempts
            return {
                "status": "error",
                "message": f"Invalid OTP. {remaining} attempts remaining" if remaining > 0 else "Maximum attempts exceeded"
            }
        
        # Step 6: Log Check-In
        checkin = frappe.get_doc({
            "doctype": "Attendance CheckIn",
            "member_id": member_id,
            "token": token,
            "checkin_time": now_datetime(),
            "qr_session": frappe.get_value("QR CheckIn Session", {"token": token}, "name")
        })
        checkin.insert(ignore_permissions=True)
        
        # Mark QR session and OTP as used
        qr_session = frappe.get_doc("QR CheckIn Session", {"token": token})
        qr_session.is_used = 1
        qr_session.save(ignore_permissions=True)
        
        otp_doc.is_used = 1
        otp_doc.save(ignore_permissions=True)
        
        frappe.db.commit()
        
        return {"status": "success", "message": "Check-in successful"}
    except Exception as e:
        frappe.log_error(f"Error in verify_otp: {str(e)}", "QR CheckIn Error")
        return {"status": "error", "message": f"OTP verification failed: {str(e)}"}