const form = document.getElementById(
    "submissionForm"
);

if (form) {

    form.addEventListener(
        "submit",
        function(event) {

            const confirmed = confirm(
                "Submit karne ke baad UID, History aur Video edit nahi kiye ja sakte.\n\nKya aap sure hain?"
            );

            if (!confirmed) {

                event.preventDefault();

                return;
            }

            const button =
                document.getElementById(
                    "submitBtn"
                );

            if (button) {

                button.disabled = true;

                button.innerText =
                    "🔒 Submitting...";
            }

        }
    );
}
