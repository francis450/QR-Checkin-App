# QR Code Attendance Check-In App

## Overview
The QR Code Attendance Check-In App is a Frappe framework-based application that allows users to check in by scanning a dynamic QR code displayed on a public web page. After scanning, users verify their identity by entering their Member ID and a one-time password (OTP) sent via email. The app ensures secure, time-bound check-ins with a mobile-friendly interface.

### Features
- **Dynamic QR Code**: Generates a new QR code every 5 minutes with a unique token, displayed on a public `/checkin` page.
- **Secure Verification**: Validates Member ID and sends an OTP via email, with a 3-second delay before showing the OTP input field.
- **OTP Validation**: Verifies OTP with a limit of 3 attempts, preventing reuse or expired tokens.
- **Check-In Logging**: Logs successful check-ins with member details and timestamps.
- **Mobile-Friendly UI**: Clean, responsive design for seamless use on mobile devices.
- **Error Handling**: Provides clear error messages for invalid tokens, Member IDs, or OTPs.

## Prerequisites
- **Frappe Framework**: Version 13 or later (tested with Python 3.10).
- **Frappe Bench**: Installed and configured.
- **SMTP Server**: Configured for sending OTP emails.
- **Dependencies**:
  - Python packages: `qrcode`, `pillow`
  - Frappe built-in modules: `frappe.utils`, `frappe.email`

## Installation

1. **Create a New Frappe App**:
   ```bash
   bench new-app qr_checkin
   ```

2. **Install the App**:
   Add the app to your Frappe site:
   ```bash
   bench --site your-site-name install-app qr_checkin
   ```

3. **Install Python Dependencies**:
   Activate the bench virtual environment and install required packages:
   ```bash
   cd ~/frappe-bench
   source env/bin/activate
   pip install qrcode pillow
   ```

4. **Create DocTypes**:
   Create the required DocTypes (`QR CheckIn Session`, `OTP Record`, `Attendance CheckIn`, `Member`) using the provided `doctype_definitions.py` script:
   ```bash
   bench --site your-site-name console
   ```
   ```python
   from qr_checkin.create_doctypes import create_doctypes
   create_doctypes()
   ```
   Alternatively, create them manually via the Frappe Desk UI under **DocType** > **New**.

5. **Configure Email Settings**:
   Update `site_config.json` with your SMTP settings:
   ```json
   {
     "mail_server": "smtp.yourmailserver.com",
     "mail_port": 587,
     "use_ssl": false,
     "use_tls": true,
     "mail_login": "your-email@yourdomain.com",
     "mail_password": "your-password",
     "auto_email_id": "no-reply@yourdomain.com"
   }
   ```
   Run `bench setup mail` for interactive setup if needed.

6. **Set Up Routes**:
   Add the following to `apps/qr_checkin/qr_checkin/hooks.py` to configure routes:
   ```python
   website_route_rules = [
       {"from_route": "/checkin", "to_route": "qr_checkin.html"},
       {"from_route": "/checkin/member", "to_route": "checkin_member.html"}
   ]
   ```

7. **Copy Files**:
   - Place `api.py` in `apps/qr_checkin/qr_checkin/api.py`.
   - Place `qr_checkin.html` and `checkin_member.html` in `apps/qr_checkin/qr_checkin/public/`.
   - Ensure file permissions:
     ```bash
     chmod -R o+rx ~/frappe-bench/apps/qr_checkin
     ```

8. **Restart the Server**:
   ```bash
   bench restart
   ```

## Usage
1. **Access the QR Code Page**:
   - Navigate to `http://your-site/checkin` to view the dynamic QR code.
   - The QR code refreshes every 5 minutes, with a countdown timer displayed.

2. **Scan the QR Code**:
   - Use a mobile device to scan the QR code, which redirects to `/checkin/member?token=<token>`.

3. **Enter Member ID**:
   - Input a valid `Member ID` (ensure a `Member` record exists with `member_id` and `email_address`).
   - An OTP will be sent to the associated email after a 3-second delay.

4. **Verify OTP**:
   - Enter the 6-digit OTP received via email.
   - The system allows up to 3 attempts. Successful verification logs the check-in.

5. **Check Logs**:
   - View saved records in the Frappe Desk UI under `QR CheckIn Session`, `OTP Record`, and `Attendance CheckIn` DocTypes.
   - Check error logs for issues:
     ```bash
     tail -f ~/frappe-bench/logs/error.log
     ```

## File Structure
```
qr_checkin/
├── qr_checkin/
│   ├── public/
│   │   ├── qr_checkin.html
│   │   ├── checkin_member.html
│   ├── api.py
│   ├── create_doctypes.py
│   ├── hooks.py
├── setup.py
├── requirements.txt
```

## Dependencies
Add the following to `apps/qr_checkin/requirements.txt`:
```
qrcode
pillow
```
Install dependencies:
```bash
bench setup requirements
```

## Troubleshooting
- **QR Code Not Displaying**:
  - Verify `qrcode` and `pillow` are installed.
  - Check browser console for JavaScript errors.
- **Records Not Saving**:
  - Ensure DocTypes are created (`QR CheckIn Session`, `OTP Record`, `Attendance CheckIn`, `Member`).
  - Check `error.log` for database or permission issues.
  - Run `bench --site your-site-name console` and test:
    ```python
    print(frappe.db.get_list("QR CheckIn Session"))
    ```
- **OTP Email Not Sending**:
  - Verify SMTP settings in `site_config.json`.
  - Test email sending:
    ```python
    frappe.sendmail(recipients="test@example.com", subject="Test", message="Test")
    ```
- **Clear Cache**:
  ```bash
  bench clear-cache
  ```

## Development Notes
- **Timezone**: Set to `Africa/Nairobi` (EAT, UTC+3) for accurate timestamps:
  ```bash
  bench --site your-site-name set-config time_zone "Africa/Nairobi"
  ```
- **Security**: The app uses hashed OTPs and single-use tokens for security.
- **Guest Access**: DocTypes have `Guest` role permissions for public access.

## License
MIT License. See [LICENSE](LICENSE) for details.

## Contributing
Contributions are welcome! Please submit issues or pull requests to the repository.