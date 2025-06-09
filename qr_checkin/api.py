import frappe
import qrcode
import base64
from io import BytesIO
from datetime import datetime, timedelta
import secrets
import time
import hashlib
from frappe.utils import get_url, now_datetime, get_datetime, get_fullname
from frappe.utils.password import get_decrypted_password

# Generate and Display QR Code
@frappe.whitelist(allow_guest=True)
def generate_qr_code(session_name=None, duration_minutes=60):
    """
    Generate a QR code for check-in with enhanced session management
    """
    try:
        # Generate a unique token
        token = secrets.token_urlsafe(32)
        start_time = now_datetime()
        expiry = start_time + timedelta(minutes=int(duration_minutes))
        
        # Create session name if not provided
        if not session_name:
            session_name = f"Check-in Session {start_time.strftime('%Y-%m-%d %H:%M')}"
        
        # Store token in QR Session DocType with enhanced fields
        qr_session = frappe.get_doc({
            "doctype": "QR CheckIn Session",
            "session_name": session_name,
            "token": token,
            "start_time": start_time,
            "expiry": expiry,
            "duration_minutes": duration_minutes,
            "is_active": 1,
            "is_used": 0,
            "total_checkins": 0,
            "allow_late_checkin": 1,
            "late_threshold_minutes": 15,
            "auto_expire": 1
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
            "status": "success",
            "qr_image": f"data:image/png;base64,{img_str}",
            "token": token,
            "session_name": session_name,
            "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "expiry": expiry.strftime("%Y-%m-%d %H:%M:%S"),
            "duration_minutes": duration_minutes,
            "checkin_url": checkin_url
        }
    except Exception as e:
        frappe.log_error(f"Error in generate_qr_code: {str(e)}", "QR CheckIn Error")
        return {"status": "error", "message": f"Failed to generate QR code: {str(e)}"}

# Handle QR Code Scans with enhanced validation
@frappe.whitelist(allow_guest=True)
def validate_qr_token(token):
    """
    Validate QR token with enhanced session management
    """
    try:
        if not token:
            return {"status": "error", "message": "No token provided"}
        
        # Get session details
        qr_session = frappe.get_all(
            "QR CheckIn Session",
            filters={"token": token},
            fields=["name", "session_name", "start_time", "expiry", "is_active", 
                   "allow_late_checkin", "late_threshold_minutes"]
        )
        
        if not qr_session:
            return {"status": "error", "message": "Invalid token"}
        
        session = qr_session[0]
        current_time = now_datetime()
        
        # Check if session is active
        if not session.is_active:
            return {"status": "error", "message": "Session is inactive"}
        
        # Check expiry with late check-in consideration
        if get_datetime(session.expiry) < current_time:
            if session.allow_late_checkin:
                late_cutoff = get_datetime(session.expiry) + timedelta(minutes=session.late_threshold_minutes)
                if current_time > late_cutoff:
                    return {"status": "error", "message": "Session has expired beyond late check-in threshold"}
            else:
                return {"status": "error", "message": "Session has expired"}
        
        return {
            "status": "success", 
            "token": token,
            "session_name": session.session_name,
            "is_late": get_datetime(session.expiry) < current_time
        }
    except Exception as e:
        frappe.log_error(f"Error in validate_qr_token: {str(e)}", "QR CheckIn Error")
        return {"status": "error", "message": f"Token validation failed: {str(e)}"}

@frappe.whitelist(allow_guest=True)
def send_otp(member_id, token):
    """
    Send OTP with enhanced member validation and OTP management
    """
    try:
        print(f"Processing send_otp with member_id: {member_id} (type: {type(member_id)}), token: {token}")
        
        # Validate token first
        token_status = validate_qr_token(token)
        if token_status["status"] != "success":
            print(f"Token validation failed: {token_status}")
            return token_status
        
        # Validate Member with enhanced fields - handle both string and int member_id
        member = frappe.get_all(
            "Member",
            filters={"member_id": member_id, "is_active": 1},
            fields=["name", "member_id", "member_name", "email_address", "whatsapp_number"]
        )
        
        if not member and str(member_id).isdigit():
            print(f"Member not found with string member_id {member_id}, trying integer {int(member_id)}")
            member = frappe.get_all(
                "Member",
                filters={"member_id": int(member_id), "is_active": 1},
                fields=["name", "member_id", "member_name", "email_address", "whatsapp_number"]
            )
        
        print(f"Found member for member_id {member_id}: {member}")
        
        if not member:
            return {"status": "error", "message": f"Invalid Member ID {member_id} or inactive member"}
        
        member_data = member[0]
        member_doc_name = member_data.name  # Use Member document name (e.g., 'ov9ulljiat')
        
        # Check for existing unused OTP for this member and token
        print(f"Checking for existing OTP for member_doc_name {member_doc_name}, token {token}")
        existing_otp = frappe.get_all(
            "OTP Record",
            filters={
                "member_id": member_doc_name,  # Use Member document name
                "token": token,
                "is_used": 0,
                "expiry": [">", now_datetime()]
            },
            fields=["name"]
        )
        print(f"Existing OTP check result: {existing_otp}")
        
        if existing_otp:
            print(f"Existing OTP found for member_doc_name {member_doc_name}, token {token}")
            return {"status": "error", "message": "OTP already sent. Please wait for expiry or use existing OTP."}
        
        # Generate OTP
        otp = str(secrets.randbelow(999999)).zfill(6)
        otp_expiry = now_datetime() + timedelta(minutes=5)
        print(f"Generated OTP: {otp}, expiry: {otp_expiry}")
        
        # Store OTP with enhanced fields
        otp_doc = frappe.get_doc({
            "doctype": "OTP Record",
            "member_id": member_doc_name,  # Use Member document name
            "otp": hashlib.sha256(otp.encode()).hexdigest(),
            "token": token,
            "expiry": otp_expiry,
            "attempts": 0,
            "max_attempts": 3,
            "is_used": 0,
            "created_at": now_datetime()
        })
        print(f"Prepared OTP doc: {otp_doc.as_dict()}")
        
        try:
            otp_doc.insert(ignore_permissions=True)
            print(f"OTP doc inserted for member_doc_name {member_doc_name}")
        except frappe.DoesNotExistError as dne:
            frappe.log_error(f"OTP Record DocType not found for member_doc_name {member_doc_name}: {str(dne)}", "QR CheckIn OTP Insert Error")
            return {"status": "error", "message": "OTP Record DocType not found. Contact administrator."}
        except frappe.exceptions.ValidationError as ve:
            frappe.log_error(f"Validation error in OTP Record insertion for member_doc_name {member_doc_name}: {str(ve)}", "QR CheckIn OTP Insert Error")
            return {"status": "error", "message": f"Failed to store OTP due to validation error: {str(ve)}"}
        except Exception as insert_error:
            frappe.log_error(f"Failed to insert OTP Record for member_doc_name {member_doc_name}: {str(insert_error)}", "QR CheckIn OTP Insert Error")
            return {"status": "error", "message": f"Failed to store OTP: {str(insert_error)}"}
        
        try:
            frappe.db.commit()
            print(f"Database committed for OTP storage, member_doc_name: {member_doc_name}")
        except Exception as commit_error:
            frappe.log_error(f"Database commit failed for member_doc_name {member_doc_name}: {str(commit_error)}", "QR CheckIn Commit Error")
            return {"status": "error", "message": f"Database commit failed: {str(commit_error)}"}
        
        # Send OTP via Email with enhanced message
        try:
            frappe.sendmail(
                recipients=member_data.email_address,
                subject="QR Check-In OTP Verification",
                message=f"""
                Hello {member_data.member_name},
                
                Your one-time password for check-in is: <strong>{otp}</strong>
                
                This OTP will expire in 5 minutes.
                Member ID: {member_id}
                
                If you didn't request this, please ignore this email.
                """,
                sender="franciskamande2001@gmail.com"
            )
            print(f"OTP email sent to {member_data.email_address} for member_doc_name {member_doc_name}")
        except Exception as email_error:
            frappe.log_error(f"Email sending failed for member_doc_name {member_doc_name}: {str(email_error)}", "QR CheckIn Email Error")
            # Continue with success response as OTP is stored
        
        return {
            "status": "success", 
            "message": "OTP sent successfully",
            "member_name": member_data.member_name,
            "expires_in": "5 minutes"
        }
    except frappe.DoesNotExistError as dne:
        frappe.log_error(f"Member not found for member_id {member_id}: {str(dne)}", "QR CheckIn Error")
        return {"status": "error", "message": f"Could not find Member: {member_id}"}
    except frappe.exceptions.ValidationError as ve:
        frappe.log_error(f"Validation error in send_otp for member_id {member_id}: {str(ve)}", "QR CheckIn Error")
        return {"status": "error", "message": f"Validation error: {str(ve)}"}
    except Exception as e:
        frappe.log_error(f"Unexpected error in send_otp for member_id {member_id}, token {token}: {str(e)}", "QR CheckIn Error")
        return {"status": "error", "message": f"Unexpected error while sending OTP: {str(e)}"}

@frappe.whitelist(allow_guest=True)
def verify_otp(member_id, token, otp):
    """
    Verify OTP and process check-in with enhanced status handling
    """
    try:
        print(f"Processing verify_otp with member_id: {member_id}, token: {token}, otp: {otp}")
        
        # Find Member document name
        member = frappe.get_all(
            "Member",
            filters={"member_id": member_id, "is_active": 1},
            fields=["name", "member_name"]
        )
        if not member and str(member_id).isdigit():
            print(f"Member not found with string member_id {member_id}, trying integer {int(member_id)}")
            member = frappe.get_all(
                "Member",
                filters={"member_id": int(member_id), "is_active": 1},
                fields=["name", "member_name"]
            )
        print(f"Found member for member_id {member_id}: {member}")
        
        if not member:
            return {"status": "error", "message": f"Invalid Member ID {member_id} or inactive member"}
        
        member_doc_name = member[0].name
        print(f"Using member_doc_name: {member_doc_name}")
        
        # Find valid OTP record
        print(f"Checking OTP Record for member_doc_name: {member_doc_name}, token: {token}, is_used: 0, attempts < 3")
        otp_records = frappe.get_all(
            "OTP Record",
            filters={
                "member_id": member_doc_name,
                "token": token,
                "is_used": 0,
                "attempts": ["<", 3]
            },
            fields=["name", "otp", "expiry", "attempts", "max_attempts"],
            order_by="creation desc",
            limit=1
        )
        print(f"OTP Record query result: {otp_records}")
        
        if not otp_records:
            all_otp_records = frappe.get_all(
                "OTP Record",
                filters={"member_id": member_doc_name, "token": token},
                fields=["name", "otp", "expiry", "is_used", "attempts", "max_attempts", "created_at"]
            )
            print(f"All OTP Records for member_doc_name {member_doc_name}, token {token}: {all_otp_records}")
            return {"status": "error", "message": "No valid OTP found or maximum attempts exceeded. Please request a new OTP."}
        
        otp_doc = frappe.get_doc("OTP Record", otp_records[0].name)
        print(f"Found OTP Record: {otp_doc.as_dict()}")
        
        # Check expiry
        if get_datetime(otp_doc.expiry) < now_datetime():
            print(f"OTP expired: {otp_doc.expiry} < {now_datetime()}")
            return {"status": "error", "message": "OTP has expired. Please request a new OTP."}
        
        # Verify OTP
        if hashlib.sha256(otp.encode()).hexdigest() != otp_doc.otp:
            try:
                otp_doc.attempts += 1
                otp_doc.save(ignore_permissions=True)
                frappe.db.commit()
                print(f"Invalid OTP, attempts incremented to {otp_doc.attempts}")
            except Exception as e:
                frappe.log_error(f"Failed to update OTP attempts for {otp_doc.name}: {str(e)}", "QR CheckIn OTP Update Error")
                return {"status": "error", "message": f"Failed to update OTP attempts: {str(e)}"}
            
            remaining = otp_doc.max_attempts - otp_doc.attempts
            if remaining <= 0:
                return {"status": "error", "message": "Maximum OTP attempts exceeded. Please request a new OTP."}
            
            return {
                "status": "error",
                "message": f"Invalid OTP. {remaining} attempts remaining"
            }
        
        # Get session and member details
        try:
            qr_session_name = frappe.get_value("QR CheckIn Session", {"token": token}, "name")
            print(f"QR Session name: {qr_session_name}")
            if not qr_session_name:
                return {"status": "error", "message": "Invalid QR session token."}
            session_doc = frappe.get_doc("QR CheckIn Session", qr_session_name)
        except Exception as e:
            frappe.log_error(f"Failed to get QR CheckIn Session for token {token}: {str(e)}", "QR CheckIn Session Error")
            return {"status": "error", "message": f"Invalid QR session: {str(e)}"}
        
        # Get Member data
        try:
            member_data = frappe.get_doc("Member", member_doc_name)
        except Exception as e:
            frappe.log_error(f"Failed to get Member {member_doc_name}: {str(e)}", "QR CheckIn Member Error")
            return {"status": "error", "message": f"Member {member_id} not found: {str(e)}"}
        
        # Determine check-in status
        current_time = now_datetime()
        is_late = get_datetime(session_doc.expiry) < current_time
        status = "Late" if is_late else "Present"
        print(f"Check-in status: {status}, current_time: {current_time}, session_expiry: {session_doc.expiry}")
        
        # Check for duplicate check-in
        try:
            existing_checkin = frappe.get_all(
                "Attendance CheckIn",
                filters={
                    "member_id": member_doc_name,  # Use Member document name
                    "qr_session": qr_session_name
                },
                limit=1
            )
            print(f"Duplicate check-in query result: {existing_checkin}")
        except Exception as e:
            frappe.log_error(f"Failed to check for duplicate check-in for member_doc_name {member_doc_name}: {str(e)}", "QR CheckIn Duplicate Check Error")
            return {"status": "error", "message": f"Failed to check for duplicate check-in: {str(e)}"}
        
        if existing_checkin:
            print(f"Duplicate check-in found for member_doc_name {member_doc_name}, qr_session {qr_session_name}")
            return {"status": "error", "message": "You have already checked in for this session"}
        
        # Create check-in record
        try:
            checkin = frappe.get_doc({
                "doctype": "Attendance CheckIn",
                "member_id": member_doc_name,  # Use Member document name
                "qr_session": qr_session_name,
                "token": token,
                "checkin_time": current_time,
                "status": status,
                "remarks": f"Checked in via QR code {'(Late)' if is_late else ''}"
            })
            checkin.insert(ignore_permissions=True)
            print(f"Check-in record created for member_doc_name {member_doc_name}")
        except Exception as e:
            frappe.log_error(f"Failed to create Attendance CheckIn for member_doc_name {member_doc_name}: {str(e)}", "QR CheckIn Insert Error")
            return {"status": "error", "message": f"Failed to create check-in record: {str(e)}"}
        
        # Update session statistics
        try:
            session_doc.total_checkins += 1
            session_doc.last_checkin_at = current_time
            session_doc.is_used = 1
            session_doc.save(ignore_permissions=True)
            print(f"Session statistics updated: total_checkins {session_doc.total_checkins}")
        except Exception as e:
            frappe.log_error(f"Failed to update QR CheckIn Session {qr_session_name}: {str(e)}", "QR CheckIn Session Update Error")
            return {"status": "error", "message": f"Failed to update session statistics: {str(e)}"}
        
        # Mark OTP as used
        try:
            otp_doc.is_used = 1
            otp_doc.used_at = current_time
            otp_doc.save(ignore_permissions=True)
            print(f"OTP marked as used: {otp_doc.name}")
        except Exception as e:
            frappe.log_error(f"Failed to mark OTP as used for {otp_doc.name}: {str(e)}", "QR CheckIn OTP Update Error")
            return {"status": "error", "message": f"Failed to mark OTP as used: {str(e)}"}
        
        try:
            frappe.db.commit()
            print(f"Database committed for check-in, member_doc_name: {member_doc_name}")
        except Exception as e:
            frappe.log_error(f"Database commit failed for member_doc_name {member_doc_name}: {str(e)}", "QR CheckIn Commit Error")
            return {"status": "error", "message": f"Database commit failed: {str(e)}"}
        
        return {
            "status": "success",
            "message": f"Check-in successful{' (Late)' if is_late else ''}",
            "member_name": member_data.member_name,
            "checkin_time": current_time.strftime("%Y-%m-%d %H:%M:%S"),
            "session_name": session_doc.session_name,
            "checkin_status": status
        }
    except Exception as e:
        frappe.log_error(f"Error in verify_otp for member_id {member_id}, token {token}: {str(e)}", "QR CheckIn Error")
        return {"status": "error", "message": f"OTP verification failed: {str(e)}"}

@frappe.whitelist()
def get_session_stats(token):
    """
    Get statistics for a specific session
    """
    try:
        session = frappe.get_doc("QR CheckIn Session", {"token": token})
        
        # Get check-in statistics
        checkins = frappe.get_all(
            "Attendance CheckIn",
            filters={"qr_session": session.name},
            fields=["member_id", "checkin_time", "status"],
            order_by="checkin_time"
        )
        
        stats = {
            "session_name": session.session_name,
            "total_checkins": len(checkins),
            "present_count": len([c for c in checkins if c.status == "Present"]),
            "late_count": len([c for c in checkins if c.status == "Late"]),
            "start_time": session.start_time,
            "expiry": session.expiry,
            "is_active": session.is_active,
            "checkins": checkins
        }
        
        return {"status": "success", "data": stats}
    except Exception as e:
        frappe.log_error(f"Error in get_session_stats: {str(e)}", "QR CheckIn Error")
        return {"status": "error", "message": str(e)}

@frappe.whitelist()
def deactivate_session(token):
    """
    Manually deactivate a session
    """
    try:
        session = frappe.get_doc("QR CheckIn Session", {"token": token})
        session.is_active = 0
        session.save()
        frappe.db.commit()
        
        return {"status": "success", "message": "Session deactivated successfully"}
    except Exception as e:
        frappe.log_error(f"Error in deactivate_session: {str(e)}", "QR CheckIn Error")
        return {"status": "error", "message": str(e)}

@frappe.whitelist(allow_guest=True)
def get_member_info(member_id):
    """
    Get basic member information for validation
    """
    try:
        # Handle member_id data type conversion
        member = frappe.get_all(
            "Member",
            filters={"member_id": member_id, "is_active": 1},
            fields=["member_name", "email_address", "member_type", "department"]
        )
        
        # If not found with string, try with int conversion
        if not member and str(member_id).isdigit():
            member = frappe.get_all(
                "Member",
                filters={"member_id": int(member_id), "is_active": 1},
                fields=["member_name", "email_address", "member_type", "department"]
            )
        
        if not member:
            return {"status": "error", "message": "Member not found or inactive"}
        
        return {"status": "success", "data": member[0]}
    except Exception as e:
        frappe.log_error(f"Error in get_member_info: {str(e)}", "QR CheckIn Error")
        return {"status": "error", "message": str(e)}