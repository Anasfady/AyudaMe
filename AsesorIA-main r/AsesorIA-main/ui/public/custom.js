/*
 * AsesorIA — targeted interface fixes + welcome layer.
 * 1) Custom editor placeholder with a tax hint.
 * 2) Localization of two strings Chainlit leaves in English
 *    (theme button accessible label and task-stop notice).
 * 3) Welcome cards (3 categories × 9 starter questions) injected next to the
 *    native welcome message, plus a FAB with a persistent quick-question menu.
 * Defensive rules: every injected node carries an id we check first, so the
 * MutationObserver re-run can never duplicate anything; if an anchor, the
 * composer textarea or a feature is missing, that feature silently no-ops.
 */
(function () {
  var PLACEHOLDER = "¿Qué quieres consultar sobre tu documentación?";
  var DEFAULT_MARK = "Escribe tu mensaje";
  var THEME_LABEL = ["Toggle theme", "Cambiar tema"];
  var STOP_NOTICE = [
    "Task manually stopped.",
    "Consulta detenida. Puedes volver a preguntar cuando quieras.",
  ];

  var WELCOME_ID = "ias-welcome-block";
  var FAB_ID = "ias-fab";
  var PANEL_ID = "ias-panel";

  /* Accessible names for the three icon-only Chainlit buttons (WAVE/axe
   * «empty button») + removal of the invalid role="presentation". */
  var BUTTON_LABELS = [
    ["new-chat-button", "Nueva conversación"],
    ["upload-button", "Subir archivo"],
    ["chat-submit", "Enviar mensaje"],
  ];

  var userManualUp = false;
  var lastInteraction = 0;
  var lastScrollH = 0;

  /* Mirrors STARTER_CATEGORIES in ui/app.py (3 categories × 3 questions). */
  var CATEGORIES = [
    {
      icon: "🧾",
      title: "Impuestos y obligaciones fiscales",
      questions: [
        "¿Qué IRPF debo aplicar en mis facturas?",
        "¿Qué gastos son realmente deducibles en Hacienda?",
        "¿Cómo presento los trimestres?",
      ],
    },
    {
      icon: "💶",
      title: "Cuota de autónomos y Seguridad Social",
      questions: [
        "¿Cómo funciona la Tarifa Plana?",
        "¿Qué es la regularización anual por ingresos reales?",
        "¿Cómo cambio mi base de cotización?",
      ],
    },
    {
      icon: "📋",
      title: "Trámites de alta y situaciones especiales",
      questions: [
        "¿Cuándo hay que darse de alta como autónomo?",
        "¿Puedo ser autónomo y tener empleo por cuenta ajena?",
        "¿Qué pasa si me doy de baja médica o cese de actividad?",
      ],
    },
  ];

  function applyPlaceholder() {
    var nodes = document.querySelectorAll("textarea");
    for (var i = 0; i < nodes.length; i++) {
      var ta = nodes[i];
      var current = ta.getAttribute("placeholder") || "";
      if (current.indexOf(DEFAULT_MARK) !== -1 || current === "") {
        if (ta.getAttribute("placeholder") !== PLACEHOLDER) {
          ta.setAttribute("placeholder", PLACEHOLDER);
        }
      }
    }
  }

  function localizeThemeLabel() {
    var spans = document.querySelectorAll(".sr-only");
    for (var i = 0; i < spans.length; i++) {
      if (spans[i].textContent.trim() === THEME_LABEL[0]) {
        spans[i].textContent = THEME_LABEL[1];
      }
    }
  }

  function localizeStopNotice() {
    if (!document.body) return;
    var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    var node;
    while ((node = walker.nextNode())) {
      if (node.data && node.data.trim() === STOP_NOTICE[0]) {
        node.data = " " + STOP_NOTICE[1] + " ";
      }
    }
  }

  /* --- Question dispatch -------------------------------------------------
   * Uses the native value setter + input event so React/Chainlit's state
   * notices the change, then synthesises Enter to submit (same path as a
   * real keystroke). Any missing piece → no-op. */
  function sendQuestion(text) {
    var ta = document.querySelector("textarea");
    if (!ta) return;
    try {
      var proto = window.HTMLTextAreaElement && window.HTMLTextAreaElement.prototype;
      var desc = proto && Object.getOwnPropertyDescriptor(proto, "value");
      if (desc && desc.set) desc.set.call(ta, text);
      else ta.value = text;
      ta.dispatchEvent(new Event("input", { bubbles: true }));
      ta.dispatchEvent(
        new KeyboardEvent("keydown", {
          key: "Enter",
          code: "Enter",
          keyCode: 13,
          which: 13,
          bubbles: true,
        })
      );
    } catch (e) {
      /* fail silently: cards are convenience only */
    }
  }

  function closePanel() {
    var panel = document.getElementById(PANEL_ID);
    if (panel) panel.classList.remove("-ias-open");
  }

  /* --- es-ES document language (Chainlit ships lang="en") ------------- */
  function setLang() {
    if (document.documentElement && document.documentElement.lang !== "es") {
      document.documentElement.lang = "es";
    }
  }

  /* --- Accessible names for icon-only Chainlit buttons ---------------- */
  function localizeButtonLabels() {
    for (var i = 0; i < BUTTON_LABELS.length; i++) {
      var el = document.getElementById(BUTTON_LABELS[i][0]);
      if (!el) continue;
      var current = el.getAttribute("aria-label");
      // Overwrite the generic «Acción» Chainlit/i18n sometimes leaves behind.
      if (!current || current === "Acción" || current === "Action") {
        el.setAttribute("aria-label", BUTTON_LABELS[i][1]);
      }
      if (el.getAttribute("role") === "presentation") {
        el.removeAttribute("role");
      }
    }
  }

  /* --- File inputs without a name get one (WAVE «missing form label») - */
  function labelFileInputs() {
    var inputs = document.querySelectorAll('input[type="file"]');
    for (var i = 0; i < inputs.length; i++) {
      var inp = inputs[i];
      if (inp.getAttribute("aria-label") || inp.closest("label")) continue;
      inp.setAttribute("aria-label", "Seleccionar archivos");
    }
  }

  /* --- The chat area is the page's main landmark ---------------------- *
   * Selected through the message content (.ai-message / step), never by
   * class list alone: several empty divs share the scroller classes. */
  function findThreadScroller() {
    var anchor =
      document.querySelector(".ai-message") ||
      document.querySelector('[id^="step-"]');
    if (!anchor) return null;
    var el = anchor.closest ? anchor.closest("div.overflow-y-auto") : null;
    if (!el || el.closest("#side-view-content")) return null;
    return el;
  }

  function ensureMainLandmark() {
    var el = findThreadScroller();
    if (el && !el.getAttribute("role")) {
      el.setAttribute("role", "main");
      el.setAttribute("aria-label", "Conversación");
    }
  }

  /* --- Composer + watermark live outside every landmark (axe «region») */
  function ensureRegionLandmarks() {
    var composer = document.getElementById("message-composer");
    if (composer && !composer.getAttribute("role")) {
      composer.setAttribute("role", "region");
      composer.setAttribute("aria-label", "Redacción del mensaje");
    }
    var wm = document.querySelector(".watermark");
    if (wm && !wm.getAttribute("role")) {
      wm.setAttribute("role", "contentinfo");
    }
  }

  /* --- Icon-only buttons (Chainlit tooltips only name them on hover) ---- */
  var ICON_LABELS = {
    "lucide-arrow-down": "Ir al final de la conversación",
    "lucide-copy": "Copiar respuesta",
    "lucide-arrow-left": "Cerrar panel lateral",
    "lucide-x": "Cerrar",
    "lucide-rotate-cw": "Regenerar respuesta",
    "lucide-pencil": "Editar mensaje"
  };

  function labelIconButtons() {
    var buttons = document.querySelectorAll("button");
    for (var i = 0; i < buttons.length; i++) {
      var b = buttons[i];
      // The three header buttons are owned by BUTTON_LABELS above.
      if (
        b.id === "new-chat-button" ||
        b.id === "upload-button" ||
        b.id === "chat-submit"
      )
        continue;
      if ((b.textContent || "").trim() || b.getAttribute("aria-label") || b.getAttribute("title"))
        continue;
      var svg = b.querySelector("svg");
      var cls = svg ? svg.getAttribute("class") || "" : "";
      var labeled = false;
      for (var key in ICON_LABELS) {
        if (cls.indexOf(key) >= 0) {
          b.setAttribute("aria-label", ICON_LABELS[key]);
          labeled = true;
          break;
        }
      }
      if (labeled) continue;
      if (/(^|\s)edit-message(\s|$)/.test(b.className || "")) {
        b.setAttribute("aria-label", "Editar mensaje");
        continue;
      }
      if (svg) b.setAttribute("aria-label", "Acción");
    }
  }

  /* --- Composer textarea: placeholder is not a label (WAVE) ------------ */
  function labelComposerInput() {
    var input = document.getElementById("chat-input");
    if (input && !input.getAttribute("aria-label")) {
      input.setAttribute("aria-label", PLACEHOLDER);
    }
  }

  /* --- Heading chain: greeting h1 then an sr-only h2 before the steps'
   * h3 (axe heading-order: h1 -> h3 is an invalid skip). ------------- */
  function ensureHeadingChain() {
    var block = document.getElementById(WELCOME_ID);
    if (!block || !block.parentNode) return;
    var h2 = document.getElementById("ias-thread-heading");
    if (!h2) {
      h2 = document.createElement("h2");
      h2.id = "ias-thread-heading";
      h2.className = "sr-only";
      h2.textContent = "Mensajes de la conversación";
      block.parentNode.insertBefore(h2, block.nextSibling);
      return;
    }
    /* Reposition only when displaced: an unconditional move would fire the
       MutationObserver again and loop forever. */
    if (h2.parentNode !== block.parentNode || block.nextSibling !== h2) {
      block.parentNode.insertBefore(h2, block.nextSibling);
    }
  }

  /* --- Mobile: close Chainlit's side-view dialog on open ---------------
   * On ≤640px the dialog (+backdrop) covers ~85% of the screen with every
   * response. Sources remain fully readable in the in-thread step, so the
   * dialog is closed the moment it appears (animation is zeroed in CSS). */
  function closeMobileSideView() {
    if (!window.matchMedia || !window.matchMedia("(max-width: 640px)").matches)
      return;
    var dialog = document.querySelector('[role="dialog"]');
    if (!dialog || !dialog.querySelector("#side-view-content")) return;
    var buttons = dialog.querySelectorAll("button");
    var target = null;
    for (var i = 0; i < buttons.length; i++) {
      var lab = (
        (buttons[i].getAttribute("aria-label") || "") +
        " " +
        (buttons[i].textContent || "")
      ).toLowerCase();
      if (lab.indexOf("close") !== -1 || lab.indexOf("cerrar") !== -1) {
        target = buttons[i];
        break;
      }
      if (!target && /right-4/.test(buttons[i].className || "")) {
        target = buttons[i];
      }
    }
    if (!target && buttons.length) target = buttons[0];
    if (target && target.click) target.click();
  }

  /* --- Focusables inside aria-hidden subtrees get tabindex=-1 ----------
   * (theme menu open → Radix marks our layer aria-hidden while the FAB
   * stays keyboard-focusable; axe «aria-hidden-focus»). Reversible. */
  function syncAriaHiddenFocus() {
    var roots = [
      document.getElementById(FAB_ID),
      document.getElementById(PANEL_ID),
    ];
    for (var r = 0; r < roots.length; r++) {
      var root = roots[r];
      if (!root) continue;
      var hidden =
        root.getAttribute("aria-hidden") === "true" ||
        (root.closest && root.closest('[aria-hidden="true"]') !== null);
      var focusables = [root];
      var inner = root.querySelectorAll("button, [tabindex]");
      for (var i = 0; i < inner.length; i++) focusables.push(inner[i]);
      for (var f = 0; f < focusables.length; f++) {
        var el = focusables[f];
        if (hidden && el.getAttribute("data-ias-tab") !== "-1") {
          el.setAttribute("data-ias-tab", "-1");
          el.setAttribute("tabindex", "-1");
        } else if (!hidden && el.getAttribute("data-ias-tab") === "-1") {
          el.removeAttribute("data-ias-tab");
          el.removeAttribute("tabindex");
        }
      }
    }
  }

  /* --- Stick-to-bottom: keep the latest state visible after an upload --
   * Chainlit scrolls on new messages but not when the actions row (suggestions)
   * lands afterwards, which left «Documentación disponible» + suggestions
   * behind the composer. Never fights the user: if they scrolled up and are
   * not interacting, nothing moves. */
  function stickToBottom() {
    var el = findThreadScroller();
    if (!el) return;
    var h = el.scrollHeight;
    if (!lastScrollH) {
      lastScrollH = h;
      return;
    }
    var grew = h - lastScrollH;
    lastScrollH = h;
    if (grew <= 16) return;
    var recent = Date.now() - lastInteraction < 8000;
    if (!userManualUp || recent) el.scrollTop = el.scrollHeight;
  }

  function trackUserScroll(event) {
    var t = event.target;
    if (!t || typeof t.scrollHeight !== "number") return;
    var dist = t.scrollHeight - t.scrollTop - t.clientHeight;
    if (dist > 200) userManualUp = true;
    else if (dist < 60) userManualUp = false;
  }

  function trackInteraction() {
    userManualUp = false;
    lastInteraction = Date.now();
  }

  document.addEventListener("scroll", trackUserScroll, true);
  document.addEventListener("pointerdown", trackInteraction, true);
  document.addEventListener("keydown", trackInteraction, true);

  function buildQuestionButton(question, extraClass) {
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = extraClass;
    btn.textContent = question;
    btn.addEventListener("click", function () {
      closePanel();
      sendQuestion(question);
    });
    return btn;
  }

  /* --- Welcome surface: integrated landing hero + light suggestions -----
   * Chainlit 2.12 renders markdown bold as <span class="font-bold"> (no
   * <strong>, no <p>), so the anchor must be found via text nodes. */
  function findTextAnchor(fragment) {
    if (!document.body) return null;
    var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    var node;
    while ((node = walker.nextNode())) {
      if (!node.data || node.data.indexOf(fragment) === -1 || !node.parentElement) {
        continue;
      }
      // Never anchor on our own injected UI (hero/FAB/panel): a menu item
      // like «¿Cómo funciona la Tarifa Plana?» would match the welcome.
      if (
        node.parentElement.closest &&
        node.parentElement.closest('[id^="ias-"], [class*="-ias-"]')
      ) {
        continue;
      }
      return node.parentElement;
    }
    return null;
  }

  function ensureWelcome() {
    var existing = document.getElementById(WELCOME_ID);
    if (existing) {
      // Self-heal: a block that ended up inside the hidden FAB panel (old
      // builds) is removed so the real one can be re-inserted.
      if (existing.closest && existing.closest("#ias-panel")) existing.remove();
      else return;
    }
    var anchor =
      findTextAnchor("Asesor Fiscal IA") || findTextAnchor("Cómo funciona");
    // welcome not visible → wait (never insert at body level)
    if (!anchor || !anchor.parentNode || anchor === document.body) return;

    var block = document.createElement("div");
    block.id = WELCOME_ID;
    block.className = "-ias-welcome";

    // The hero heading is the page's only <h1> (heading structure for AT).
    var greet = document.createElement("h1");
    greet.className = "-ias-greeting";
    greet.textContent = "AsesorIA";
    block.appendChild(greet);

    var tagline = document.createElement("p");
    tagline.className = "-ias-sub";
    tagline.textContent =
      "Consulta tu documentación fiscal con respuestas claras, trazables y basadas en fuentes.";
    block.appendChild(tagline);

    var prompt = document.createElement("div");
    prompt.className = "-ias-prompt";
    prompt.textContent = "¿Qué quieres consultar?";
    block.appendChild(prompt);

    var sugLabel = document.createElement("span");
    sugLabel.className = "-ias-sug-label";
    sugLabel.textContent = "Puedes empezar por:";
    block.appendChild(sugLabel);

    // Three light suggestions (one per topic) — the full set of nine lives
    // in the FAB menu, shown only once the conversation has started.
    var chips = document.createElement("div");
    chips.className = "-ias-grid";
    for (var c = 0; c < CATEGORIES.length; c++) {
      chips.appendChild(
        buildQuestionButton(CATEGORIES[c].questions[0], "-ias-card -ias-chip")
      );
    }
    block.appendChild(chips);

    // Climb to the largest ancestor that contains only the anchor text
    // (typically the anchor's line), then insert before it. No <p> exists
    // in Chainlit's markdown output, so a <div> is always legal here.
    var node = anchor;
    while (
      node.parentElement &&
      node.parentElement !== document.body &&
      node.parentElement.textContent.trim() === node.textContent.trim()
    ) {
      node = node.parentElement;
    }
    node.parentNode.insertBefore(block, node);
  }

  /* --- FAB + persistent quick menu -------------------------------------- *
   * The FAB is «inspiration after starting»: it stays hidden while the
   * thread only holds the welcome message (the hero already offers the
   * first suggestions) and appears from the first exchange onwards. */
  function syncFabVisibility() {
    var fab = document.getElementById(FAB_ID);
    if (!fab) return;
    var started = document.querySelectorAll(".step").length >= 2;
    if (started && fab.classList.contains("-ias-fab-wait")) {
      fab.classList.remove("-ias-fab-wait");
    } else if (!started && !fab.classList.contains("-ias-fab-wait")) {
      fab.classList.add("-ias-fab-wait");
      closePanel();
    }
  }

  function ensureFab() {
    if (!document.getElementById(FAB_ID)) {
      var fab = document.createElement("button");
      fab.id = FAB_ID;
      fab.type = "button";
      fab.className = "-ias-fab";
      fab.setAttribute("aria-label", "Menú de preguntas frecuentes");
      fab.textContent = "☰";
      fab.addEventListener("click", function () {
        var panel = document.getElementById(PANEL_ID);
        if (panel) panel.classList.toggle("-ias-open");
      });
      document.body.appendChild(fab);
    }
    if (!document.getElementById(PANEL_ID)) {
      var panel = document.createElement("div");
      panel.id = PANEL_ID;
      panel.className = "-ias-panel";

      var head = document.createElement("div");
      head.className = "-ias-panel-head";
      head.textContent = "Preguntas frecuentes";
      var close = document.createElement("button");
      close.type = "button";
      close.className = "-ias-panel-close";
      close.setAttribute("aria-label", "Cerrar menú");
      close.textContent = "✕";
      close.addEventListener("click", closePanel);
      head.appendChild(close);
      panel.appendChild(head);

      for (var c = 0; c < CATEGORIES.length; c++) {
        var cat = CATEGORIES[c];
        var group = document.createElement("div");
        group.className = "-ias-menu-group";
        group.textContent = cat.icon + " " + cat.title;
        panel.appendChild(group);
        for (var q = 0; q < cat.questions.length; q++) {
          panel.appendChild(
            buildQuestionButton(cat.questions[q], "-ias-menu-item")
          );
        }
      }
      document.body.appendChild(panel);
    }
  }

  /* --- Skip link (WCAG 2.4.1): first tab stop jumps to the thread ----- */
  function ensureSkipLink() {
    if (!document.body) return;
    var main = findThreadScroller();
    if (!main) return;
    if (!main.getAttribute("tabindex")) main.setAttribute("tabindex", "-1");
    if (!main.getAttribute("id")) main.setAttribute("id", "ias-skip-target");
    var target = "#" + main.getAttribute("id");
    var a = document.getElementById("ias-skip");
    if (!a) {
      a = document.createElement("a");
      a.id = "ias-skip";
      a.className = "-ias-skip";
      a.textContent = "Saltar al contenido";
      a.href = target;
      a.addEventListener("click", function (ev) {
        ev.preventDefault();
        var m = findThreadScroller();
        if (m && m.focus) m.focus();
      });
      document.body.insertBefore(a, document.body.firstChild);
    } else if (a.getAttribute("href") !== target) {
      a.setAttribute("href", target);
    }
  }

  function apply() {
    setLang();
    applyPlaceholder();
    localizeThemeLabel();
    localizeStopNotice();
    localizeButtonLabels();
    labelFileInputs();
    ensureWelcome();
    if (document.body) ensureFab();
    ensureHeadingChain();
    ensureMainLandmark();
    ensureRegionLandmarks();
    ensureSkipLink();
    labelIconButtons();
    labelComposerInput();
    syncFabVisibility();
    closeMobileSideView();
    syncAriaHiddenFocus();
    stickToBottom();
  }

  apply();

  if (window.MutationObserver) {
    new MutationObserver(apply).observe(document.body, {
      childList: true,
      subtree: true,
    });
  }
})();
