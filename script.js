
// Mobile menu toggle functionality
document.addEventListener('DOMContentLoaded', function() {
  const menuToggle = document.getElementById('menu-toggle');
  const navMenu = document.querySelector('nav ul');
  
  console.log('Menu toggle element:', menuToggle);
  console.log('Nav menu element:', navMenu);
  
      if (menuToggle && navMenu) {
      menuToggle.addEventListener('click', function() {
        console.log('Menu toggle clicked!');
        const nav = navMenu.parentElement;
        nav.classList.toggle('show');
        navMenu.classList.toggle('show');
        console.log('Nav menu classes:', navMenu.className);
      });
      
      // Close menu when clicking on menu items
      const menuItems = navMenu.querySelectorAll('a');
      menuItems.forEach(function(item) {
        item.addEventListener('click', function() {
          console.log('Menu item clicked, closing menu');
          const nav = navMenu.parentElement;
          nav.classList.remove('show');
          navMenu.classList.remove('show');
        });
      });
    } else {
      console.error('Menu toggle or nav menu not found!');
    }
});

// Check login status and update navigation
function updateNavigation() {
  const isLoggedIn = localStorage.getItem("isLoggedIn");
  const loginLink = document.getElementById("loginLink");
  const registerLink = document.getElementById("registerLink");

  if (isLoggedIn && loginLink && registerLink) {
    loginLink.innerHTML = '<a href="dashboard.html">Dashboard</a>';
    registerLink.innerHTML = '<a href="#" id="logoutBtn">Logout</a>';

    // Add logout functionality
    document
      .getElementById("logoutBtn")
      .addEventListener("click", function (e) {
        e.preventDefault();
        localStorage.removeItem("user");
        localStorage.removeItem("isLoggedIn");
        window.location.reload();
      });
  }
}

// BMI Calculator
function calculateBMI() {
  const height = parseFloat(document.getElementById("height").value) / 100;
  const weight = parseFloat(document.getElementById("weight").value);
  const bmi = weight / (height * height);
  const result = document.getElementById("bmiResult");

  if (isNaN(bmi)) {
    result.innerText = "Please enter valid height and weight.";
  } else {
    let category = "";
    if (bmi < 18.5) category = "Underweight";
    else if (bmi < 24.9) category = "Normal weight";
    else if (bmi < 29.9) category = "Overweight";
    else category = "Obese";

    result.innerText = `Your BMI is ${bmi.toFixed(2)} (${category})`;
  }
}

// Contact Form with API
document
  .getElementById("contactForm")
  .addEventListener("submit", async function (e) {
    e.preventDefault();

    const formData = new FormData(this);
    const name =
      formData.get("name") || this.querySelector('input[type="text"]').value;
    const email =
      formData.get("email") || this.querySelector('input[type="email"]').value;
    const message =
      formData.get("message") || this.querySelector("textarea").value;

    try {
      const response = await fetch("http://localhost:8000/api/contact", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: name,
          email: email,
          message: message,
        }),
      });

      const data = await response.json();

      if (data.success) {
        alert("Thank you for your message! We will get back to you soon.");
        this.reset();
      } else {
        alert("Failed to send message. Please try again.");
      }
    } catch (error) {
      alert("Connection error. Please check if the server is running.");
    }
  });

// Plan Selection Buttons
document.addEventListener("DOMContentLoaded", function () {
  const planButtons = document.querySelectorAll(
    ".pricing-option .btn, .plan-cta .btn-large"
  );

  planButtons.forEach((button) => {
    button.addEventListener("click", function (e) {
      e.preventDefault();
      const planName =
        this.closest(".pricing-option")?.querySelector("h3")?.textContent ||
        this.closest(".plan-cta")?.querySelector("h2")?.textContent ||
        "this plan";

      // If this is the Buy Membership button, use new logic
      if (this.id === "buyMembershipBtn") {
        // Check if user is logged in
        const isLoggedIn = localStorage.getItem("isLoggedIn");
        const user = localStorage.getItem("user");
        if (!isLoggedIn || !user) {
          if (
            confirm("You need to be logged in to buy a membership. Login now?")
          ) {
            window.location.href = "login.html";
          }
          return;
        }
        // Show payment modal (simulate QR code/payment)
        // For now, just confirm purchase
        if (confirm(`Proceed to buy the ${planName} membership?`)) {
          // Save membership to backend (simulate payment success)
          const userData = JSON.parse(user);
          fetch("http://localhost:8000/api/membership", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              user_id: userData.id,
              plan_type: planName.toLowerCase(),
            }),
          })
            .then((res) => res.json())
            .then((data) => {
              if (data.success) {
                alert(
                  "Membership purchased successfully! You can view it on your dashboard."
                );
                window.location.href = "dashboard.html";
              } else {
                alert("Failed to purchase membership: " + data.message);
              }
            })
            .catch(() => {
              alert("Error connecting to server. Please try again later.");
            });
        }
        return;
      }

      // Old alert for other plan buttons
      alert(
        `Thank you for choosing ${planName}! Our team will contact you within 24 hours to complete your membership.`
      );
    });
  });

  // Update navigation on page load
  updateNavigation();
});

function buyMembership(plan) {
  window.location.href = `buy-membership.html?plan=${encodeURIComponent(plan)}`;
}
