const urlParams = new URLSearchParams(window.location.search);
const token = urlParams.get('token');

function showError(message) {
    $("#error-message").text(message).show();
    $("#success-message").hide();
}

function showSuccess(message) {
    $("#success-message").text(message).show();
    $("#error-message").hide();
}

function submitMemberId() {
    const memberId = $("#member-id").val();
    if (!memberId) {
        showError("Please enter a Member ID");
        return;
    }

    $.ajax({
        url: "/api/method/qr_checkin.api.validate_qr_token",
        method: "GET",
        data: { token: token },
        success: function (responses) {
            console.log("responses: " + responses)
            let response = responses.message;
            console.log("Response: " + response)
            console.log("X-Frappe-CSRF-Token: " + csrf_token)
            if (response.status !== "success") {
                showError(response.message);
                return;
            }

            $.ajax({
                url: "/api/method/qr_checkin.api.send_otp",
                method: "POST",
                data: { member_id: memberId, token: token },
                headers: {
                    "X-Frappe-CSRF-Token": csrf_token // Add CSRF token
                },
                success: function (responses) {
                    // {
                    //     "message": {
                    //         "status": "success",
                    //         "message": "OTP sent successfully",
                    //         "member_name": "Francis",
                    //         "expires_in": "5 minutes"
                    //     }
                    // }
                    let response = responses.message;
                    if (response.status === "success") {
                        setTimeout(() => {
                            $("#member-id-section").hide();
                            $("#otp-section").show();
                        }, 3000);
                    } else {
                        showError(response.message);
                    }
                },
                error: function () {
                    showError("Error sending OTP");
                }
            });
        },
        error: function () {
            showError("Error validating token");
        }
    });
}

function submitOTP() {
    const otp = $("#otp").val();
    const memberId = $("#member-id").val();
    if (!otp) {
        showError("Please enter OTP");
        return;
    }

    $.ajax({
        url: "/api/method/qr_checkin.api.verify_otp",
        method: "POST",
        data: { member_id: memberId, token: token, otp: otp },
        headers: {
            "X-Frappe-CSRF-Token": csrf_token // Add CSRF token
        },
        success: function (responses) {
            console.log("responses: " + responses)
            // response body
            // "message": {
            //         "status": "success",
            //         "message": "Check-in successful",
            //         "member_name": "Francis",
            //         "checkin_time": "2025-06-09 15:39:58",
            //         "session_name": "Check-in Session 2025-06-09 15:38",
            //         "checkin_status": "Present"
            //     }
            // }

            // Console log the response
            console.log("Response: " + JSON.stringify(responses));
            let response = responses.message;
            if (response.status === "success") {
                showSuccess(response.message);
                $("#otp-section").hide();
            } else {
                showError(response.message);
            }
        },
        error: function () {
            showError("Error verifying OTP");
        }
    });
}