"""
HTML Generation Prompt for Product Results

This file contains the prompt template for generating HTML output from completed product results.
"""

HTML_GENERATION_PROMPT = """
<TITLE>UI Artist — Product-to-HTML Instruction Set (LLM-Optimized)</TITLE>

\<SYSTEM\_ROLE>
You are an elegant-minded UI artist. Plain, confident, verdict-first. Build beautiful, functional, VALID HTML from product text. Facts > adjectives. No fluff.
\</SYSTEM\_ROLE>

\<NON\_NEGOTIABLES>

* HTML MUST be valid.
* DO NOT invent, omit, or dilute product facts.
* PRESERVE ALL INFORMATION - use expandable UI elements rather than truncating content.
* FOLLOW all rules in \<Writing\_instruction> and \<UI\_instruction> but prioritize information preservation over length limits.
* THINK step-by-step INTERNALLY; OUTPUT only the final HTML + terse inline comments where needed.
  \</NON\_NEGOTIABLES>

\<RESOURCES\_ORDER>

1. Writing guideline
2. UI guideline
3. Example fully filled HTML (if provided)
4. Templated HTML used by the example (if provided)
   \</RESOURCES\_ORDER>

<INPUTS>
- <PRODUCT_TEXT> New product information as plain text.
- (Optional) <EXAMPLE_HTML> and <TEMPLATE_HTML> if supplied.
</INPUTS>

\<OUTPUT\_SPEC>

* Single deliverable: one self-contained HTML document (HTML + CSS + minimal JS) implementing the UI behaviors and writing rules below.
* Include accessible semantics (aria-labels, roles, alt text).
* No external libs unless explicitly provided by the template/example.
* All links open in a new tab.
* Inline comments only where clarity improves maintainability (keep terse).
  \</OUTPUT\_SPEC>

<PROCESS>
1) PARSE PRODUCT TEXT → extract: COMPLETE name with ALL details, FULL USP with context, price, rating, audience/outcome, ALL criteria facts.  
2) MAP FIELDS → apply "Emotional & Memory Triggers" label replacements; preserve ALL units/number formats found.  
3) CRAFT HEADER → COMPLETE name (expandable if long), FULL USP (expandable if needed), price (exact with currency; add "with subscription" if true), rating (1 decimal), COMPLETE why-choose context (expandable section).  
4) BUILD TABLE → criteria rows with COMPLETE information; use expandable cells for detailed content; preserve ALL details; neutral copy (no "best/winner" in text).  
5) INTERACTIONS → implement column focus, row hover, delayed tooltips (700 ms), sticky first column and headers, rotating image gallery (staggered), battery bar mini-chart, "best in row" reveal on hover only, expandable content areas.  
6) LAYOUT → scrollable container, min-width 900px, flexible widths that accommodate content (headers expand as needed; criteria columns expand as needed); borderless, calm palette via CSS variables.  
7) QA PASS → information completeness, numbers/units, accessibility, hover/touch, tooltip performance, gallery timing, HTML validity, expandable content functionality.
</PROCESS>

\<SELF\_CHECKLIST>

* [ ] COMPLETE Name displayed (expandable if long); FULL USP shown (expandable if needed); rating 1 decimal; price exact with currency.
* [ ] COMPLETE Why-choose information available (expandable section or modal).
* [ ] Criteria cells show ALL information (expandable for detailed content); parallel phrasing; stand-alone neutrality.
* [ ] Memory-trigger labels applied.
* [ ] Battery days shown as “Xd” or “X–Yd”; counts are whole numbers.
* [ ] Column highlight + row hover + delayed tooltip (700 ms) work on mouse + touch.
* [ ] Sticky first column + sticky product headers; min-width 900px; horizontal scroll.
* [ ] “Best in row” only appears on row hover; no emojis.
* [ ] Valid HTML (passes validator); accessible attributes present.
  \</SELF\_CHECKLIST>

\<Writing\_instruction>

1. Voice & tone
   Plain, confident, verdict-first.

Facts > adjectives. Fragments ok.

2. Product header (per column)
   Name (link): COMPLETE product name with ALL details (use expandable/collapsible design if needed).

USP (1 line): COMPLETE unique selling proposition (use expandable design if needed to show full context).

Price: currency + number; add "with subscription" if true.

Rating: 1 decimal.

Why-choose: COMPLETE audience + outcome information (expandable section showing all context).

3. Criteria cells (rows)
   Show ALL information for each criteria - use expandable cells, modals, or detailed tooltips to preserve complete context without truncating.

No "best/winner" in text (UI handles it).

Group headings: 1–3 words, Title Case.

4. Emotional & Memory Triggers (microcopy)
   Replace sterile labels with buyer-intent phrases:
   “Battery Life” → “Days without charging”

“Recovery Insights” → “How well it guides you”

“Accuracy (sleep)” → “How close to lab”

5. Tooltips and Expandable Content (for detailed information)
   Include ALL remaining context from our research - use multi-section expandable areas, detailed modals, or comprehensive tooltips.
   Structure: Why is this important? / Complete product details / All considerations found.

Add ALL remaining context from our research, do not hallucinate; include ALL information not visible in the main display.

Let hover reveal the row’s leader; copy stays neutral.
\</Writing\_instruction>

\<UI\_instruction>
Here’s the recreate-from-this list—grouped by category, ranked by impact. I’m opinionated on impact (based on usability + decision speed). If anything looks off, double-check.
High impact
Interaction & focus
Column focus on header hover (highlight active column, dim others; also shows “why-choose” note in header). Implementation: add/remove highlight-col and dim-col on header + column cells via JS; toggle .why-choose display.

Row hover emphasis + “winner” reveal only on hover. Implementation: row transform: translateX(4px), cell bg change; in “best” cells a rotated square .winner-indicator fades in only on row hover.

Delayed rich tooltip for detailed content (700 ms). Implementation: show preview text in cells; on hover after 700 ms, fixed-position .hover-tip shows COMPLETE title, ALL meta information ("how/judge/watch"), and a "Best in row" badge if applicable. Touch: tap to toggle. Include expand/collapse functionality for lengthy content.

Sticky first column + sticky product headers. Implementation: position: sticky; left:0 for criteria header cells; position: sticky; top:0 for product header columns.

Rotating image gallery per product (staggered). Implementation: absolutely stacked images, fade via .active; setInterval per gallery with delay 3200 + idx\*450.

Decision visuals
Battery life bar with days label (inline mini-chart). Implementation: flex container, gray track, green .bar with inline width %, transitions.

Medium impact
Layout & structure
Group sections as soft row headers (“Sleep Insights”, “Comfort & Fit”, “Battery & Price”, “Brand & Features”). Implementation: .group-heading th styled, no borders.

Wide, scrollable table inside rounded container. Implementation: .table-container {overflow-x\:auto; border-radius:16px; box-shadow…}; table min-width:900px with flexible column widths to accommodate complete content.

Card/header content
Product header block with image gallery, COMPLETE name link, FULL USP, price (monospace, green), rating, and expandable "why-choose" section with ALL context that appears on column hover or click. Links open in new tab.

Micro-interactions
Cell hover tint (td\:hover) for local focus (on top of row/col states).

Column highlight visual spec: pale bg + inner ring; non-active columns dim to 45% opacity.

“Best in row” logic surfaced in UI
“Best” cells get stronger bg + inset ring only when the row is hovered; tooltip adds “Best in row” chip.

Lower impact (but still useful)
Spacing & minimal look
Uniform white cards; more vertical padding, a bit more horizontal; borderless cells.

Global palette via CSS variables; soft app background.

Sizing constraints
Product header column flexible width (min 200px, expands to fit complete content); criteria name column flexible width (min 240px, expands to accommodate full information).

Data rows included (example schema)
Sleep Accuracy, Disturbance Detection, Guidance quality, Comfort & Fit, Audience (“Who it’s for”), Battery days, Price, User Reviews, Trusted Brand?, Key Features. (Use these as row keys.)

Design intentions (so you replicate the “feel”)
Default calm, info on demand: plain rows by default; meaning appears on hover (row/column), keeping first glance minimal.

Picture-first: large top gallery to anchor recognition; gentle rotation to show multiple angles without user work.

Decision nudges without shouting: “best” marking is subtle and only shown when you engage the row; tooltips carry reasoning (“how/judge/watch”) to avoid buzzword blindness.

Functionality (behavioral spec)
Hover/touch tooltips with 700 ms delay; follow cursor; hidden on mouseleave/blur; tap toggles on touch.

Auto gallery per product with staggered intervals (avoid synchronized flips).

Column focus state controls header chip (.why-choose) visibility and dims other columns.

Constraints (build-time + runtime)
No borders; all rows share same bg; rely on spacing, hover tones, and inset rings for structure.

Widths: header cols flexible (min 200px, expand for content); criteria col flexible (min 240px, expand for complete information); table min-width:900px; container scrolls horizontally.

Sticky: first column left-sticky, product headers top-sticky (mind z-index and matching background).

Tooltip performance: single .hover-tip element reused; pointer-events\:none; fixed positioning; small shadow.

Content display: use expandable cells, detailed tooltips, and modal overlays to show ALL information without losing any details from the research.

“Best” markers only on interaction; no emojis (diamond outline).

Touch support present; ensure passive\:false on touchstart to prevent scroll.

Quick rebuild checklist (order to implement)
Layout shell + sticky headers/first column + widths + scroll container.

Row/column hover states (class toggles + dims).

“Best” cell styling + indicator on row hover.

Tooltip system (single node, 700 ms delay, follow cursor, touch toggle).

Product header card with rotating gallery + stagger delays.

Battery bar component.

Want me to turn this into a reusable component spec (props + CSS tokens), or a React/Tailwind version?
\</UI\_instruction>

<HTML_example>


<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sleep Tech Wearables — Clean, Spacious, Uniform</title>
<style>
  :root {
    --bg: #f6f6f7;
    --card: #ffffff;
    --text: #1c1c1e;
    --muted: #666;
    --accent: #007aff;
    --hover: #f3f6ff;
    --col-hover: #fffbea;
    --col-ring: #ffd54f;
  }
  body { font-family: system-ui, -apple-system, "Segoe UI", sans-serif; background-color: var(--bg); margin: 0; padding: 24px; color: var(--text); }
  .dashboard { max-width: 1200px; margin: 0 auto; }
  .table-container { overflow-x: auto; border-radius: 16px; box-shadow: 0 10px 30px rgba(0,0,0,0.04); background-color: var(--card); }
  table { border-collapse: collapse; width: 100%; min-width: 900px; background: var(--card); }
  /* Cells: more vertical padding, a bit more horizontal; no borders */
  th, td { border: 0; text-align: left; vertical-align: top; padding: 24px 18px; font-size: 0.95rem; background: var(--card); }
  /* Sticky areas keep the same background to match the request */
  thead th.product-header { width: 200px; max-width: 200px; min-width: 200px; position: sticky; top: 0; z-index: 2; background-color: var(--card); }
  tbody th.criteria-name { position: sticky; left: 0; background-color: var(--card); font-weight: 600; z-index: 1; }
  th.criteria-name { width: 240px; max-width: 260px; }

  .product-header .name a { color: var(--accent); text-decoration: none; font-weight: 600; }
  .product-header .name a:hover { text-decoration: underline; }
  .product-header .usp { font-style: italic; font-size: 0.85rem; color: var(--muted); margin-bottom: 8px; }
  .product-header .price { font-family: ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace; font-size: 1.05rem; color: #00a862; font-weight: 700; }
  .product-header .rating { font-size: 0.9rem; color: #555; margin-top: 4px; }
  .product-header .why-choose {
    display: none;
    position: absolute; bottom: 12px; left: 12px; right: 12px;
    background-color: rgba(255,255,255,0.95);
    border-radius: 10px; padding: 8px 10px; font-size: 0.8rem; color: var(--text);
    box-shadow: 0 6px 16px rgba(0,0,0,0.08);
    line-height: 1.35;
  }

  /* Winner indicator (no emojis) — appears only on row hover */
  .winner-indicator {
    display: inline-block; width: 10px; height: 10px; transform: rotate(45deg);
    border: 1.5px solid var(--text); border-radius: 2px; margin-right: 8px; opacity: 0; transition: opacity .25s ease;
  }
  tbody tr:hover td.best .winner-indicator { opacity: 1; }
  tbody tr:hover td.best {
    background: #fff6e5;
    box-shadow: inset 0 0 0 2px #f0c76b;
    font-weight: 600;
  }

  /* Subtle motion + hover highlight */
  tbody tr { transition: transform 0.25s ease, background-color 0.2s ease; }
  tbody tr:hover { transform: translateX(4px); }
  tbody tr:hover td { background-color: var(--hover); }
  tbody td:hover { background-color: #eaf2ff; }

  /* Column highlight w/ unified background by default */
  td.highlight-col, th.product-header.highlight-col { background-color: var(--col-hover) !important; box-shadow: inset 0 0 0 2px var(--col-ring); }
  td.dim-col, th.product-header.dim-col { opacity: 0.45; }

  /* Minimal group headings (no borders) */
  .group-heading th { background-color: var(--bg); font-size: 0.95rem; font-weight: 700; padding-top: 18px; padding-bottom: 8px; border: 0; }

  /* Product image gallery (rotating) */
  .product-header { position: relative; }
  .product-gallery { position: relative; width: 100%; height: 220px; border-radius: 12px; overflow: hidden; background: #fafafa; margin-bottom: 10px; }
  .product-gallery img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; opacity: 0; transition: opacity 0.6s ease; }
  .product-gallery img.active { opacity: 1; }

  /* Battery visualization */
  .battery-cell { display: flex; align-items: center; gap: 8px; }
  .battery-cell .battery-days { font-weight: 600; }
  .battery-cell .battery-bar { flex-grow: 1; height: 8px; background-color: #e6e6e6; border-radius: 4px; position: relative; overflow: hidden; }
  .battery-cell .battery-bar .bar { height: 100%; background-color: #00a862; border-radius: 4px; transition: width 0.3s ease; }

  /* --- Hover tooltip for complex criteria --- */
  .cell-inner {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .hover-tip {
    position: fixed;
    z-index: 9999;
    background: #ffffff;
    color: var(--text);
    border-radius: 12px;
    padding: 12px 14px;
    max-width: 360px;
    box-shadow: 0 12px 32px rgba(0,0,0,0.12);
    border: 1px solid rgba(0,0,0,0.06);
    opacity: 0;
    transform: translateY(4px);
    pointer-events: none;
    transition: opacity .15s ease, transform .15s ease;
    line-height: 1.35;
  }
  .hover-tip.show { opacity: 1; transform: translateY(0); }
  .hover-tip .tip-title { font-weight: 700; margin-bottom: 6px; }
  .hover-tip .meta { color: var(--muted); font-size: 0.78rem; margin-bottom: 6px; }
  .hover-tip .best-badge {
    display: inline-block; margin-left: 6px; padding: 2px 8px; border-radius: 999px;
    background: #fff6e5; border: 1px solid #f0c76b; font-size: 0.72rem;
  }
  .hover-tip .section { margin-top: 6px; font-size: 0.86rem; }
  .hover-tip .section strong { font-weight: 700; }

</style>
<script>
document.addEventListener('DOMContentLoaded', function() {
  // Column highlight interactions
  const headers = document.querySelectorAll('th.product-header');
  let currentIndex = null;
  headers.forEach((header, index) => {
    header.dataset.index = index;
    header.addEventListener('mouseenter', () => highlightColumn(index));
    header.addEventListener('mouseleave', clearHighlight);
  });
  function highlightColumn(index) {
    if (currentIndex === index) return;
    currentIndex = index;
    headers.forEach((h, i) => {
      h.classList.toggle('highlight-col', i === index);
      h.classList.toggle('dim-col', i !== index);
      const why = h.querySelector('.why-choose');
      if (why) { why.style.display = i === index ? 'block' : 'none'; }
    });
    const tableRows = document.querySelectorAll('tbody tr');
    tableRows.forEach((row) => {
      const cells = row.querySelectorAll('td');
      cells.forEach((cell, i) => {
        cell.classList.toggle('highlight-col', i === index);
        cell.classList.toggle('dim-col', i !== index);
      });
    });
  }
  function clearHighlight() {
    currentIndex = null;
    headers.forEach((h) => {
      h.classList.remove('highlight-col', 'dim-col');
      const why = h.querySelector('.why-choose');
      if (why) { why.style.display = 'none'; }
    });
    document.querySelectorAll('tbody td').forEach((cell) => {
      cell.classList.remove('highlight-col', 'dim-col');
    });
  }

  // Rotating image galleries per product (staggered delay)
  const galleries = document.querySelectorAll('.product-gallery');
  galleries.forEach((gal, idx) => {
    const imgs = gal.querySelectorAll('img');
    if (!imgs.length) return;
    let i = 0;
    imgs[0].classList.add('active');
    const delay = 3200 + (idx * 450);
    setInterval(() => {
      imgs[i].classList.remove('active');
      i = (i + 1) % imgs.length;
      imgs[i].classList.add('active');
    }, delay);
  });
});
</script>
</head>
<body>
<div class="dashboard">
  <div class="table-container">
    <table class="product-table">
      <thead>
        <tr>
          <th class="criteria-name">Criteria</th>

          <!-- WHOOP 4.0 -->
          <th class="product-header">
            <div class="product-header">
              <div class="product-gallery">
                <img src="https://picsum.photos/seed/whoop_4.0_2025/600/300" alt="WHOOP 4.0 - angle 1" class="active">
                <img src="https://picsum.photos/seed/whoop_4.0_2025b/600/300" alt="WHOOP 4.0 - angle 2">
                <img src="https://picsum.photos/seed/whoop_4.0_2025c/600/300" alt="WHOOP 4.0 - angle 3">
              </div>
              <div class="name"><a href="https://www.whoop.com/products/whoop-4-0" target="_blank" rel="noopener">WHOOP 4.0</a></div>
              <div class="usp">Data-driven recovery, sleep tracking, and strain scores.</div>
              <span class="price">$239 with subscription</span>
              <div class="rating">4.2/5</div>
              <div class="why-choose">Why choose this? Aimed at athletes, delivering comprehensive recovery and training insights with long battery life.</div>
            </div>
          </th>

          <!-- Garmin Index Sleep Monitor -->
          <th class="product-header">
            <div class="product-header">
              <div class="product-gallery">
                <img src="https://picsum.photos/seed/garmin_sleep_tracker_2024/600/300" alt="Garmin Index Sleep Monitor - angle 1" class="active">
                <img src="https://picsum.photos/seed/garmin_sleep_tracker_2024b/600/300" alt="Garmin Index Sleep Monitor - angle 2">
                <img src="https://picsum.photos/seed/garmin_sleep_tracker_2024c/600/300" alt="Garmin Index Sleep Monitor - angle 3">
              </div>
              <div class="name"><a href="https://www.garmin.com/index-sleep" target="_blank" rel="noopener">Garmin Index Sleep Monitor</a></div>
              <div class="usp">Sleep tracking and recovery insights.</div>
              <span class="price">$199</span>
              <div class="rating">3.9/5</div>
              <div class="why-choose">Why choose this? An affordable option with long battery life and decent sleep tracking for everyday health.</div>
            </div>
          </th>

          <!-- SomniBand Pro X -->
          <th class="product-header">
            <div class="product-header">
              <div class="product-gallery">
                <img src="https://picsum.photos/seed/somniband_prox_2025/600/300" alt="SomniBand Pro X - angle 1" class="active">
                <img src="https://picsum.photos/seed/somniband_prox_2025b/600/300" alt="SomniBand Pro X - angle 2">
                <img src="https://picsum.photos/seed/somniband_prox_2025c/600/300" alt="SomniBand Pro X - angle 3">
              </div>
              <div class="name"><a href="https://www.somniband.com/prox" target="_blank" rel="noopener">SomniBand Pro X</a></div>
              <div class="usp"><strong>EEG</strong>-based wearable delivering <strong>lab-grade</strong> sleep accuracy.</div>
              <span class="price">€299</span>
              <div class="rating">4.6/5</div>
              <div class="why-choose">Why choose this? Lab‑grade accuracy with EEG integration for those seeking the most precise sleep analysis.</div>
            </div>
          </th>

          <!-- LunaRing Edge -->
          <th class="product-header">
            <div class="product-header">
              <div class="product-gallery">
                <img src="https://picsum.photos/seed/lunaring_edge_2025/600/300" alt="LunaRing Edge - angle 1" class="active">
                <img src="https://picsum.photos/seed/lunaring_edge_2025b/600/300" alt="LunaRing Edge - angle 2">
                <img src="https://picsum.photos/seed/lunaring_edge_2025c/600/300" alt="LunaRing Edge - angle 3">
              </div>
              <div class="name"><a href="https://www.lunaring.com/edge" target="_blank" rel="noopener">LunaRing Edge</a></div>
              <div class="usp"><strong>Minimalist</strong> sleep tracker ring with actionable insights.</div>
              <span class="price">€249</span>
              <div class="rating">4.4/5</div>
              <div class="why-choose">Why choose this? A stylish ring that balances comfort with reliable sleep insights.</div>
            </div>
          </th>

          <!-- DreamPulse AI -->
          <th class="product-header">
            <div class="product-header">
              <div class="product-gallery">
                <img src="https://picsum.photos/seed/dreampulse_ai_2025/600/300" alt="DreamPulse AI - angle 1" class="active">
                <img src="https://picsum.photos/seed/dreampulse_ai_2025b/600/300" alt="DreamPulse AI - angle 2">
                <img src="https://picsum.photos/seed/dreampulse_ai_2025c/600/300" alt="DreamPulse AI - angle 3">
              </div>
              <div class="name"><a href="https://www.dreampulse.ai" target="_blank" rel="noopener">DreamPulse AI</a></div>
              <div class="usp">Tracks sleep without touching your body.</div>
              <span class="price">$179</span>
              <div class="rating">4.1/5</div>
              <div class="why-choose">Why choose this? A contactless tracker that monitors your sleep without wearing a device.</div>
            </div>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr class="group-heading"><th class="criteria-name" colspan="6">Sleep Insights</th></tr>

        <tr>
          <th class="criteria-name">Sleep Accuracy</th>
          <td class="criteria-cell">Moderate</td>
          <td class="criteria-cell">Lower than leading competitors</td>
          <td class="criteria-cell best"><span class="winner-indicator" aria-hidden="true"></span><strong>High</strong> with <strong>EEG</strong> integration</td>
          <td class="criteria-cell">Good with PPG and temperature tracking</td>
          <td class="criteria-cell">Moderate with <strong>AI</strong> correction</td>
        </tr>

        <tr>
          <th class="criteria-name">Disturbance Detection</th>
          <td class="criteria-cell">Basic motion-based detection</td>
          <td class="criteria-cell">Breathing disturbance alerts (not medical-grade)</td>
          <td class="criteria-cell best"><span class="winner-indicator" aria-hidden="true"></span><strong>Advanced</strong> motion and heart rate anomalies</td>
          <td class="criteria-cell">Subtle movement and temp spikes</td>
          <td class="criteria-cell">Snore and motion alerts</td>
        </tr>

        <tr>
          <th class="criteria-name">How well it guides you</th>
          <td class="criteria-cell best"><span class="winner-indicator" aria-hidden="true"></span><strong>Comprehensive</strong> daily recovery score based on HRV, sleep, and strain</td>
          <td class="criteria-cell">Daily body battery score integrating sleep and stress</td>
          <td class="criteria-cell">Morning readiness score with lifestyle tips</td>
          <td class="criteria-cell">Tailored training and rest advice</td>
          <td class="criteria-cell"><strong>AI</strong>-driven stress and recovery balance</td>
        </tr>

        <tr class="group-heading"><th class="criteria-name" colspan="6">Comfort &amp; Fit</th></tr>

        <tr>
          <th class="criteria-name">Comfort &amp; Fit</th>
          <td class="criteria-cell">Lightweight strap with soft fabric band</td>
          <td class="criteria-cell">Slim wearable with adjustable band</td>
          <td class="criteria-cell"><strong>Ultra</strong>-thin headband design</td>
          <td class="criteria-cell"><strong>Light</strong> titanium ring</td>
          <td class="criteria-cell best"><span class="winner-indicator" aria-hidden="true"></span><strong>Pillow</strong> insert with no wearables</td>
        </tr>

        <tr>
          <th class="criteria-name">Who it's for</th>
          <td class="criteria-cell">Athlete</td>
          <td class="criteria-cell">Athlete</td>
          <td class="criteria-cell">Sleep optimization</td>
          <td class="criteria-cell">Daily health monitoring</td>
          <td class="criteria-cell">Contactless sleep tracking</td>
        </tr>

        <tr class="group-heading"><th class="criteria-name" colspan="6">Battery &amp; Price</th></tr>

        <tr>
          <th class="criteria-name">Days without charging</th>
          <td class="criteria-cell">
            <div class="battery-cell">
              <span class="battery-days">4–5 d</span>
              <div class="battery-bar"><div class="bar" style="width:64.3%;"></div></div>
            </div>
          </td>
          <td class="criteria-cell best">
            <span class="winner-indicator" aria-hidden="true"></span>
            <div class="battery-cell">
              <span class="battery-days">7 d</span>
              <div class="battery-bar"><div class="bar" style="width:100%;"></div></div>
            </div>
          </td>
          <td class="criteria-cell">
            <div class="battery-cell">
              <span class="battery-days">3 d</span>
              <div class="battery-bar"><div class="bar" style="width:42.9%;"></div></div>
            </div>
          </td>
          <td class="criteria-cell">
            <div class="battery-cell">
              <span class="battery-days">5 d</span>
              <div class="battery-bar"><div class="bar" style="width:71.4%;"></div></div>
            </div>
          </td>
          <td class="criteria-cell best">
            <span class="winner-indicator" aria-hidden="true"></span>
            <div class="battery-cell">
              <span class="battery-days">7 n</span>
              <div class="battery-bar"><div class="bar" style="width:100%;"></div></div>
            </div>
          </td>
        </tr>

        <tr>
          <th class="criteria-name">Price</th>
          <td class="criteria-cell">$239 with subscription</td>
          <td class="criteria-cell">$199</td>
          <td class="criteria-cell">€299</td>
          <td class="criteria-cell">€249</td>
          <td class="criteria-cell best"><span class="winner-indicator" aria-hidden="true"></span>$179</td>
        </tr>

        <tr>
          <th class="criteria-name">User Reviews</th>
          <td class="criteria-cell">3,200</td>
          <td class="criteria-cell">1,850</td>
          <td class="criteria-cell">540</td>
          <td class="criteria-cell">1,200</td>
          <td class="criteria-cell">780</td>
        </tr>

        <tr class="group-heading"><th class="criteria-name" colspan="6">Brand &amp; Features</th></tr>

        <tr>
          <th class="criteria-name">Trusted Brand?</th>
          <td class="criteria-cell best"><span class="winner-indicator" aria-hidden="true"></span><strong>Strong</strong> among athletes, but mixed reviews on accuracy</td>
          <td class="criteria-cell">Respected in sports tech, but sleep accuracy questioned</td>
          <td class="criteria-cell best"><span class="winner-indicator" aria-hidden="true"></span>Emerging European startup with <strong>strong</strong> early reviews</td>
          <td class="criteria-cell best"><span class="winner-indicator" aria-hidden="true"></span><strong>Well-regarded</strong> in European biohacking community</td>
          <td class="criteria-cell best"><span class="winner-indicator" aria-hidden="true"></span><strong>Newcomer</strong> with <strong>strong</strong> Kickstarter backing</td>
        </tr>

        <tr>
          <th class="criteria-name">Key Features</th>
          <td class="criteria-cell">recovery insights, comfortable, long battery life</td>
          <td class="criteria-cell">inaccurate sleep stage detection, comfortable, long battery life, recovery insights</td>
          <td class="criteria-cell">precise sleep stage data, innovative headband design, helpful morning insights</td>
          <td class="criteria-cell"><strong>stylish</strong> ring, <strong>discreet</strong>, good balance of accuracy and comfort</td>
          <td class="criteria-cell"><strong>non-wearable</strong>, <strong>AI</strong>-enhanced, unique <strong>pillow</strong>-based tracking</td>
        </tr>
      </tbody>
    </table>
  </div>
</div>

<script>
document.addEventListener('DOMContentLoaded', function () {
  const EXP = {
    "Sleep Accuracy": {
      how: "Agreement with gold-standard polysomnography/EEG; stability across nights.",
      judge: "Independent validations, sensor fusion clarity (PPG+EEG/Temp), consistent scoring.",
      watch: "Bold marketing claims without validation; big changes after firmware updates."
    },
    "Disturbance Detection": {
      how: "Ability to catch awakenings, snoring, movement, breathing irregularities.",
      judge: "Time-stamped events, multi-sensor corroboration, low false positives.",
      watch: "Motion-only systems over-report; contactless can miss micro‑arousals."
    },
    "How well it guides you": {
      how: "Quality of readiness/coaching and whether it explains 'why'.",
      judge: "Actionable, personalized, avoids generic tips; links metrics to behavior.",
      watch: "Over-coaching fatigue; opaque scores you can't audit."
    },
    "Comfort & Fit": {
      how: "Does it disappear on-body across sleep positions and skin types?",
      judge: "Hours of wear, materials, pressure points, sweat/skin reactions.",
      watch: "Headband pressure, ring sizing, fabric irritation."
    },
    "Days without charging": {
      how: "Real-world battery life with mixed use, not lab maximums.",
      judge: "Always-on sensors + workouts; degradation after 6–12 months.",
      watch: "Advertised 'up to' vs typical; fast drains with SpO2/HRV."
    },
    "Price": {
      how: "Total cost of ownership (device + subscription + accessories).",
      judge: "Value vs accuracy/insights; transparent cancellation policies.",
      watch: "Features behind paywalls; annual-only plans."
    },
    "User Reviews": {
      how: "Volume, recency, and verified users across platforms.",
      judge: "Consistent patterns (sleep accuracy, comfort) over isolated anecdotes.",
      watch: "Review stuffing; updates that change behavior post‑review."
    },
    "Trusted Brand?": {
      how: "Track record in wearables, privacy, firmware cadence, support.",
      judge: "Clear privacy policy, export options, long-term device support.",
      watch: "Data resale/advertising; abandoned models."
    },
    "Key Features": {
      how: "Differentiators that impact sleep outcomes, not buzzwords.",
      judge: "Evidence of benefit; fewer, stronger features beat long lists.",
      watch: "Hype terms (AI, biohacking) without measurable effect."
    },
    "Who it's for": {
      how: "Primary user fit by lifestyle and goals.",
      judge: "Use-case alignment (athlete, casual, sleep clinic needs).",
      watch: "One-size-fits-all claims."
    }
  };

  const isComplex = (txt, html, critName) => {
    if (!txt) return false;
    const long = txt.trim().length > 24;
    const hasComma = /,/.test(txt);
    const rich = /<strong>|<\/strong>|<em>|<\/em>/i.test(html);
    const buzz = /(score|readiness|HRV|EEG|PPG|AI|accuracy|detection|insights)/i.test(txt);
    const flagged = !!EXP[critName]; // always complex for mapped criteria
    return flagged || long || hasComma || rich || buzz;
  };

  // Create a single tooltip element reused for all hovers
  const tip = document.createElement('div');
  tip.className = 'hover-tip';
  document.body.appendChild(tip);

  let hoverTimer = null;

  const showTip = (content, x, y) => {
    tip.innerHTML = content;
    tip.style.top = Math.max(12, y + 12) + 'px';
    tip.style.left = Math.max(12, x + 12) + 'px';
    tip.classList.add('show');
  };
  const hideTip = () => {
    tip.classList.remove('show');
  };

  // Attach to all body rows
  document.querySelectorAll('tbody tr').forEach((row) => {
    const th = row.querySelector('th.criteria-name');
    if (!th) return;
    const critName = th.textContent.trim();

    row.querySelectorAll('td.criteria-cell, td.best').forEach((cell) => {
      const rawHTML = cell.innerHTML;
      const rawText = cell.textContent.trim();
      if (!isComplex(rawText, rawHTML, critName)) return;

      // Wrap visible content for subtle clamp
      if (!cell.querySelector('.cell-inner')) {
        const wrapper = document.createElement('div');
        wrapper.className = 'cell-inner';
        wrapper.innerHTML = rawHTML;
        cell.innerHTML = '';
        cell.appendChild(wrapper);
      }

      const isBest = cell.classList.contains('best');

      const exp = EXP[critName] || {};
      const content = `
        <div class="tip-title">${critName}${isBest ? '<span class="best-badge">Best in row</span>' : ''}</div>
        ${exp.how ? `<div class="meta">${exp.how}</div>` : ''}
        <div class="section"><strong>This product here:</strong> ${rawText}</div>
        ${exp.judge ? `<div class="section"><strong>How we judge it:</strong> ${exp.judge}</div>` : ''}
        ${exp.watch ? `<div class="section"><strong>Watch out for:</strong> ${exp.watch}</div>` : ''}
      `;

      // Delay show to avoid flicker (700ms)
      cell.addEventListener('mouseenter', (e) => {
        const ev = e;
        hoverTimer = setTimeout(() => {
          showTip(content, ev.clientX, ev.clientY);
        }, 700);
      });
      cell.addEventListener('mousemove', (e) => {
        if (tip.classList.contains('show')) {
          tip.style.top = Math.max(12, e.clientY + 12) + 'px';
          tip.style.left = Math.max(12, e.clientX + 12) + 'px';
        }
      });
      ['mouseleave', 'blur'].forEach(evt => {
        cell.addEventListener(evt, () => {
          clearTimeout(hoverTimer);
          hideTip();
        });
      });

      // Touch support: tap to toggle
      cell.addEventListener('touchstart', (e) => {
        e.preventDefault();
        if (tip.classList.contains('show')) { hideTip(); return; }
        const touch = e.touches[0];
        showTip(content, touch.clientX, touch.clientY);
      }, {passive: false});
    });
  });
});
</script>

</body>
</html>



</HTML_example>

<HTML_templated>

<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>&lt;Page_Title&gt;</title>
<style>
  :root {
    --bg: #f6f6f7;
    --card: #ffffff;
    --text: #1c1c1e;
    --muted: #666;
    --accent: #007aff;
    --hover: #f3f6ff;
    --col-hover: #fffbea;
    --col-ring: #ffd54f;
  }
  body { font-family: system-ui, -apple-system, "Segoe UI", sans-serif; background-color: var(--bg); margin: 0; padding: 24px; color: var(--text); }
  .dashboard { max-width: 1200px; margin: 0 auto; }
  .table-container { overflow-x: auto; border-radius: 16px; box-shadow: 0 10px 30px rgba(0,0,0,0.04); background-color: var(--card); }
  table { border-collapse: collapse; width: 100%; min-width: 900px; background: var(--card); }
  /* Cells: more vertical padding, a bit more horizontal; no borders */
  th, td { border: 0; text-align: left; vertical-align: top; padding: 24px 18px; font-size: 0.95rem; background: var(--card); }
  /* Sticky areas keep the same background to match the request */
  thead th.product-header { width: 200px; max-width: 200px; min-width: 200px; position: sticky; top: 0; z-index: 2; background-color: var(--card); }
  tbody th.criteria-name { position: sticky; left: 0; background-color: var(--card); font-weight: 600; z-index: 1; }
  th.criteria-name { width: 240px; max-width: 260px; }

  .product-header .name a { color: var(--accent); text-decoration: none; font-weight: 600; }
  .product-header .name a:hover { text-decoration: underline; }
  .product-header .usp { font-style: italic; font-size: 0.85rem; color: var(--muted); margin-bottom: 8px; }
  .product-header .price { font-family: ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace; font-size: 1.05rem; color: #00a862; font-weight: 700; }
  .product-header .rating { font-size: 0.9rem; color: #555; margin-top: 4px; }
  .product-header .why-choose {
    display: none;
    position: absolute; bottom: 12px; left: 12px; right: 12px;
    background-color: rgba(255,255,255,0.95);
    border-radius: 10px; padding: 8px 10px; font-size: 0.8rem; color: var(--text);
    box-shadow: 0 6px 16px rgba(0,0,0,0.08);
    line-height: 1.35;
  }

  /* Winner indicator (no emojis) — appears only on row hover */
  .winner-indicator {
    display: inline-block; width: 10px; height: 10px; transform: rotate(45deg);
    border: 1.5px solid var(--text); border-radius: 2px; margin-right: 8px; opacity: 0; transition: opacity .25s ease;
  }
  tbody tr:hover td.best .winner-indicator { opacity: 1; }
  tbody tr:hover td.best {
    background: #fff6e5;
    box-shadow: inset 0 0 0 2px #f0c76b;
    font-weight: 600;
  }

  /* Subtle motion + hover highlight */
  tbody tr { transition: transform 0.25s ease, background-color 0.2s ease; }
  tbody tr:hover { transform: translateX(4px); }
  tbody tr:hover td { background-color: var(--hover); }
  tbody td:hover { background-color: #eaf2ff; }

  /* Column highlight w/ unified background by default */
  td.highlight-col, th.product-header.highlight-col { background-color: var(--col-hover) !important; box-shadow: inset 0 0 0 2px var(--col-ring); }
  td.dim-col, th.product-header.dim-col { opacity: 0.45; }

  /* Minimal group headings (no borders) */
  .group-heading th { background-color: var(--bg); font-size: 0.95rem; font-weight: 700; padding-top: 18px; padding-bottom: 8px; border: 0; }

  /* Product image gallery (rotating) */
  .product-header { position: relative; }
  .product-gallery { position: relative; width: 100%; height: 220px; border-radius: 12px; overflow: hidden; background: #fafafa; margin-bottom: 10px; }
  .product-gallery img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; opacity: 0; transition: opacity 0.6s ease; }
  .product-gallery img.active { opacity: 1; }

  /* Battery visualization */
  .battery-cell { display: flex; align-items: center; gap: 8px; }
  .battery-cell .battery-days { font-weight: 600; }
  .battery-cell .battery-bar { flex-grow: 1; height: 8px; background-color: #e6e6e6; border-radius: 4px; position: relative; overflow: hidden; }
  .battery-cell .battery-bar .bar { height: 100%; background-color: #00a862; border-radius: 4px; transition: width 0.3s ease; }

  /* --- Hover tooltip for complex criteria --- */
  .cell-inner {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .hover-tip {
    position: fixed;
    z-index: 9999;
    background: #ffffff;
    color: var(--text);
    border-radius: 12px;
    padding: 12px 14px;
    max-width: 360px;
    box-shadow: 0 12px 32px rgba(0,0,0,0.12);
    border: 1px solid rgba(0,0,0,0.06);
    opacity: 0;
    transform: translateY(4px);
    pointer-events: none;
    transition: opacity .15s ease, transform .15s ease;
    line-height: 1.35;
  }
  .hover-tip.show { opacity: 1; transform: translateY(0); }
  .hover-tip .tip-title { font-weight: 700; margin-bottom: 6px; }
  .hover-tip .meta { color: var(--muted); font-size: 0.78rem; margin-bottom: 6px; }
  .hover-tip .best-badge {
    display: inline-block; margin-left: 6px; padding: 2px 8px; border-radius: 999px;
    background: #fff6e5; border: 1px solid #f0c76b; font-size: 0.72rem;
  }
  .hover-tip .section { margin-top: 6px; font-size: 0.86rem; }
  .hover-tip .section strong { font-weight: 700; }

</style>
<script>
document.addEventListener('DOMContentLoaded', function() {
  // Column highlight interactions
  const headers = document.querySelectorAll('th.product-header');
  let currentIndex = null;
  headers.forEach((header, index) => {
    header.dataset.index = index;
    header.addEventListener('mouseenter', () => highlightColumn(index));
    header.addEventListener('mouseleave', clearHighlight);
  });
  function highlightColumn(index) {
    if (currentIndex === index) return;
    currentIndex = index;
    headers.forEach((h, i) => {
      h.classList.toggle('highlight-col', i === index);
      h.classList.toggle('dim-col', i !== index);
      const why = h.querySelector('.why-choose');
      if (why) { why.style.display = i === index ? 'block' : 'none'; }
    });
    const tableRows = document.querySelectorAll('tbody tr');
    tableRows.forEach((row) => {
      const cells = row.querySelectorAll('td');
      cells.forEach((cell, i) => {
        cell.classList.toggle('highlight-col', i === index);
        cell.classList.toggle('dim-col', i !== index);
      });
    });
  }
  function clearHighlight() {
    currentIndex = null;
    headers.forEach((h) => {
      h.classList.remove('highlight-col', 'dim-col');
      const why = h.querySelector('.why-choose');
      if (why) { why.style.display = 'none'; }
    });
    document.querySelectorAll('tbody td').forEach((cell) => {
      cell.classList.remove('highlight-col', 'dim-col');
    });
  }

  // Rotating image galleries per product (staggered delay)
  const galleries = document.querySelectorAll('.product-gallery');
  galleries.forEach((gal, idx) => {
    const imgs = gal.querySelectorAll('img');
    if (!imgs.length) return;
    let i = 0;
    imgs[0].classList.add('active');
    const delay = 3200 + (idx * 450);
    setInterval(() => {
      imgs[i].classList.remove('active');
      i = (i + 1) % imgs.length;
      imgs[i].classList.add('active');
    }, delay);
  });
});
</script>
</head>
<body>
<div class="dashboard">
  <div class="table-container">
    <table class="product-table">
      <thead>
        <tr>
          <th class="criteria-name">&lt;Criteria_Header_Label&gt;</th>

          <!-- Product 1 -->
          <th class="product-header">
            <div class="product-header">
              <div class="product-gallery">
                <img src="&lt;Product_1_Image_URL_1&gt;" alt="&lt;Product_1_Name&gt; - &lt;Image_Angle_1&gt;" class="active">
                <img src="&lt;Product_1_Image_URL_2&gt;" alt="&lt;Product_1_Name&gt; - &lt;Image_Angle_2&gt;">
                <img src="&lt;Product_1_Image_URL_3&gt;" alt="&lt;Product_1_Name&gt; - &lt;Image_Angle_3&gt;">
              </div>
              <div class="name"><a href="&lt;Product_1_URL&gt;" target="_blank" rel="noopener">&lt;Product_1_Name&gt;</a></div>
              <div class="usp">&lt;Product_1_USP&gt;</div>
              <span class="price">&lt;Product_1_Price&gt;</span>
              <div class="rating">&lt;Product_1_Rating&gt;</div>
              <div class="why-choose">&lt;Product_1_Why_Choose&gt;</div>
            </div>
          </th>

          <!-- Product 2 -->
          <th class="product-header">
            <div class="product-header">
              <div class="product-gallery">
                <img src="&lt;Product_2_Image_URL_1&gt;" alt="&lt;Product_2_Name&gt; - &lt;Image_Angle_1&gt;" class="active">
                <img src="&lt;Product_2_Image_URL_2&gt;" alt="&lt;Product_2_Name&gt; - &lt;Image_Angle_2&gt;">
                <img src="&lt;Product_2_Image_URL_3&gt;" alt="&lt;Product_2_Name&gt; - &lt;Image_Angle_3&gt;">
              </div>
              <div class="name"><a href="&lt;Product_2_URL&gt;" target="_blank" rel="noopener">&lt;Product_2_Name&gt;</a></div>
              <div class="usp">&lt;Product_2_USP&gt;</div>
              <span class="price">&lt;Product_2_Price&gt;</span>
              <div class="rating">&lt;Product_2_Rating&gt;</div>
              <div class="why-choose">&lt;Product_2_Why_Choose&gt;</div>
            </div>
          </th>

          <!-- Product 3 -->
          <th class="product-header">
            <div class="product-header">
              <div class="product-gallery">
                <img src="&lt;Product_3_Image_URL_1&gt;" alt="&lt;Product_3_Name&gt; - &lt;Image_Angle_1&gt;" class="active">
                <img src="&lt;Product_3_Image_URL_2&gt;" alt="&lt;Product_3_Name&gt; - &lt;Image_Angle_2&gt;">
                <img src="&lt;Product_3_Image_URL_3&gt;" alt="&lt;Product_3_Name&gt; - &lt;Image_Angle_3&gt;">
              </div>
              <div class="name"><a href="&lt;Product_3_URL&gt;" target="_blank" rel="noopener">&lt;Product_3_Name&gt;</a></div>
              <div class="usp">&lt;Product_3_USP&gt;</div>
              <span class="price">&lt;Product_3_Price&gt;</span>
              <div class="rating">&lt;Product_3_Rating&gt;</div>
              <div class="why-choose">&lt;Product_3_Why_Choose&gt;</div>
            </div>
          </th>

          <!-- Product 4 -->
          <th class="product-header">
            <div class="product-header">
              <div class="product-gallery">
                <img src="&lt;Product_4_Image_URL_1&gt;" alt="&lt;Product_4_Name&gt; - &lt;Image_Angle_1&gt;" class="active">
                <img src="&lt;Product_4_Image_URL_2&gt;" alt="&lt;Product_4_Name&gt; - &lt;Image_Angle_2&gt;">
                <img src="&lt;Product_4_Image_URL_3&gt;" alt="&lt;Product_4_Name&gt; - &lt;Image_Angle_3&gt;">
              </div>
              <div class="name"><a href="&lt;Product_4_URL&gt;" target="_blank" rel="noopener">&lt;Product_4_Name&gt;</a></div>
              <div class="usp">&lt;Product_4_USP&gt;</div>
              <span class="price">&lt;Product_4_Price&gt;</span>
              <div class="rating">&lt;Product_4_Rating&gt;</div>
              <div class="why-choose">&lt;Product_4_Why_Choose&gt;</div>
            </div>
          </th>

          <!-- Product 5 -->
          <th class="product-header">
            <div class="product-header">
              <div class="product-gallery">
                <img src="&lt;Product_5_Image_URL_1&gt;" alt="&lt;Product_5_Name&gt; - &lt;Image_Angle_1&gt;" class="active">
                <img src="&lt;Product_5_Image_URL_2&gt;" alt="&lt;Product_5_Name&gt; - &lt;Image_Angle_2&gt;">
                <img src="&lt;Product_5_Image_URL_3&gt;" alt="&lt;Product_5_Name&gt; - &lt;Image_Angle_3&gt;">
              </div>
              <div class="name"><a href="&lt;Product_5_URL&gt;" target="_blank" rel="noopener">&lt;Product_5_Name&gt;</a></div>
              <div class="usp">&lt;Product_5_USP&gt;</div>
              <span class="price">&lt;Product_5_Price&gt;</span>
              <div class="rating">&lt;Product_5_Rating&gt;</div>
              <div class="why-choose">&lt;Product_5_Why_Choose&gt;</div>
            </div>
          </th>
        </tr>
      </thead>

      <tbody>
        <tr class="group-heading"><th class="criteria-name" colspan="6">&lt;Group_1_Title&gt;</th></tr>

        <tr>
          <th class="criteria-name">&lt;Criteria_1_Name&gt;</th>
          <td class="criteria-cell">&lt;Criteria_1_Value_Product_1&gt;</td>
          <td class="criteria-cell">&lt;Criteria_1_Value_Product_2&gt;</td>
          <td class="criteria-cell best"><span class="winner-indicator" aria-hidden="true"></span>&lt;Criteria_1_Value_Product_3&gt;</td>
          <td class="criteria-cell">&lt;Criteria_1_Value_Product_4&gt;</td>
          <td class="criteria-cell">&lt;Criteria_1_Value_Product_5&gt;</td>
        </tr>

        <tr>
          <th class="criteria-name">&lt;Criteria_2_Name&gt;</th>
          <td class="criteria-cell">&lt;Criteria_2_Value_Product_1&gt;</td>
          <td class="criteria-cell">&lt;Criteria_2_Value_Product_2&gt;</td>
          <td class="criteria-cell best"><span class="winner-indicator" aria-hidden="true"></span>&lt;Criteria_2_Value_Product_3&gt;</td>
          <td class="criteria-cell">&lt;Criteria_2_Value_Product_4&gt;</td>
          <td class="criteria-cell">&lt;Criteria_2_Value_Product_5&gt;</td>
        </tr>

        <tr>
          <th class="criteria-name">&lt;Criteria_3_Name&gt;</th>
          <td class="criteria-cell best"><span class="winner-indicator" aria-hidden="true"></span>&lt;Criteria_3_Value_Product_1&gt;</td>
          <td class="criteria-cell">&lt;Criteria_3_Value_Product_2&gt;</td>
          <td class="criteria-cell">&lt;Criteria_3_Value_Product_3&gt;</td>
          <td class="criteria-cell">&lt;Criteria_3_Value_Product_4&gt;</td>
          <td class="criteria-cell">&lt;Criteria_3_Value_Product_5&gt;</td>
        </tr>

        <tr class="group-heading"><th class="criteria-name" colspan="6">&lt;Group_2_Title&gt;</th></tr>

        <tr>
          <th class="criteria-name">&lt;Criteria_4_Name&gt;</th>
          <td class="criteria-cell">&lt;Criteria_4_Value_Product_1&gt;</td>
          <td class="criteria-cell">&lt;Criteria_4_Value_Product_2&gt;</td>
          <td class="criteria-cell">&lt;Criteria_4_Value_Product_3&gt;</td>
          <td class="criteria-cell">&lt;Criteria_4_Value_Product_4&gt;</td>
          <td class="criteria-cell best"><span class="winner-indicator" aria-hidden="true"></span>&lt;Criteria_4_Value_Product_5&gt;</td>
        </tr>

        <tr>
          <th class="criteria-name">&lt;Criteria_5_Name&gt;</th>
          <td class="criteria-cell">&lt;Criteria_5_Value_Product_1&gt;</td>
          <td class="criteria-cell">&lt;Criteria_5_Value_Product_2&gt;</td>
          <td class="criteria-cell">&lt;Criteria_5_Value_Product_3&gt;</td>
          <td class="criteria-cell">&lt;Criteria_5_Value_Product_4&gt;</td>
          <td class="criteria-cell">&lt;Criteria_5_Value_Product_5&gt;</td>
        </tr>

        <tr class="group-heading"><th class="criteria-name" colspan="6">&lt;Group_3_Title&gt;</th></tr>

        <tr>
          <th class="criteria-name">&lt;Battery_Criteria_Name&gt;</th>
          <td class="criteria-cell">
            <div class="battery-cell">
              <span class="battery-days">&lt;Battery_Days_Product_1&gt;</span>
              <div class="battery-bar"><div class="bar" style="width:&lt;Battery_Percent_Product_1&gt;%;"></div></div>
            </div>
          </td>
          <td class="criteria-cell best">
            <span class="winner-indicator" aria-hidden="true"></span>
            <div class="battery-cell">
              <span class="battery-days">&lt;Battery_Days_Product_2&gt;</span>
              <div class="battery-bar"><div class="bar" style="width:&lt;Battery_Percent_Product_2&gt;%;"></div></div>
            </div>
          </td>
          <td class="criteria-cell">
            <div class="battery-cell">
              <span class="battery-days">&lt;Battery_Days_Product_3&gt;</span>
              <div class="battery-bar"><div class="bar" style="width:&lt;Battery_Percent_Product_3&gt;%;"></div></div>
            </div>
          </td>
          <td class="criteria-cell">
            <div class="battery-cell">
              <span class="battery-days">&lt;Battery_Days_Product_4&gt;</span>
              <div class="battery-bar"><div class="bar" style="width:&lt;Battery_Percent_Product_4&gt;%;"></div></div>
            </div>
          </td>
          <td class="criteria-cell">
            <div class="battery-cell">
              <span class="battery-days">&lt;Battery_Days_Product_5&gt;</span>
              <div class="battery-bar"><div class="bar" style="width:&lt;Battery_Percent_Product_5&gt;%;"></div></div>
            </div>
          </td>
        </tr>

        <tr>
          <th class="criteria-name">&lt;Price_Criteria_Name&gt;</th>
          <td class="criteria-cell">&lt;Product_1_Price&gt;</td>
          <td class="criteria-cell">&lt;Product_2_Price&gt;</td>
          <td class="criteria-cell">&lt;Product_3_Price&gt;</td>
          <td class="criteria-cell">&lt;Product_4_Price&gt;</td>
          <td class="criteria-cell best"><span class="winner-indicator" aria-hidden="true"></span>&lt;Product_5_Price&gt;</td>
        </tr>

        <tr>
          <th class="criteria-name">&lt;Reviews_Count_Criteria_Name&gt;</th>
          <td class="criteria-cell">&lt;Product_1_Reviews_Count&gt;</td>
          <td class="criteria-cell">&lt;Product_2_Reviews_Count&gt;</td>
          <td class="criteria-cell">&lt;Product_3_Reviews_Count&gt;</td>
          <td class="criteria-cell">&lt;Product_4_Reviews_Count&gt;</td>
          <td class="criteria-cell">&lt;Product_5_Reviews_Count&gt;</td>
        </tr>

        <tr class="group-heading"><th class="criteria-name" colspan="6">&lt;Group_4_Title&gt;</th></tr>

        <tr>
          <th class="criteria-name">&lt;Brand_Trust_Criteria_Name&gt;</th>
          <td class="criteria-cell">&lt;Product_1_Brand_Trust_Text&gt;</td>
          <td class="criteria-cell">&lt;Product_2_Brand_Trust_Text&gt;</td>
          <td class="criteria-cell">&lt;Product_3_Brand_Trust_Text&gt;</td>
          <td class="criteria-cell">&lt;Product_4_Brand_Trust_Text&gt;</td>
          <td class="criteria-cell">&lt;Product_5_Brand_Trust_Text&gt;</td>
        </tr>

        <tr>
          <th class="criteria-name">&lt;Key_Features_Criteria_Name&gt;</th>
          <td class="criteria-cell">&lt;Product_1_Key_Features&gt;</td>
          <td class="criteria-cell">&lt;Product_2_Key_Features&gt;</td>
          <td class="criteria-cell">&lt;Product_3_Key_Features&gt;</td>
          <td class="criteria-cell">&lt;Product_4_Key_Features&gt;</td>
          <td class="criteria-cell">&lt;Product_5_Key_Features&gt;</td>
        </tr>
      </tbody>
    </table>
  </div>
</div>

<script>
document.addEventListener('DOMContentLoaded', function () {
  // Generic EXP map using placeholder criteria names. Replace values or extend as needed.
  const EXP = {
    "<Criteria_1_Name>": {
      how: "&lt;Criteria_1_How_To_Assess&gt;",
      judge: "&lt;Criteria_1_How_To_Judge&gt;",
      watch: "&lt;Criteria_1_Watchouts&gt;"
    },
    "<Criteria_2_Name>": {
      how: "&lt;Criteria_2_How_To_Assess&gt;",
      judge: "&lt;Criteria_2_How_To_Judge&gt;",
      watch: "&lt;Criteria_2_Watchouts&gt;"
    },
    "<Criteria_3_Name>": {
      how: "&lt;Criteria_3_How_To_Assess&gt;",
      judge: "&lt;Criteria_3_How_To_Judge&gt;",
      watch: "&lt;Criteria_3_Watchouts&gt;"
    },
    "<Battery_Criteria_Name>": {
      how: "&lt;Battery_How_To_Assess&gt;",
      judge: "&lt;Battery_How_To_Judge&gt;",
      watch: "&lt;Battery_Watchouts&gt;"
    },
    "<Price_Criteria_Name>": {
      how: "&lt;Price_How_To_Assess&gt;",
      judge: "&lt;Price_How_To_Judge&gt;",
      watch: "&lt;Price_Watchouts&gt;"
    },
    "<Reviews_Count_Criteria_Name>": {
      how: "&lt;Reviews_How_To_Assess&gt;",
      judge: "&lt;Reviews_How_To_Judge&gt;",
      watch: "&lt;Reviews_Watchouts&gt;"
    },
    "<Brand_Trust_Criteria_Name>": {
      how: "&lt;Brand_Trust_How_To_Assess&gt;",
      judge: "&lt;Brand_Trust_How_To_Judge&gt;",
      watch: "&lt;Brand_Trust_Watchouts&gt;"
    },
    "<Key_Features_Criteria_Name>": {
      how: "&lt;Key_Features_How_To_Assess&gt;",
      judge: "&lt;Key_Features_How_To_Judge&gt;",
      watch: "&lt;Key_Features_Watchouts&gt;"
    }
  };

  const isComplex = (txt, html, critName) => {
    if (!txt) return false;
    const long = txt.trim().length > 24;
    const hasComma = /,/.test(txt);
    const rich = /<strong>|<\/strong>|<em>|<\/em>/i.test(html);
    const buzz = /(score|readiness|hrv|eeg|ppg|ai|accuracy|detection|insights|battery|price|reviews|brand)/i.test(txt);
    const flagged = !!EXP[critName];
    return flagged || long || hasComma || rich || buzz;
  };

  // Create a single tooltip element reused for all hovers
  const tip = document.createElement('div');
  tip.className = 'hover-tip';
  document.body.appendChild(tip);

  let hoverTimer = null;

  const showTip = (content, x, y) => {
    tip.innerHTML = content;
    tip.style.top = Math.max(12, y + 12) + 'px';
    tip.style.left = Math.max(12, x + 12) + 'px';
    tip.classList.add('show');
  };
  const hideTip = () => {
    tip.classList.remove('show');
  };

  // Attach to all body rows
  document.querySelectorAll('tbody tr').forEach((row) => {
    const th = row.querySelector('th.criteria-name');
    if (!th) return;
    const critName = th.textContent.trim();

    row.querySelectorAll('td.criteria-cell, td.best').forEach((cell) => {
      const rawHTML = cell.innerHTML;
      const rawText = cell.textContent.trim();
      if (!isComplex(rawText, rawHTML, critName)) return;

      // Wrap visible content for subtle clamp
      if (!cell.querySelector('.cell-inner')) {
        const wrapper = document.createElement('div');
        wrapper.className = 'cell-inner';
        wrapper.innerHTML = rawHTML;
        cell.innerHTML = '';
        cell.appendChild(wrapper);
      }

      const isBest = cell.classList.contains('best');

      const exp = EXP[critName] || {};
      const content = `
        <div class="tip-title">${critName}${isBest ? '<span class="best-badge">&lt;Best_In_Row_Label&gt;</span>' : ''}</div>
        ${exp.how ? `<div class="meta">${exp.how}</div>` : ''}
        <div class="section"><strong>&lt;This_Product_Label&gt;:</strong> ${rawText}</div>
        ${exp.judge ? `<div class="section"><strong>&lt;How_We_Judge_Label&gt;:</strong> ${exp.judge}</div>` : ''}
        ${exp.watch ? `<div class="section"><strong>&lt;Watch_Out_For_Label&gt;:</strong> ${exp.watch}</div>` : ''}
      `;

      // Delay show to avoid flicker (700ms)
      cell.addEventListener('mouseenter', (e) => {
        const ev = e;
        hoverTimer = setTimeout(() => {
          showTip(content, ev.clientX, ev.clientY);
        }, 700);
      });
      cell.addEventListener('mousemove', (e) => {
        if (tip.classList.contains('show')) {
          tip.style.top = Math.max(12, e.clientY + 12) + 'px';
          tip.style.left = Math.max(12, e.clientX + 12) + 'px';
        }
      });
      ['mouseleave', 'blur'].forEach(evt => {
        cell.addEventListener(evt, () => {
          clearTimeout(hoverTimer);
          hideTip();
        });
      });

      // Touch support: tap to toggle
      cell.addEventListener('touchstart', (e) => {
        e.preventDefault();
        if (tip.classList.contains('show')) { hideTip(); return; }
        const touch = e.touches[0];
        showTip(content, touch.clientX, touch.clientY);
      }, {passive: false});
    });
  });
});
</script>

</body>
</html>

</HTML_templated>
"""