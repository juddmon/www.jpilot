/* www.jpilot.org -- copy buttons and the theme toggle.
   No dependencies; the site works without any of this, it just gets nicer. */
(function () {
  "use strict";

  /* ---- Copy buttons on code blocks -------------------------------------
     Added here rather than in the HTML so the markup stays clean and a
     browser with scripting off never shows a button that cannot work. */
  var ICON =
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" ' +
    'd="M16 1H4a2 2 0 0 0-2 2v14h2V3h12V1zm3 4H8a2 2 0 0 0-2 2v14a2 2 0 0 0 ' +
    '2 2h11a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2zm0 16H8V7h11v14z"/></svg>';

  function copy(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text);
    }
    // Fall back to the old selection trick on plain http.
    return new Promise(function (resolve, reject) {
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      try {
        document.execCommand("copy") ? resolve() : reject();
      } catch (e) {
        reject(e);
      } finally {
        ta.remove();
      }
    });
  }

  Array.prototype.forEach.call(document.querySelectorAll(".code-block"), function (block) {
    var code = block.querySelector("code");
    if (!code) return;

    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "copy-btn";
    btn.setAttribute("aria-label", "Copy the commands to the clipboard");
    btn.innerHTML = ICON + '<span class="copy-label">Copy</span>';

    var label = btn.querySelector(".copy-label");
    var reset;

    btn.addEventListener("click", function () {
      copy(code.innerText).then(
        function () {
          btn.classList.add("copied");
          label.textContent = "Copied";
        },
        function () {
          label.textContent = "Press Ctrl+C";
        }
      );
      clearTimeout(reset);
      reset = setTimeout(function () {
        btn.classList.remove("copied");
        label.textContent = "Copy";
      }, 1600);
    });

    block.appendChild(btn);
  });

  /* ---- Theme toggle ----------------------------------------------------
     The choice is stored so it survives navigation; the inline script in
     <head> reapplies it before the first paint. Starting from whatever the
     OS currently reports means the first click always flips what you see. */
  var btn = document.getElementById("themeBtn");
  if (!btn) return;

  var root = document.documentElement;

  function current() {
    var set = root.getAttribute("data-theme");
    if (set) return set;
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  }

  btn.addEventListener("click", function () {
    var next = current() === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    btn.setAttribute("aria-label", "Switch to the " + (next === "dark" ? "light" : "dark") + " theme");
    try {
      localStorage.setItem("jp-theme", next);
    } catch (e) {
      /* Private browsing, or storage turned off. The toggle still works. */
    }
  });
})();
