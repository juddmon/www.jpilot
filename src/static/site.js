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

/* ---- Screenshot viewer -------------------------------------------------
   Opens a screenshot over the page with previous and next controls, so you
   can walk every picture on the page without going back and forth.

   The links still point at the real image, so with scripting off, or if this
   fails, clicking one just opens the file as it always did.

   Everything on a page forms one gallery, in the order it appears in the
   markup -- the sections a screenshot is filed under are a way of laying the
   page out, not a reason to stop stepping through. */
(function () {
  "use strict";

  var gallery = [], seen = {};

  var links = document.querySelectorAll(
    'a.shot, [data-gallery] a[href$=".png"], [data-gallery] a[href$=".jpg"], [data-gallery] a[href$=".gif"]'
  );

  Array.prototype.forEach.call(links, function (a) {
    var href = a.getAttribute("href");
    // The same picture can be linked twice -- the Preferences card and its
    // own tab, say. Point both at one entry rather than showing it twice.
    if (href in seen) {
      a.dataset.jpIndex = seen[href];
      return;
    }
    var img = a.querySelector("img");
    var cap = a.querySelector(".cap");
    var alt = (img && img.getAttribute("alt")) || "";
    gallery.push({
      href: href,
      // An explicit data-title wins, then a card's caption, then the alt text.
      label: a.dataset.title
        || (cap && cap.childNodes[0].textContent.trim())
        || alt
        || a.textContent.trim(),
      detail: (cap && cap.querySelector("span")
        ? cap.querySelector("span").textContent.trim()
        : alt),
    });
    seen[href] = gallery.length - 1;
    a.dataset.jpIndex = gallery.length - 1;
  });

  if (gallery.length < 1) return;
  var group = gallery;

  /* Build the overlay once, and only if there is something to show in it. */
  var box = document.createElement("div");
  box.className = "lightbox";
  box.setAttribute("role", "dialog");
  box.setAttribute("aria-modal", "true");
  box.hidden = true;
  box.innerHTML =
    '<button class="lb-close" type="button" aria-label="Close">&#10005;</button>' +
    '<button class="lb-nav lb-prev" type="button" aria-label="Previous screenshot">&#8249;</button>' +
    '<figure class="lb-figure"><img alt=""><figcaption></figcaption></figure>' +
    '<button class="lb-nav lb-next" type="button" aria-label="Next screenshot">&#8250;</button>';
  document.body.appendChild(box);

  var image = box.querySelector("img"),
      caption = box.querySelector("figcaption"),
      prev = box.querySelector(".lb-prev"),
      next = box.querySelector(".lb-next"),
      close = box.querySelector(".lb-close");

  var at = 0, opener = null;

  function show(i) {
    at = (i + group.length) % group.length;
    var item = group[at];
    image.src = item.href;
    image.alt = item.detail || item.label;
    caption.textContent = group.length > 1
      ? item.label + "  —  " + (at + 1) + " of " + group.length
      : item.label;
    box.setAttribute("aria-label", item.label);
    // Only offer navigation when there is somewhere to go.
    prev.hidden = next.hidden = group.length < 2;
    // Fetch the neighbours so stepping through does not flash.
    if (group.length > 1) {
      [at + 1, at - 1].forEach(function (n) {
        new Image().src = group[(n + group.length) % group.length].href;
      });
    }
  }

  function open(i, from) {
    opener = from;
    box.hidden = false;
    document.body.classList.add("lb-open");
    show(i);
    close.focus();
  }

  function shut() {
    box.hidden = true;
    document.body.classList.remove("lb-open");
    image.removeAttribute("src");
    // Put focus back where it came from, or the page loses its place.
    if (opener) { opener.focus(); opener = null; }
  }

  document.addEventListener("click", function (e) {
    var a = e.target.closest ? e.target.closest("a[data-jp-index]") : null;
    if (!a) return;
    // Leave modified clicks alone: they mean "open this somewhere else".
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return;
    e.preventDefault();
    open(+a.dataset.jpIndex, a);
  });

  prev.addEventListener("click", function () { show(at - 1); });
  next.addEventListener("click", function () { show(at + 1); });
  close.addEventListener("click", shut);
  box.addEventListener("click", function (e) {
    // A click on the backdrop, rather than on the picture or a button.
    if (e.target === box || e.target.classList.contains("lb-figure")) shut();
  });

  document.addEventListener("keydown", function (e) {
    if (box.hidden) return;
    if (e.key === "Escape") { shut(); return; }
    if (group.length < 2) return;
    if (e.key === "ArrowLeft") { e.preventDefault(); show(at - 1); }
    if (e.key === "ArrowRight") { e.preventDefault(); show(at + 1); }
  });

  /* Keep tabbing inside the overlay while it is open. */
  box.addEventListener("keydown", function (e) {
    if (e.key !== "Tab") return;
    var stops = [close, prev, next].filter(function (b) { return !b.hidden; });
    var i = stops.indexOf(document.activeElement);
    e.preventDefault();
    stops[(i + (e.shiftKey ? -1 : 1) + stops.length) % stops.length].focus();
  });

  /* Swipe, for touch screens. */
  var x0 = null;
  box.addEventListener("touchstart", function (e) { x0 = e.touches[0].clientX; }, { passive: true });
  box.addEventListener("touchend", function (e) {
    if (x0 === null || group.length < 2) return;
    var dx = e.changedTouches[0].clientX - x0;
    if (Math.abs(dx) > 45) show(at + (dx < 0 ? 1 : -1));
    x0 = null;
  }, { passive: true });
})();
