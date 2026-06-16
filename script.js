/* =========================================================
   Meesterhand — interactions
   Kept minimal and deliberate. CSS does the heavy lifting.
   ========================================================= */
(function () {
  "use strict";

  /* ---- Nav: subtle border once the page is scrolled ---- */
  var nav = document.getElementById("nav");
  if (nav) {
    var onScroll = function () {
      nav.setAttribute("data-scrolled", window.scrollY > 8 ? "true" : "false");
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  /* ---- Mobile drawer ---- */
  var body = document.body;
  var toggle = document.getElementById("navToggle");
  var scrim = document.getElementById("scrim");
  var drawer = document.getElementById("drawer");

  function setMenu(open) {
    body.setAttribute("data-menu", open ? "open" : "closed");
    if (toggle) {
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
      toggle.setAttribute("aria-label", open ? "Menu sluiten" : "Menu openen");
    }
    if (scrim) {
      // toggle hidden after the transition so it stays focus/click-safe
      if (open) {
        scrim.hidden = false;
      } else {
        window.setTimeout(function () {
          if (body.getAttribute("data-menu") === "closed") scrim.hidden = true;
        }, 360);
      }
    }
  }

  if (toggle) {
    toggle.addEventListener("click", function () {
      setMenu(body.getAttribute("data-menu") !== "open");
    });
  }
  if (scrim) scrim.addEventListener("click", function () { setMenu(false); });
  if (drawer) {
    drawer.querySelectorAll("a").forEach(function (a) {
      a.addEventListener("click", function () { setMenu(false); });
    });
  }
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && body.getAttribute("data-menu") === "open") {
      setMenu(false);
    }
  });

  /* ---- Reveal on scroll (IntersectionObserver) ---- */
  var reveals = document.querySelectorAll(".reveal");
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  if (reduce || !("IntersectionObserver" in window)) {
    reveals.forEach(function (el) { el.classList.add("is-in"); });
  } else {
    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-in");
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -60px 0px" }
    );

    // Gentle stagger for groups sharing a parent
    var groups = new Map();
    reveals.forEach(function (el) {
      var key = el.parentElement;
      var i = groups.get(key) || 0;
      el.style.transitionDelay = Math.min(i * 60, 240) + "ms";
      groups.set(key, i + 1);
      io.observe(el);
    });
  }

  /* ---- Contact form (no backend — graceful confirmation) ---- */
  var form = document.getElementById("contactForm");
  if (form) {
    var success = document.getElementById("formSuccess");
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      if (!form.checkValidity()) {
        form.reportValidity();
        return;
      }
      form.reset();
      if (success) {
        success.classList.add("is-visible");
        success.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "center" });
      }
    });
  }
})();
