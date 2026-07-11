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