const form = document.getElementById("loginForm");

form.addEventListener("submit", async (e) => {

    e.preventDefault();

    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value.trim();

    try {

        const response = await fetch("/login", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                email: email,
                password: password
            })

        });

        const data = await response.json();

        if (response.ok && data.message === "Login Successful") {

            window.location.href = data.redirect;

        } else {

            alert(data.message);

        }

    } catch (error) {

        alert("Server Error! Please try again.");

        console.error(error);

    }

});

function togglePassword() {

    var password = document.getElementById("password");
    var eye = document.getElementById("eyeIcon");

    if (password.type === "password") {
        password.type = "text";
        eye.classList.remove("fa-eye");
        eye.classList.add("fa-eye-slash");
    } else {
        password.type = "password";
        eye.classList.remove("fa-eye-slash");
        eye.classList.add("fa-eye");
    }

}