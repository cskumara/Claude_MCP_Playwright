const form = document.getElementById("login-form");
const message = document.getElementById("message");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  message.replaceChildren();

  const res = await fetch("/api/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: form.elements.email.value,
      password: form.elements.password.value,
    }),
  });
  const body = await res.json();

  const el = document.createElement("p");
  if (res.ok) {
    el.textContent = "Welcome back";
  } else {
    el.setAttribute("role", "alert");
    el.className = "error";
    el.textContent = body.error || "Login failed";
  }
  message.appendChild(el);
});
