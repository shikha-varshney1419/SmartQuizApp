const form = document.getElementById("signupForm");

form.addEventListener("submit", async (e) => {

    e.preventDefault();

    const formData = new FormData();

    formData.append("name", document.getElementById("name").value);
    formData.append("email", document.getElementById("email").value);
    formData.append("phone", document.getElementById("phone").value);
    formData.append("password", document.getElementById("password").value);

    const file = document.getElementById("profile_pic").files[0];

    if (file) {
        formData.append("profile_pic", file);
    }

    const response = await fetch("/register", {
        method: "POST",
        body: formData
    });

    const data = await response.json();

    alert(data.message);

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