function parseDateTime(dateTimeStr) {
    try {
        const [date, time] = dateTimeStr.split(' ');
        const [year, month, day] = date.split('-').map(Number);
        const [hours, minutes, seconds] = time.split(':').map(Number);
        return new Date(year, month - 1, day, hours, minutes, seconds).getTime();
    } catch (e) {
        console.error("Error parsing date:", dateTimeStr, e);
        return null;
    }
}

function updateQRCode() {
    $.ajax({
        url: "/api/method/qr_checkin.api.generate_qr_code",
        method: "GET",
        success: function (response) {
            if (response.message && response.message.qr_image) {
                $("#qr-image").attr("src", response.message.qr_image);
                const expiryTime = parseDateTime(response.message.expiry);
                if (expiryTime) {
                    startCountdown(expiryTime);
                } else {
                    $("#error-message").text("Invalid expiry timestamp").show();
                }
            } else {
                $("#error-message").text("Invalid response from server").show();
            }
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.error("QR code fetch error:", textStatus, errorThrown);
            $("#error-message").text("Error loading QR code").show();
        }
    });
}

function startCountdown(expiryTime) {
    const countdownElement = $("#countdown");
    const updateCountdown = () => {
        const now = new Date().getTime();
        const distance = expiryTime - now;
        if (distance <= 0) {
            countdownElement.text("Refreshing QR code...");
            updateQRCode();
            return;
        }
        const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((distance % (1000 * 60)) / 1000);
        countdownElement.text(`QR code expires in ${minutes}m ${seconds}s`);
        setTimeout(updateCountdown, 1000);
    };
    updateCountdown();
}

$(document).ready(function () {
    updateQRCode();
});