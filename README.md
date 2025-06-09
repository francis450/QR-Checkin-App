# QR Code Attendance Check-In App

## Overview
The QR Code Attendance Check-In App is a Frappe framework-based application that allows users to check in by scanning a dynamic QR code displayed on a public web page. After scanning, users verify their identity by entering their Member ID and a one-time password (OTP) sent via email. The app ensures secure, time-bound check-ins with a mobile-friendly interface.

## Features

- Dynamic QR code generation for each check-in session
- OTP-based identity verification via email
- Secure, time-limited check-in process
- Mobile-friendly and responsive web interface
- Integration with Frappe user and email systems

## Installation

1. Navigate to your Frappe bench directory:
   ```bash
   cd /path/to/frappe-bench
   ```
2. Get the app:
   ```bash
   bench get-app qr_checkin
   ```
3. Install the app on your site:
   ```bash
   bench --site your-site-name install-app qr_checkin
   ```
4. Run migrations:
   ```bash
   bench --site your-site-name migrate
   ```

## Usage

1. Log in to your Frappe site as an administrator.
2. Configure email settings to enable OTP delivery.
3. Access the QR Check-In page from the web interface.
4. Users scan the QR code, enter their Member ID, and verify with the OTP sent to their email.
5. Attendance is recorded and can be viewed in the admin dashboard.

## Configuration

- Ensure email settings are correctly configured in Frappe.
- Set up user accounts with valid email addresses.
- Adjust QR code expiry and OTP validity in the app settings if needed.

## Contributing

Contributions are welcome! Please open issues or submit pull requests for improvements or bug fixes.

## License

This project is licensed under the MIT License.