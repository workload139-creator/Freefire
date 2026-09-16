const form = document.getElementById("submissionForm");
const button = document.getElementById("submitBtn");

form.addEventListener("submit", function (event) {

    const uid = document.getElementById("uid").value.trim();
    const history = document.getElementById("history").files.length;
    const video = document.getElementById("video").files.length;
    const confirm = document.getElementById("confirm").checked;

    if (!uid || !history || !video || !confirm) {
        event.preventDefault();

        alert("Please complete all required fields.");

        return;
    }

    const ok = confirm(
        "Submit karne ke baad information edit nahi ki ja sakti.\n\nContinue?"
    );

    if (!ok) {
        event.preventDefault();
        return;
    }

    button.disabled = true;
    button.innerText = "🔒 Submitting...";

});
