from __future__ import annotations


def render_index() -> str:
    return """<!doctype html>
<html lang="cs">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Multi-Agent UGC Generator</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #07090f;
      --panel: rgba(18, 22, 32, .88);
      --panel-strong: #111827;
      --panel-soft: rgba(255, 255, 255, .045);
      --ink: #f4f7fb;
      --muted: #93a0b4;
      --line: rgba(255, 255, 255, .095);
      --accent: #7dd3fc;
      --accent-strong: #38bdf8;
      --warn: #fbbf24;
      --fail: #fb7185;
      --pass: #34d399;
      --shadow: 0 22px 70px rgba(0, 0, 0, .35);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background:
        radial-gradient(circle at top left, rgba(56, 189, 248, .15), transparent 34vw),
        radial-gradient(circle at 80% 10%, rgba(167, 139, 250, .10), transparent 30vw),
        linear-gradient(180deg, #090d16 0%, var(--bg) 46%, #05070c 100%);
      color: var(--ink);
      min-height: 100vh;
    }
    header {
      border-bottom: 1px solid var(--line);
      background: var(--panel);
      padding: 16px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }
    h1 {
      margin: 0;
      font-size: 20px;
      font-weight: 700;
      letter-spacing: 0;
    }
    .status {
      color: var(--muted);
      font-size: 13px;
      white-space: nowrap;
    }
    main {
      display: grid;
      grid-template-columns: minmax(320px, 420px) minmax(0, 1fr);
      min-height: calc(100vh - 65px);
    }
    form {
      background: var(--panel);
      border-right: 1px solid var(--line);
      padding: 20px;
      overflow: auto;
    }
    .results {
      padding: 20px;
      overflow: auto;
    }
    .group {
      margin-bottom: 16px;
    }
    .hint {
      color: var(--muted);
      font-size: 12px;
      line-height: 1.4;
      margin-top: 6px;
    }
    label {
      display: block;
      font-size: 13px;
      color: #334155;
      font-weight: 650;
      margin-bottom: 6px;
    }
    input, textarea, select {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px 11px;
      font: inherit;
      color: var(--ink);
      background: #fff;
    }
    textarea {
      min-height: 120px;
      resize: vertical;
    }
    details {
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 12px;
      margin-bottom: 16px;
      background: #fbfcfd;
    }
    summary {
      cursor: pointer;
      font-size: 14px;
      font-weight: 750;
      color: #243142;
    }
    .prompt-editor {
      min-height: 170px;
      margin-top: 6px;
      font-family: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace;
      font-size: 12px;
      line-height: 1.45;
    }
    .prompt-editor.tall {
      min-height: 260px;
    }
    .prompt-source-box {
      max-height: 260px;
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px 11px;
      background: #fbfcfd;
      color: #334155;
      font-family: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace;
      font-size: 12px;
      line-height: 1.45;
    }
    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }
    .tabs {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 6px;
      background: #edf1f5;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 4px;
      margin-bottom: 16px;
    }
    .tab-button {
      border: 0;
      border-radius: 6px;
      background: transparent;
      color: #475569;
      padding: 9px 8px;
      font-size: 13px;
      font-weight: 750;
      cursor: pointer;
      width: auto;
    }
    .tab-button.active {
      background: #fff;
      color: var(--accent-strong);
      box-shadow: 0 1px 2px rgba(15, 23, 42, .08);
    }
    .tab-panel {
      display: none;
    }
    .tab-panel.active {
      display: block;
    }
    .check {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
      color: #334155;
      margin: 8px 0 16px;
    }
    .check input {
      width: auto;
    }
    button {
      width: 100%;
      border: 0;
      border-radius: 6px;
      background: var(--accent);
      color: #fff;
      padding: 11px 14px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
    }
    button:hover { background: var(--accent-strong); }
    button:disabled {
      opacity: .65;
      cursor: wait;
    }
    .progress-panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 14px;
      margin-bottom: 16px;
    }
    .progress-top {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: baseline;
      margin-bottom: 10px;
    }
    .progress-title {
      font-size: 14px;
      font-weight: 750;
    }
    .progress-percent {
      font-size: 13px;
      color: var(--muted);
      font-weight: 650;
    }
    .progress-track {
      height: 9px;
      border-radius: 999px;
      background: #e8edf3;
      overflow: hidden;
    }
    .progress-fill {
      height: 100%;
      width: 0%;
      background: var(--accent);
      transition: width .35s ease;
    }
    .progress-current {
      margin-top: 9px;
      font-size: 13px;
      color: var(--muted);
    }
    .workflow {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 8px;
      margin-bottom: 16px;
    }
    .step {
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 6px;
      padding: 10px;
      font-size: 13px;
      color: #334155;
      min-height: 48px;
      display: flex;
      align-items: center;
      transition: border-color .2s ease, background .2s ease, color .2s ease;
    }
    .step.active {
      border-color: var(--accent);
      background: #eefaf7;
      color: var(--accent-strong);
      font-weight: 750;
    }
    .step.done {
      border-color: #b9decf;
      background: #f3fbf7;
      color: var(--pass);
    }
    .creative-progress-panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 14px;
      margin-bottom: 16px;
    }
    .creative-progress-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: baseline;
      margin-bottom: 6px;
    }
    .creative-progress-subtitle {
      color: var(--muted);
      font-size: 12px;
      line-height: 1.4;
      margin-bottom: 12px;
    }
    .creative-status {
      color: var(--muted);
      font-size: 13px;
      font-weight: 650;
      white-space: nowrap;
    }
    .creative-track {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
    }
    .creative-step {
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fbfcfd;
      min-height: 112px;
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 6px;
      transition: border-color .2s ease, background .2s ease;
    }
    .creative-kicker {
      color: var(--muted);
      font-size: 11px;
      font-weight: 750;
      text-transform: uppercase;
      letter-spacing: .04em;
    }
    .creative-name {
      color: var(--ink);
      font-size: 14px;
      font-weight: 800;
    }
    .creative-detail {
      color: var(--muted);
      font-size: 12px;
      line-height: 1.35;
      flex: 1;
    }
    .creative-state {
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
    }
    .creative-step.active {
      border-color: var(--accent);
      background: #eefaf7;
    }
    .creative-step.active .creative-state {
      color: var(--accent-strong);
    }
    .creative-step.done {
      border-color: #b9decf;
      background: #f3fbf7;
    }
    .creative-step.done .creative-state {
      color: var(--pass);
    }
    .creative-step.blocked,
    .creative-step.failed,
    .creative-step.skipped {
      border-color: #f0b8b4;
      background: #fff7f6;
    }
    .creative-step.blocked .creative-state,
    .creative-step.failed .creative-state {
      color: var(--fail);
    }
    .creative-step.skipped {
      border-color: #eed5a7;
      background: #fffdf5;
    }
    .creative-step.skipped .creative-state {
      color: var(--warn);
    }
    .summary {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }
    .report-hero {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 16px;
      margin-bottom: 12px;
    }
    .report-hero h2 {
      margin: 0 0 6px;
      font-size: 18px;
    }
    .report-hero p {
      color: var(--muted);
      line-height: 1.45;
      margin: 0;
      font-size: 13px;
    }
    .report-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
      margin-bottom: 12px;
    }
    .report-card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 14px;
      min-height: 116px;
    }
    .report-card h3 {
      margin: 0 0 8px;
      font-size: 13px;
      color: #243142;
    }
    .report-card .big {
      font-size: 20px;
      font-weight: 850;
      margin-bottom: 6px;
      overflow-wrap: anywhere;
    }
    .report-card p, .report-card li {
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
      margin: 4px 0;
    }
    .report-card ul {
      padding-left: 18px;
      margin: 6px 0 0;
    }
    .status-chip {
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 3px 8px;
      font-size: 11px;
      font-weight: 800;
      background: #eef1f5;
      color: #415063;
      border: 1px solid #d5e1e7;
      margin-bottom: 8px;
    }
    .status-chip.pass, .status-chip.completed, .status-chip.approved {
      background: #edf9f1;
      border-color: #b9decf;
      color: var(--pass);
    }
    .status-chip.warning, .status-chip.partial, .status-chip.skipped, .status-chip.unknown {
      background: #fff8eb;
      border-color: #eed5a7;
      color: var(--warn);
    }
    .status-chip.blocked, .status-chip.fail, .status-chip.failed {
      background: #fff1f0;
      border-color: #f0b8b4;
      color: var(--fail);
    }
    .stage-list {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 10px;
    }
    .stage-card {
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      padding: 12px;
    }
    .stage-card h3 {
      margin: 0 0 8px;
      font-size: 13px;
    }
    .stage-card p {
      margin: 5px 0;
      font-size: 12px;
      line-height: 1.45;
      color: var(--muted);
    }
    .info-table {
      display: grid;
      gap: 6px;
    }
    .info-row {
      display: grid;
      grid-template-columns: minmax(120px, .7fr) 1fr;
      gap: 10px;
      border-bottom: 1px solid #eef1f5;
      padding-bottom: 6px;
      font-size: 12px;
    }
    .info-row span:first-child {
      color: var(--muted);
      font-weight: 700;
    }
    .info-row span:last-child {
      overflow-wrap: anywhere;
    }
    .audit-details {
      border: 1px solid var(--line);
      border-radius: 6px;
      margin-bottom: 12px;
      background: var(--panel);
      padding: 12px;
    }
    .metric, .section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 14px;
    }
    .metric .name {
      font-size: 12px;
      color: var(--muted);
      margin-bottom: 4px;
    }
    .metric .value {
      font-size: 20px;
      font-weight: 800;
    }
    .pass { color: var(--pass); }
    .warning { color: var(--warn); }
    .blocked, .fail { color: var(--fail); }
    .section {
      margin-bottom: 12px;
    }
    .section h2 {
      font-size: 15px;
      margin: 0 0 10px;
    }
    pre {
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      font-size: 12px;
      line-height: 1.45;
      color: #263241;
      background: #f9fafb;
      border: 1px solid #eef1f5;
      border-radius: 6px;
      padding: 10px;
      max-height: 360px;
      overflow: auto;
    }
    .empty {
      color: var(--muted);
      background: var(--panel);
      border: 1px dashed var(--line);
      border-radius: 6px;
      padding: 18px;
    }
    .links a {
      display: block;
      color: var(--accent-strong);
      font-size: 13px;
      margin-top: 4px;
      overflow-wrap: anywhere;
    }
    .asset-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
    }
    .asset-card {
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      overflow: hidden;
    }
    .asset-card img {
      width: 100%;
      aspect-ratio: 1 / 1;
      object-fit: cover;
      display: block;
      background: #eef1f5;
    }
    .asset-meta {
      padding: 10px;
      font-size: 12px;
      color: var(--muted);
      overflow-wrap: anywhere;
    }
    .asset-meta strong {
      display: block;
      color: var(--ink);
      margin-bottom: 4px;
    }
    .creative-card-title {
      display: flex;
      justify-content: space-between;
      gap: 8px;
      align-items: flex-start;
      margin-bottom: 8px;
    }
    .pill-row {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin: 8px 0;
    }
    .pill {
      border: 1px solid #d5e1e7;
      border-radius: 999px;
      padding: 3px 7px;
      color: #415063;
      background: #f7fafb;
      font-size: 11px;
      font-weight: 750;
      white-space: nowrap;
    }
    .creative-copy {
      color: #334155;
      font-size: 12px;
      line-height: 1.45;
      margin: 8px 0;
    }
    .creative-copy b {
      color: var(--ink);
    }
    .prompt-preview {
      margin-top: 8px;
      max-height: 150px;
    }
    .asset-card details {
      border: 0;
      border-top: 1px solid var(--line);
      border-radius: 0;
      margin: 0;
      padding: 9px 10px;
      background: #fbfcfd;
    }
    .asset-card details summary {
      font-size: 12px;
      color: var(--accent-strong);
    }
    .output-hero {
      display: grid;
      grid-template-columns: minmax(0, 1.6fr) minmax(240px, .8fr);
      gap: 12px;
      align-items: stretch;
      margin-bottom: 12px;
    }
    .output-hero .section {
      margin-bottom: 0;
    }
    .result-kicker {
      color: var(--muted);
      font-size: 12px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: .03em;
      margin-bottom: 6px;
    }
    .output-title {
      font-size: 22px;
      font-weight: 850;
      margin: 0 0 8px;
      line-height: 1.15;
    }
    .output-subtitle {
      color: #405066;
      font-size: 13px;
      line-height: 1.45;
      margin: 0 0 12px;
    }
    .preview-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 10px;
    }
    .preview-card {
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      overflow: hidden;
      min-width: 0;
    }
    .preview-card img {
      width: 100%;
      aspect-ratio: 1 / 1;
      object-fit: cover;
      display: block;
      background: #eef1f5;
    }
    .preview-meta {
      padding: 8px;
      font-size: 11px;
      line-height: 1.35;
      color: var(--muted);
      overflow-wrap: anywhere;
    }
    .preview-meta strong {
      display: block;
      color: var(--ink);
      margin-bottom: 3px;
    }
    .preview-empty {
      border: 1px dashed var(--line);
      border-radius: 6px;
      padding: 14px;
      color: #536174;
      background: #fbfcfd;
      font-size: 13px;
      line-height: 1.45;
    }
    .rating-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 12px;
      margin-top: 12px;
    }
    .rating-card {
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      padding: 12px;
      min-width: 0;
    }
    .rating-row {
      display: grid;
      grid-template-columns: minmax(110px, 1fr) 96px;
      gap: 8px;
      align-items: center;
      margin: 7px 0;
      font-size: 12px;
      color: #334155;
    }
    .rating-row select {
      padding: 7px 8px;
      font-size: 12px;
    }
    .rating-reasons {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 6px 10px;
      margin: 10px 0;
      font-size: 12px;
      color: #334155;
    }
    .rating-reasons label {
      display: flex;
      gap: 6px;
      align-items: center;
      margin: 0;
      font-size: 12px;
      font-weight: 550;
    }
    .rating-reasons input {
      width: auto;
    }
    .rating-actions {
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: 8px;
      margin-top: 8px;
    }
    .rating-actions button {
      padding: 8px 9px;
      font-size: 12px;
    }
    .rating-actions .reject {
      background: var(--fail);
    }
    .rating-actions .regen {
      background: #475569;
    }
    .creative-board {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 12px;
    }
    .creative-set-card {
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 8px;
      min-width: 0;
    }
    .creative-set-card.generated {
      border-color: #8fd4b3;
      box-shadow: inset 0 3px 0 #26a269;
    }
    .creative-set-card.selected {
      border-color: #b7d7ef;
      box-shadow: inset 0 3px 0 var(--accent);
    }
    .creative-set-card.skipped {
      opacity: .72;
    }
    .creative-set-card .set-id {
      font-size: 20px;
      font-weight: 850;
      color: var(--ink);
    }
    .creative-set-card .set-name {
      font-size: 13px;
      font-weight: 800;
      color: #243244;
    }
    .creative-set-card .set-purpose {
      font-size: 12px;
      line-height: 1.45;
      color: #4b5b70;
    }
    .mini-thumb-row {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 6px;
    }
    .mini-thumb-row img {
      width: 100%;
      aspect-ratio: 1 / 1;
      object-fit: cover;
      border-radius: 4px;
      background: #eef1f5;
      border: 1px solid #e5ebf0;
    }
    .audit-collapse {
      margin-top: 12px;
    }
    .topbar {
      position: sticky;
      top: 0;
      z-index: 30;
      min-height: 72px;
      border-bottom: 1px solid var(--line);
      background: rgba(7, 9, 15, .82);
      backdrop-filter: blur(18px);
      padding: 14px 22px;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 0;
    }
    .brand-mark {
      width: 38px;
      height: 38px;
      border-radius: 12px;
      background: linear-gradient(135deg, #7dd3fc, #a78bfa 58%, #f0abfc);
      box-shadow: 0 12px 28px rgba(56, 189, 248, .22);
    }
    .brand-eyebrow {
      color: var(--muted);
      font-size: 11px;
      font-weight: 800;
      letter-spacing: .08em;
      text-transform: uppercase;
    }
    .topbar-actions {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .topbar .status {
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 7px 11px;
      background: rgba(255, 255, 255, .055);
    }
    .app-shell {
      display: grid;
      grid-template-columns: 248px minmax(0, 1fr);
      min-height: calc(100vh - 72px);
    }
    .sidebar {
      position: sticky;
      top: 72px;
      height: calc(100vh - 72px);
      padding: 18px 14px;
      border-right: 1px solid var(--line);
      background: rgba(10, 13, 21, .68);
      overflow: auto;
    }
    .sidebar-section {
      color: #667085;
      font-size: 10px;
      font-weight: 850;
      letter-spacing: .1em;
      text-transform: uppercase;
      margin: 16px 10px 8px;
    }
    .sidebar-nav {
      display: grid;
      gap: 5px;
    }
    .nav-item {
      display: flex;
      align-items: center;
      gap: 10px;
      color: #cbd5e1;
      text-decoration: none;
      border-radius: 10px;
      padding: 10px 11px;
      font-size: 13px;
      font-weight: 700;
    }
    .nav-item span:first-child {
      display: grid;
      place-items: center;
      width: 22px;
      height: 22px;
      border-radius: 7px;
      background: rgba(255,255,255,.065);
      color: var(--accent);
      font-size: 12px;
    }
    .nav-item.active, .nav-item:hover {
      background: rgba(255, 255, 255, .075);
      color: #fff;
    }
    .sidebar-card {
      margin: 18px 4px 0;
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 13px;
      background: rgba(255, 255, 255, .045);
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
    }
    .workspace {
      min-width: 0;
      padding: 22px;
    }
    .workspace-hero {
      border: 1px solid var(--line);
      border-radius: 22px;
      padding: 24px;
      margin-bottom: 18px;
      background:
        linear-gradient(135deg, rgba(125, 211, 252, .12), rgba(167, 139, 250, .08)),
        rgba(255, 255, 255, .04);
      box-shadow: var(--shadow);
    }
    .workspace-hero h2 {
      margin: 0;
      font-size: clamp(28px, 4vw, 48px);
      line-height: 1.02;
      letter-spacing: 0;
    }
    .workspace-hero p {
      margin: 12px 0 0;
      max-width: 820px;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.6;
    }
    .quick-stats {
      display: grid;
      grid-template-columns: repeat(5, minmax(130px, 1fr));
      gap: 10px;
      margin-top: 18px;
    }
    .quick-stat {
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 13px;
      background: rgba(2, 6, 23, .36);
    }
    .quick-stat b {
      display: block;
      font-size: 18px;
      margin-bottom: 4px;
    }
    .quick-stat span {
      color: var(--muted);
      font-size: 11px;
      font-weight: 750;
      text-transform: uppercase;
      letter-spacing: .04em;
    }
    .recent-projects {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
      margin-top: 14px;
    }
    .project-card {
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 14px;
      background: rgba(255, 255, 255, .045);
      min-height: 96px;
    }
    .project-card strong {
      display: block;
      margin-bottom: 8px;
      font-size: 13px;
    }
    .project-card p {
      margin: 0;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
    }
    .workspace-grid {
      display: grid;
      grid-template-columns: minmax(330px, 430px) minmax(0, 1fr);
      gap: 18px;
      align-items: start;
    }
    .campaign-console {
      position: sticky;
      top: 92px;
      max-height: calc(100vh - 112px);
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 18px;
      background: rgba(14, 18, 28, .88);
      box-shadow: var(--shadow);
      padding: 16px;
    }
    .campaign-console-head {
      margin-bottom: 14px;
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: rgba(255,255,255,.045);
    }
    .campaign-console-head h2 {
      margin: 0 0 6px;
      font-size: 18px;
    }
    .campaign-console-head p {
      margin: 0;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
    }
    .wizard-roadmap {
      display: grid;
      gap: 7px;
      margin: 12px 0 0;
    }
    .wizard-step {
      display: flex;
      gap: 8px;
      align-items: center;
      color: #cbd5e1;
      font-size: 12px;
      font-weight: 750;
    }
    .wizard-step b {
      display: grid;
      place-items: center;
      width: 22px;
      height: 22px;
      border-radius: 999px;
      color: #06111f;
      background: var(--accent);
      font-size: 11px;
    }
    .studio-pane {
      min-width: 0;
    }
    .dashboard-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 12px;
    }
    .workspace-band {
      margin: 18px 0;
    }
    .workspace-band-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: end;
      margin-bottom: 10px;
    }
    .workspace-band h2 {
      margin: 0;
      font-size: 18px;
    }
    .workspace-band p {
      margin: 4px 0 0;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }
    .why-card {
      border: 1px solid rgba(125, 211, 252, .2);
      border-radius: 12px;
      padding: 10px;
      background: rgba(125, 211, 252, .06);
      color: #d8eefc;
      font-size: 12px;
      line-height: 1.45;
    }
    .why-card b {
      display: block;
      color: #fff;
      margin-bottom: 5px;
    }
    header, form, .results {
      background: transparent;
      border: 0;
    }
    label, .check, .rating-row, .rating-reasons, .creative-copy, .output-subtitle,
    .creative-set-card .set-purpose, .creative-set-card .set-name, .info-row {
      color: #c3ccda;
    }
    input, textarea, select {
      border-color: var(--line);
      background: rgba(255, 255, 255, .055);
      color: var(--ink);
    }
    input::placeholder, textarea::placeholder {
      color: #64748b;
    }
    details, .section, .metric, .report-hero, .report-card, .stage-card,
    .progress-panel, .creative-progress-panel, .creative-step, .asset-card,
    .preview-card, .rating-card, .creative-set-card, .audit-details {
      border-color: var(--line);
      background: rgba(255, 255, 255, .045);
      border-radius: 14px;
    }
    .creative-set-card.generated {
      border-color: rgba(52, 211, 153, .45);
      box-shadow: inset 0 3px 0 var(--pass);
    }
    .creative-set-card.selected {
      border-color: rgba(125, 211, 252, .45);
      box-shadow: inset 0 3px 0 var(--accent);
    }
    .creative-step.active, .creative-step.done, .creative-step.skipped,
    .creative-step.blocked, .creative-step.failed {
      background: rgba(255, 255, 255, .07);
    }
    summary, .report-card h3, .preview-meta strong, .asset-meta strong,
    .creative-set-card .set-id, .creative-name {
      color: var(--ink);
    }
    .tabs {
      background: rgba(255,255,255,.05);
      border-color: var(--line);
      border-radius: 12px;
    }
    .tab-button {
      color: #cbd5e1;
      border-radius: 9px;
    }
    .tab-button.active {
      color: #06111f;
      background: var(--accent);
      box-shadow: none;
    }
    pre, .prompt-source-box {
      color: #dbeafe;
      background: rgba(2, 6, 23, .55);
      border-color: var(--line);
    }
    .pill, .status-chip {
      border-color: var(--line);
      background: rgba(255, 255, 255, .07);
      color: #dbe4ef;
    }
    .preview-empty, .empty {
      background: rgba(255, 255, 255, .035);
      color: var(--muted);
    }
    button {
      border-radius: 12px;
      color: #06111f;
      background: linear-gradient(135deg, #7dd3fc, #a7f3d0);
    }
    button:hover {
      background: linear-gradient(135deg, #38bdf8, #6ee7b7);
    }
    @media (max-width: 860px) {
      .app-shell { grid-template-columns: 1fr; }
      .sidebar { position: static; height: auto; border-right: 0; border-bottom: 1px solid var(--line); }
      .workspace { padding: 14px; }
      .workspace-grid { grid-template-columns: 1fr; }
      .campaign-console { position: static; max-height: none; }
      .quick-stats { grid-template-columns: repeat(2, minmax(130px, 1fr)); }
      .recent-projects { grid-template-columns: 1fr; }
      header { align-items: flex-start; flex-direction: column; }
      .status { white-space: normal; }
      .creative-track { grid-template-columns: 1fr; }
      .output-hero { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header class="topbar">
    <div class="brand">
      <div class="brand-mark" aria-hidden="true"></div>
      <div>
        <div class="brand-eyebrow">AI Creative Ads Platform</div>
        <h1>Creative Operating System</h1>
      </div>
    </div>
    <div class="topbar-actions">
    <div class="status" id="status">Připraveno | Workflow V2</div>
    </div>
  </header>
  <main class="app-shell">
    <aside class="sidebar" aria-label="Workspace navigation">
      <div class="sidebar-section">Workspace</div>
      <nav class="sidebar-nav">
        <a class="nav-item active" href="#dashboard"><span>D</span>Dashboard</a>
        <a class="nav-item" href="#new-campaign"><span>N</span>New Campaign</a>
        <a class="nav-item" href="#creative-studio"><span>C</span>Creative Studio</a>
        <a class="nav-item" href="#asset-library"><span>A</span>Asset Library</a>
        <a class="nav-item" href="#prompt-lab"><span>P</span>Prompt Lab</a>
        <a class="nav-item" href="#analytics"><span>G</span>Analytics</a>
      </nav>
      <div class="sidebar-section">System</div>
      <nav class="sidebar-nav">
        <a class="nav-item" href="#models"><span>M</span>Models</a>
        <a class="nav-item" href="#team"><span>T</span>Team</a>
        <a class="nav-item" href="#settings"><span>S</span>Settings</a>
      </nav>
      <div class="sidebar-card">
        WORKSPACE -> PROJECT -> CAMPAIGN -> CREATIVE SET -> ASSET. Kazdy vystup ma plan, prompt audit, duvod existence, rating a memory signal.
      </div>
    </aside>
    <section class="workspace">
      <section class="workspace-hero" id="dashboard">
        <div class="brand-eyebrow">Creative Intelligence Dashboard</div>
        <h2>Generate high-performing ads with AI</h2>
        <p>Professional workflow for UGC video, static ads, carousel creatives, prompt auditing, quality scoring and creative memory. Build campaigns, review assets and let performance data shape the next generation.</p>
        <div class="quick-stats">
          <div class="quick-stat"><b id="dashCreatives">Live</b><span>Creatives Generated</span></div>
          <div class="quick-stat"><b id="dashCtr">RAG</b><span>Winning CTR</span></div>
          <div class="quick-stat"><b>1</b><span>Active Workspace</span></div>
          <div class="quick-stat"><b id="dashCost">$0.00</b><span>Cost This Month</span></div>
          <div class="quick-stat"><b id="dashBestHook">Identity</b><span>Best Performing Hook</span></div>
        </div>
        <div class="recent-projects" aria-label="Recent projects">
          <div class="project-card">
            <strong>Summer Bags UK</strong>
            <p>Premium lifestyle workflow for Meta, British creator voice, identity and aspiration angles.</p>
          </div>
          <div class="project-card">
            <strong>Beauty UGC US</strong>
            <p>Review-first mobile workflow with avatar consistency, realism QA and prompt audit trail.</p>
          </div>
          <div class="project-card">
            <strong>Sneakers Campaign</strong>
            <p>Category-aware visuals with on-person product context, retargeting statics and carousel assets.</p>
          </div>
        </div>
      </section>
      <div class="workspace-grid">
    <form id="generatorForm" class="campaign-console">
      <div class="campaign-console-head" id="new-campaign">
        <div class="brand-eyebrow">New Campaign Wizard</div>
        <h2>Build a complete creative set</h2>
        <p>Start with product and avatar data. The app then builds strategy, prompts, provider validation, assets, ratings and memory guidance.</p>
        <div class="wizard-roadmap">
          <div class="wizard-step"><b>1</b>Product input and AI extraction</div>
          <div class="wizard-step"><b>2</b>Avatar identity and voice</div>
          <div class="wizard-step"><b>3</b>Platform, market and language</div>
          <div class="wizard-step"><b>4</b>Creative strategy and angles</div>
          <div class="wizard-step"><b>5</b>Generation plan and cost guard</div>
        </div>
      </div>
      <div class="tabs" role="tablist" aria-label="Nastavení">
        <button class="tab-button active" type="button" data-tab="setup">Vstup</button>
        <button class="tab-button" type="button" data-tab="avatar">Avatar</button>
        <button class="tab-button" type="button" data-tab="prompts">Prompty</button>
      </div>
      <div class="tab-panel active" id="tab-setup">
      <div class="campaign-console-head">
        <div class="brand-eyebrow">Step 1-5</div>
        <h2>Product, market and generation plan</h2>
        <p>Product data drives category intelligence, platform adaptation, creative strategy and final generation scope.</p>
      </div>
      <div class="group">
        <label for="product_image">Obrázek produktu</label>
        <input id="product_image" name="product_image" type="file" accept="image/*">
        <div class="hint">Nahraj soubor nebo níže vlož veřejnou HTTPS URL obrázku.</div>
      </div>
      <div class="group">
        <label for="product_name">Název produktu</label>
        <input id="product_name" name="product_name" type="text" placeholder="Everyday Tote" required>
      </div>
      <div class="group">
        <label for="product_info">Poznámky k produktu</label>
        <textarea id="product_info" name="product_info" placeholder="Viditelné vlastnosti, použití, bezpečné benefity. Nepiš nepodložená tvrzení."></textarea>
      </div>
      <div class="group">
        <label for="product_category">Typ produktu pro prompty</label>
        <select id="product_category" name="product_category">
          <option value="auto" selected>Auto detect z názvu a poznámek</option>
          <option value="handbag">Kabelky / tote bags</option>
          <option value="shoes">Boty / footwear</option>
          <option value="apparel">Oblečení / apparel</option>
        </select>
        <div class="hint">Tahle volba řídí category-specific prompt layer pro video i statické kreativy. Produktová fakta se pořád berou jen z briefu a reference.</div>
      </div>
      <div class="group">
        <label for="generation_mode">Co chceš generovat</label>
        <select id="generation_mode" name="generation_mode">
          <option value="both" selected>UGC video + statické kreativy</option>
          <option value="video">Jen UGC video</option>
          <option value="static">Jen statické kreativy</option>
        </select>
        <div class="hint">Creative plan a prompty se připraví vždy. API volání se spustí jen pro zvolené výstupy.</div>
      </div>
      <div class="grid">
        <div class="group">
          <label for="avatar_id">Avatar</label>
          <select id="avatar_id" name="avatar_id">
            <option value="avatar1">Avatar1</option>
            <option value="default_creator">Default Creator</option>
            <option value="premium_creator">Premium Creator</option>
          </select>
        </div>
        <div class="group">
          <label for="platform">Platforma</label>
          <select id="platform" name="platform">
            <option value="meta" selected>Meta Ads</option>
            <option value="google_ads">Google Ads</option>
            <option value="tiktok">TikTok</option>
            <option value="instagram">Instagram Reels</option>
            <option value="youtube">YouTube</option>
          </select>
        </div>
      </div>
      <div class="grid">
        <div class="group">
          <label for="market">Trh</label>
          <select id="market" name="market">
            <option value="CZ">Česko</option>
            <option value="SK">Slovensko</option>
            <option value="US">USA</option>
            <option value="UK" selected>Velká Británie</option>
            <option value="DE">Německo</option>
            <option value="AT">Rakousko</option>
            <option value="PL">Polsko</option>
            <option value="EU">Evropská unie</option>
          </select>
        </div>
        <div class="group">
          <label for="language">Jazyk výstupu</label>
          <select id="language" name="language">
            <option value="cs">Čeština</option>
            <option value="sk">Slovenština</option>
            <option value="en" selected>Angličtina</option>
            <option value="de">Němčina</option>
            <option value="pl">Polština</option>
            <option value="es">Španělština</option>
            <option value="fr">Francouzština</option>
            <option value="it">Italština</option>
          </select>
        </div>
      </div>
      <div class="grid">
        <div class="group">
          <label for="video_length">Délka v sekundách</label>
          <input id="video_length" name="video_length" type="number" min="6" max="60" value="15">
        </div>
        <div class="group">
          <label for="resolution">Rozlišení</label>
          <select id="resolution" name="resolution">
            <option value="720p">720p</option>
            <option value="1080p">1080p</option>
          </select>
        </div>
      </div>
      <label class="check">
        <input id="testimonial_mode" name="testimonial_mode" type="checkbox" value="true">
        Testimonial režim
      </label>
      <div class="group">
        <label for="testimonial_source">Zdroj testimonialu</label>
        <input id="testimonial_source" name="testimonial_source" type="text" placeholder="Povinné jen pro testimonial režim">
      </div>
      <div class="group" id="models">
        <label for="seedance_model">Seedance model</label>
        <select id="seedance_model" name="seedance_model">
          <option value="bytedance/seedance-2.0-fast" selected>Seedance 2.0 Fast</option>
          <option value="bytedance/seedance-2.0">Seedance 2.0 Normal</option>
        </select>
      </div>
      <div class="group">
        <label for="openrouter_api_key">OpenRouter API key</label>
        <input id="openrouter_api_key" name="openrouter_api_key" type="password" autocomplete="off" placeholder="sk-or-...">
        <div class="hint">Volitelne. Kdyz je klic v .env, muzes nechat prazdne.</div>
      </div>
      <div class="group">
        <label for="prompt_model">Prompt model pro UGC + staticke kreativy</label>
        <input id="prompt_model" name="prompt_model" type="text" value="openai/gpt-5.4-mini">
        <div class="hint">Pouzije se pro OpenRouter prompt enhancement: scene JSON pro UGC video a prompt/copy refine pro staticke kreativy pred image modelem.</div>
      </div>
      <details open>
        <summary>Staticke ads obrazky</summary>
        <div class="hint">Statické kreativy se budou volat jen když je výše zvoleno "Jen statické kreativy" nebo "UGC video + statické kreativy".</div>
        <div class="group">
          <label for="image_model">Image model</label>
          <input id="image_model" name="image_model" type="text" value="google/gemini-3-pro-image-preview">
          <div class="hint">Nano Banana Pro / Gemini 3 Pro Image Preview v OpenRouteru.</div>
        </div>
        <div class="grid">
          <div class="group">
            <label for="max_static_images">Limit kreativ</label>
            <input id="max_static_images" name="max_static_images" type="number" min="1" max="10" value="8">
            <div class="hint">Jen horni strop. Kdyz plan obsahuje 8 kreativ a limit je 10, vygeneruje se porad jen 8. Nic se nedoplnuje duplicitami.</div>
          </div>
          <div class="group">
            <label for="image_size">Velikost</label>
            <select id="image_size" name="image_size">
              <option value="1K" selected>1K</option>
              <option value="2K">2K</option>
              <option value="4K">4K</option>
            </select>
          </div>
        </div>
      </details>
      <div class="group">
        <label for="product_reference_url">URL reference produktu</label>
        <input id="product_reference_url" name="product_reference_url" type="url" placeholder="https://example.com/product.jpg">
        <div class="hint">Pro Seedance použij veřejný obrázek dostupný z internetu. Lokální upload zůstane jen pro lokální workflow.</div>
      </div>
      <div class="hint">Do kreativ se nepise URL, tlacitko ani instrukce ke kliknuti. Cilova URL a CTA ovladaci prvek se nastavi az v Meta nebo Google Ads kampani.</div>
      </div>
      <div class="tab-panel" id="tab-avatar">
      <div class="campaign-console-head">
        <div class="brand-eyebrow">Step 2</div>
        <h2>Avatar and voice personality</h2>
        <p>Use your own creator reference for consistency, identity lock and market-specific voice direction.</p>
      </div>
      <div class="group">
        <label for="custom_avatar_name">Jméno / label vlastní osoby</label>
        <input id="custom_avatar_name" name="custom_avatar_name" type="text" value="Můj AI avatar" placeholder="Můj AI avatar">
        <div class="hint">Interní label pro konzistenci. Nemusí se zobrazovat v reklamě.</div>
      </div>
      <div class="group">
        <label for="avatar_reference_url">URL reference mého AI avatara</label>
        <input id="avatar_reference_url" name="avatar_reference_url" type="url" value="https://i.ibb.co/6082rzf9/newkoi.png" placeholder="https://example.com/avatar.png">
        <div class="hint">Pro konzistenci použij jednu čistou, veřejnou HTTPS fotku: obličej vidět, přirozené světlo, bez filtrů, bez brýlí přes oči.</div>
      </div>
      <div class="group">
        <label for="custom_avatar_persona">Persona / energie na kameru</label>
        <input id="custom_avatar_persona" name="custom_avatar_persona" type="text" value="natural UGC creator, calm and direct, slightly imperfect delivery" placeholder="natural UGC creator, calm and direct">
      </div>
      <div class="group">
        <label for="custom_avatar_voice">Hlas a přízvuk</label>
        <input id="custom_avatar_voice" name="custom_avatar_voice" type="text" value="natural British English creator voice, relaxed and conversational" placeholder="natural British English creator voice">
      </div>
      <div class="group">
        <label for="avatar_wardrobe_policy">Wardrobe lock</label>
        <select id="avatar_wardrobe_policy" name="avatar_wardrobe_policy">
          <option value="reference_unchanged" selected>Stejné oblečení jako reference</option>
          <option value="consistent_simple">Jednoduché konzistentní oblečení</option>
          <option value="allow_controlled_change">Kontrolovaná změna jen když dává smysl</option>
        </select>
        <div class="hint">Nejvyšší konzistence = stejné oblečení jako v referenci. Změny outfitu zvyšují riziko driftu identity.</div>
      </div>
      <div class="group">
        <label for="avatar_identity_note">Poznámka k identitě / projevu</label>
        <textarea id="avatar_identity_note" name="avatar_identity_note" placeholder="Např. držet klidný tón, žádné přehrávání, mluvit jako normální člověk z UK."></textarea>
      </div>
      <label class="check">
        <input id="avatar_own_person_consent" name="avatar_own_person_consent" type="checkbox" value="true" checked>
        Souhlasím s použitím mé podoby jako AI avatara pro tvorbu reklamních videí pro zvolený brand/projekt, včetně úprav, lip-syncu a generování nových scén.
      </label>
      <label class="check">
        <input id="use_avatar_image_reference" name="use_avatar_image_reference" type="checkbox" value="true" checked>
        Poslat vlastní osobu jako Seedance image reference pro identity lock
      </label>
      <div class="hint">Pro konzistentní osobu zapnuto. Kdyby provider vrátil privacy/sensitive blokaci, vypni to: app pak pojede prompt-only, ale konzistence bude slabší.</div>
      </div>
      <div class="tab-panel" id="tab-prompts">
      <div id="settings"></div>
      <div class="campaign-console-head">
        <div class="brand-eyebrow">Prompt Lab Settings</div>
        <h2>Models, category rules and safety</h2>
        <p>Edit only the human-readable prompt layers. The app still shows final compiled prompts and payloads after generation.</p>
      </div>
      <div class="hint">Prompt nastavení je rozdělené podle toho, kde se opravdu používá: prompt model, Seedance video, category layer a audit zdrojů.</div>
      <details open>
        <summary>Core video prompts</summary>
        <div class="group">
          <label for="content_prompt_system">OpenRouter prompt model: system prompt</label>
          <textarea class="prompt-editor tall" id="content_prompt_system" name="content_prompt_system"></textarea>
          <div class="hint">Použije se jen pro volitelné vylepšení strukturovaného scene JSONu přes prompt model.</div>
        </div>
        <div class="group">
          <label for="content_prompt_task">OpenRouter prompt model: task prompt</label>
          <textarea class="prompt-editor" id="content_prompt_task" name="content_prompt_task"></textarea>
        </div>
        <div class="group">
          <label for="base_video_prompt_template">Seedance base video prompt template</label>
          <textarea class="prompt-editor tall" id="base_video_prompt_template" name="base_video_prompt_template"></textarea>
          <div class="hint">Dostupné proměnné: {duration}, {platform}, {language}, {market}, {voice_profile}, {category_prompt}, {fidelity}, {avatar_instruction}, {voiceover}, {scene_summary}, {aspect_ratio}, {negative_prompt}</div>
        </div>
        <div class="group">
          <label for="negative_prompt">Negative prompt</label>
          <textarea class="prompt-editor" id="negative_prompt" name="negative_prompt"></textarea>
        </div>
      </details>
      <details open>
        <summary>Category prompt presets</summary>
        <div class="hint">Vybraný typ produktu použije příslušný preset níže. Text můžeš přepsat pro jednu session; nic se nezapisuje do zdrojáku.</div>
        <div class="group">
          <label for="category_prompt_handbag">Kabelky / handbags</label>
          <textarea class="prompt-editor" id="category_prompt_handbag" name="category_prompt_handbag"></textarea>
        </div>
        <div class="group">
          <label for="category_prompt_shoes">Boty / shoes</label>
          <textarea class="prompt-editor" id="category_prompt_shoes" name="category_prompt_shoes"></textarea>
        </div>
        <div class="group">
          <label for="category_prompt_apparel">Oblečení / apparel</label>
          <textarea class="prompt-editor" id="category_prompt_apparel" name="category_prompt_apparel"></textarea>
        </div>
      </details>
      <details>
        <summary>Prompt/data source inventory</summary>
        <div class="group">
          <pre class="prompt-source-box" id="prompt_source_inventory">Nacitani zdroju promptu...</pre>
          <div class="hint">Prehled vsech vrstev, ktere se podileji na vysledku. Editovatelna jsou textova pole vyse, ostatni vrstvy jsou trace/fallback/safety logika.</div>
        </div>
      </details>
      </div>
      <div class="section" id="creativePlanPreflight"></div>
      <button id="submitButton" type="submit">Generovat</button>
    </form>
    <section class="results studio-pane" id="creative-studio">
      <div class="section">
        <div class="result-kicker">Creative Studio</div>
        <h2>Campaign command center</h2>
        <div class="creative-copy">
          Tady vidis cely tok: plan kreativ pred generaci, live pipeline, vysledne assety, proc kazda kreativa existuje, Prompt Lab audit, Analytics a Creative Intelligence memory.
        </div>
      </div>
      <div class="section">
        <h2>Aktivní workflow V2</h2>
        <div class="creative-copy">
          Backend teď jede přes Multi-Agent Creative Brain, Structured Prompt Architecture V2, Prompt Compression, Vision QA a AI Self Critique.
          Tyhle vrstvy se projeví v prompt auditu a ve výsledkovém print-outu po generování.
        </div>
        <div class="stage-list">
          <div class="stage-card">
            <span class="status-chip pass">ACTIVE</span>
            <h3>Product intelligence</h3>
            <p>Auto category, material, audience, usage context, market position, season a style.</p>
          </div>
          <div class="stage-card">
            <span class="status-chip pass">ACTIVE</span>
            <h3>Advanced UGC</h3>
            <p>Emotional angle, voice personality, true scene chaining, wardrobe a environment continuity.</p>
          </div>
          <div class="stage-card">
            <span class="status-chip pass">ACTIVE</span>
            <h3>Prompt Architecture V2</h3>
            <p>Scene, camera, lighting, emotion, motion, product_rules a avatar_rules se kompilují až na konci.</p>
          </div>
          <div class="stage-card">
            <span class="status-chip pass">ACTIVE</span>
            <h3>Quality loops</h3>
            <p>Prompt compression, provider validation, vision fidelity/realism QA a AI self critique.</p>
          </div>
        </div>
      </div>
      <div class="section" id="creativeIntelligenceOverview">
        <h2>Creative Intelligence</h2>
        <div class="creative-copy">Nacitam znalostni bazi creative, ratings a performance dat...</div>
      </div>
      <div class="progress-panel">
        <div class="progress-top">
          <div class="progress-title">Stav generování</div>
          <div class="progress-percent" id="progressPercent">0%</div>
        </div>
        <div class="progress-track"><div class="progress-fill" id="progressFill"></div></div>
        <div class="progress-current" id="progressCurrent">Čekám na spuštění.</div>
      </div>
      <div class="creative-progress-panel">
        <div class="creative-progress-head">
          <div class="progress-title">Ads creative set</div>
          <div class="creative-status" id="creativeProgressStatus">Cekam na brief</div>
        </div>
        <div class="creative-progress-subtitle">Skladam media-plan sety: C1 UGC video, C2-C4 staticke 1:1 obrazky a C5 carousel 5 karet.</div>
        <div class="creative-track" id="creativeTrack"></div>
      </div>
      <div class="workflow" id="workflow"></div>
      <div class="summary" id="summary"></div>
      <div id="result"><div class="empty">Nahraj produkt a spusť celý workflow.</div></div>
    </section>
      </div>
    </section>
  </main>
  <script>
    const workflowSteps = [
      "Product Intake Agent",
      "Automatic Product Understanding",
      "Performance Memory Layer",
      "Audience Research Agent",
      "Emotional Angle Engine",
      "Creative Psychology Agent",
      "Voice Personality Engine",
      "UGC Hook Agent",
      "Scene Director Agent",
      "Scene Chaining Agent",
      "UGC Strategy Agent",
      "Content Prompt Engineer Agent",
      "Structured Prompt Architecture V2",
      "Prompt Compression Layer",
      "Ads Creative Set Agent",
      "Product Fidelity Guard",
      "Compliance Guard",
      "Quality Scorer",
      "Provider Capability Validation",
      "Static Image Generation",
      "Seedance Video Generation",
      "AI Self Critique",
      "Session Cost Summary",
      "Export JSON/Markdown"
    ];
    const workflow = document.getElementById("workflow");
    workflow.innerHTML = workflowSteps.map((step, index) => `<div class="step" data-step-index="${index}">${step}</div>`).join("");

    const creativeSteps = [
      {
        key: "C1",
        name: "UGC video",
        detail: "C1 | UGC | TOFU + retargeting | hlavni video set"
      },
      {
        key: "C2",
        name: "Static product hero",
        detail: "C2 | PRODUCT HERO | 1:1 | TOFU + retargeting | 10%"
      },
      {
        key: "C3",
        name: "Static use context",
        detail: "C3 | USE CONTEXT | 1:1 | TOFU + retargeting | 10%"
      },
      {
        key: "C4",
        name: "Static proof detail",
        detail: "C4 | DETAIL PROOF | 1:1 | retargeting | 10%"
      },
      {
        key: "C5",
        name: "Carousel buying guide",
        detail: "C5 | BUYING GUIDE | 1:1 | MOFU | 15%"
      }
    ];
    const creativeTrack = document.getElementById("creativeTrack");
    const creativeProgressStatus = document.getElementById("creativeProgressStatus");
    creativeTrack.innerHTML = creativeSteps.map((step, index) => `
      <div class="creative-step" data-creative-step="${index}">
        <div class="creative-kicker">Creative ${index + 1}</div>
        <div class="creative-name">${step.name}</div>
        <div class="creative-detail">${step.detail}</div>
        <div class="creative-state">Ceka</div>
      </div>
    `).join("");

    const form = document.getElementById("generatorForm");
    const statusEl = document.getElementById("status");
    const resultEl = document.getElementById("result");
    const summaryEl = document.getElementById("summary");
    const button = document.getElementById("submitButton");
    const progressFill = document.getElementById("progressFill");
    const progressPercent = document.getElementById("progressPercent");
    const progressCurrent = document.getElementById("progressCurrent");
    let progressTimer = null;
    let creativeTimer = null;
    let progressIndex = 0;
    let creativeProgressIndex = 0;
    let creativeProgressStarted = false;
    let memoryPreviewTimer = null;

    setupTabs();
    applyQueryParams();
    loadPromptSettings();
    loadCreativeIntelligenceOverview();
    resetCreativeProgress();
    updateCreativePlanPreflight();

    ["generation_mode", "max_static_images", "image_model", "seedance_model", "openrouter_api_key"].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.addEventListener("input", updateCreativePlanPreflight);
      if (el) el.addEventListener("change", updateCreativePlanPreflight);
    });
    ["product_name", "product_info", "product_category", "platform", "market", "language"].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.addEventListener("input", scheduleMemoryPreview);
      if (el) el.addEventListener("change", scheduleMemoryPreview);
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      button.disabled = true;
      statusEl.textContent = "Spouštím workflow...";
      summaryEl.innerHTML = "";
      startProgress();
      resultEl.innerHTML = `<div class="empty">Generuji vystup agentu. Pri zapnutem OpenRouter video/image generovani to muze trvat dele.</div>`;

      const formData = new FormData(form);
      if (!document.getElementById("testimonial_mode").checked) {
        formData.set("testimonial_mode", "false");
      }
      if (!document.getElementById("use_avatar_image_reference").checked) {
        formData.set("use_avatar_image_reference", "false");
      }
      if (!document.getElementById("avatar_own_person_consent").checked) {
        formData.set("avatar_own_person_consent", "false");
      }

      try {
        const response = await fetch("/generate", { method: "POST", body: formData });
        const payload = await parseResponse(response);
        renderResult(payload);
        finishProgress(payload);
        statusEl.textContent = response.ok ? "Hotovo" : "Požadavek selhal";
      } catch (error) {
        const recovered = await recoverLatestOutput(error);
        if (!recovered) {
          statusEl.textContent = "Chyba";
          failProgress(String(error));
          resultEl.innerHTML = `<div class="section"><h2>Chyba</h2><pre>${escapeHtml(String(error))}</pre></div>`;
        }
      } finally {
        button.disabled = false;
      }
    });

    function updateCreativePlanPreflight() {
      const target = document.getElementById("creativePlanPreflight");
      if (!target) return;
      const mode = document.getElementById("generation_mode")?.value || "both";
      const maxImages = Number(document.getElementById("max_static_images")?.value || 0);
      const hasUiKey = Boolean((document.getElementById("openrouter_api_key")?.value || "").trim());
      const rows = previewRows(mode, maxImages, hasUiKey);
      target.innerHTML = `
        <h2>Creative plan preview pred generaci</h2>
        <div class="creative-copy"><b>Orientační náhled:</b> finální stav se ještě ověří backendem podle API key z .env, provider validace a prompt modelu.</div>
        <div class="stage-list">
          ${rows.map((row) => `
            <div class="stage-card">
              <span class="status-chip ${statusClass(row.status)}">${escapeHtml(row.status)}</span>
              <h3>${escapeHtml(row.id)} ${escapeHtml(row.name)}</h3>
              <p>${escapeHtml(row.reason)}</p>
            </div>
          `).join("")}
        </div>
      `;
    }

    function previewRows(mode, maxImages, hasUiKey) {
      const imageSlots = [
        { id: "C2", name: "Pain", priority: 1 },
        { id: "C4", name: "Demo", priority: 2 },
        { id: "C3", name: "Identity", priority: 3 },
        { id: "C5", name: "Carousel", priority: 4 }
      ];
      const selected = imageSlots
        .slice()
        .sort((a, b) => a.priority - b.priority)
        .slice(0, Math.max(0, maxImages))
        .map((item) => item.id);
      const rows = [];
      rows.push({
        id: "C1",
        name: "Video",
        status: mode === "static" ? "SKIPPED" : "YES",
        reason: mode === "static" ? "generation mode=static" : "vybrane pro UGC video"
      });
      imageSlots.forEach((slot) => {
        let status = "YES";
        let reason = "vybrane pro static image generation";
        if (mode === "video") {
          status = "SKIPPED";
          reason = "generation mode=video";
        } else if (!selected.includes(slot.id)) {
          status = "SKIPPED";
          reason = "max_static_images";
        }
        rows.push({ id: slot.id, name: slot.name, status, reason });
      });
      if (!hasUiKey) {
        rows.push({
          id: "API",
          name: "Key",
          status: "UNKNOWN",
          reason: "UI key je prazdny; backend muze pouzit .env, jinak API generovani preskoci jako no API key"
        });
      }
      return rows;
    }


    function startProgress() {
      clearInterval(progressTimer);
      clearInterval(creativeTimer);
      progressIndex = 0;
      creativeProgressIndex = 0;
      creativeProgressStarted = false;
      resetCreativeProgress();
      setProgress(0, "Nahrávám produkt a připravuji vstup.");
      progressTimer = setInterval(() => {
        if (progressIndex < workflowSteps.length - 2) {
          progressIndex += 1;
          setProgress(progressIndex, workflowSteps[progressIndex]);
        }
      }, 1400);
    }

    function finishProgress(payload) {
      clearInterval(progressTimer);
      clearInterval(creativeTimer);
      const blocked = payload.final_export_status === "blocked" || payload.video_generation?.video_generation_status === "blocked";
      const failed = payload.video_generation?.video_generation_status === "failed";
      renderCreativeFinal(payload, blocked);
      setProgress(workflowSteps.length - 1, blocked ? "Export zablokován kontrolou." : failed ? "Workflow hotový, video skončilo chybou." : "Hotovo.");
    }

    function failProgress(message) {
      clearInterval(progressTimer);
      clearInterval(creativeTimer);
      setCreativeCards(creativeSteps.map(() => ({ className: "failed", state: "Chyba" })), "Workflow skoncil chybou");
      progressFill.style.width = "100%";
      progressFill.style.background = "var(--fail)";
      progressPercent.textContent = "Chyba";
      progressCurrent.textContent = message;
    }

    function setProgress(index, label) {
      const steps = Array.from(document.querySelectorAll(".step"));
      steps.forEach((step, stepIndex) => {
        step.classList.toggle("done", stepIndex < index);
        step.classList.toggle("active", stepIndex === index);
      });
      const percent = Math.round(((index + 1) / workflowSteps.length) * 100);
      progressFill.style.background = "var(--accent)";
      progressFill.style.width = `${percent}%`;
      progressPercent.textContent = `${percent}%`;
      progressCurrent.textContent = label;
      maybeStartCreativeProgress(index);
    }

    function resetCreativeProgress() {
      setCreativeCards(creativeSteps.map(() => ({ className: "", state: "Ceka" })), "Cekam na brief");
    }

    function maybeStartCreativeProgress(index) {
      const adsIndex = workflowSteps.indexOf("Ads Creative Set Agent");
      if (index !== adsIndex || creativeProgressStarted) return;
      creativeProgressStarted = true;
      creativeProgressIndex = 0;
      setCreativeActive(0, "Generuji C1 UGC video set");
      creativeTimer = setInterval(() => {
        creativeProgressIndex += 1;
        if (creativeProgressIndex < creativeSteps.length) {
          setCreativeActive(creativeProgressIndex, `Generuji ${creativeSteps[creativeProgressIndex].name}`);
          return;
        }
        clearInterval(creativeTimer);
        setCreativeCards(creativeSteps.map(() => ({ className: "done", state: "Set pripraven" })), "Ads creative set pripraven");
      }, 900);
    }

    function setCreativeActive(activeIndex, statusText) {
      const states = creativeSteps.map((_, index) => {
        if (index < activeIndex) return { className: "done", state: "Hotovo" };
        if (index === activeIndex) return { className: "active", state: "Generuji..." };
        return { className: "", state: "Ceka" };
      });
      setCreativeCards(states, statusText);
    }

    function renderCreativeFinal(payload, blocked) {
      const ads = payload.ads_creative_set || {};
      if (blocked) {
        setCreativeCards(creativeSteps.map(() => ({ className: "blocked", state: "Blokovano kontrolou" })), "Ads creative set zablokovan");
        return;
      }
      const imageGeneration = payload.static_image_generation || {};
      const videoGeneration = payload.video_generation || {};
      const selectedImagePlan = imageGeneration.generation_plan || [];
      const selectedBySet = selectedImagePlan.reduce((acc, item) => {
        const key = item.set_id || item.asset_type || "unknown";
        acc[key] = (acc[key] || 0) + 1;
        return acc;
      }, {});
      const imageStatus = imageGeneration.image_generation_status || "unknown";
      const reusedCount = imageGeneration.reused_count || 0;
      const reuseLabel = reusedCount ? `, reuse: ${reusedCount}` : "";
      const plan = ads.creative_plan || [];
      const states = creativeSteps.map((step) => {
        const item = plan.find((entry) => entry.set_id === step.key) || {};
        if (step.key === "C1") {
          if (videoGeneration.skipped_by_generation_mode) {
            return { className: "skipped", state: "Nevybrano v rezimu" };
          }
          return { className: "done", state: `${item.budget_share_percent || 55}% | video: ${videoGeneration.video_generation_status || "ready"}` };
        }
        if (step.key === "C5") {
          const selectedCards = selectedBySet.C5 || 0;
          return selectedCards
            ? { className: "done", state: `${selectedCards} vybrane karty | ${item.budget_share_percent || 15}%` }
            : { className: "skipped", state: imageGeneration.skipped_by_generation_mode ? "Nevybrano v rezimu" : "Mimo limit" };
        }
        const selectedCount = selectedBySet[step.key] || 0;
        return selectedCount
          ? { className: "done", state: `${item.angle || ""} | ${selectedCount} kreativa | image API: ${imageStatus}${reuseLabel}` }
          : { className: "skipped", state: imageGeneration.skipped_by_generation_mode ? "Nevybrano v rezimu" : "Mimo limit" };
      });
      const videoLabel = videoGeneration.skipped_by_generation_mode ? "video nevybrano" : "video vybrano";
      setCreativeCards(states, `Vybrane pro generovani: ${selectedImagePlan.length} image kreativ + ${videoLabel}`);
    }

    function setCreativeCards(states, statusText) {
      const cards = Array.from(document.querySelectorAll(".creative-step"));
      cards.forEach((card, index) => {
        const state = states[index] || { className: "", state: "Ceka" };
        card.classList.remove("active", "done", "blocked", "failed", "skipped");
        if (state.className) card.classList.add(state.className);
        const stateEl = card.querySelector(".creative-state");
        if (stateEl) stateEl.textContent = state.state;
      });
      creativeProgressStatus.textContent = statusText;
    }

    function renderResult(payload) {
      if (payload.error && !payload.workflow_sequence) {
        summaryEl.innerHTML = "";
        resultEl.innerHTML = `<div class="section"><h2>Chyba serveru</h2><pre>${escapeHtml(payload.error)}</pre></div>`;
        return;
      }
      const exportStatus = payload.final_export_status || "unknown";
      const fidelity = payload.product_fidelity_result?.product_fidelity_status || "unknown";
      const compliance = payload.compliance_result?.compliance_status || "unknown";
      const score = payload.quality_result?.overall_quality_score ?? "n/a";
      const aiPrompt = payload.content_prompt_package?.prompt_generation?.status || "unknown";
      const image = payload.static_image_generation?.image_generation_status || "unknown";
      const video = payload.video_generation?.video_generation_status || "unknown";
      const sessionCost = payload.session_cost_summary?.total_known_cost_display || "unknown";

      summaryEl.innerHTML = `
        ${metric("Export", exportStatus, exportStatus)}
        ${metric("AI prompt", aiPrompt, aiPrompt)}
        ${metric("Fidelita produktu", fidelity, fidelity)}
        ${metric("Compliance", compliance, compliance)}
        ${metric("Kvalita", score, "")}
        ${metric("Cena", sessionCost, "")}
        ${metric("Obrazky", image, image)}
        ${metric("Video", video, video)}
      `;

      const files = payload.output_files || {};
      const recoveryNotice = payload._recovered_from_latest_output ? renderRecoveryNotice() : "";
      const videoNotice = renderVideoNotice(payload);
      const imageNotice = renderImageNotice(payload);
      resultEl.innerHTML = `
        ${recoveryNotice}
        <div class="workspace-band" id="creative-studio-output">
          <div class="workspace-band-head">
            <div>
              <div class="result-kicker">Creative Studio</div>
              <h2>Review assets first</h2>
              <p>Visual previews, creative set cards, selection logic and generated assets stay at the top.</p>
            </div>
          </div>
        ${renderOutputHero(payload)}
        ${renderTopImagePreview(payload.static_image_generation)}
        ${renderAdsCreativeSetBoard(payload.ads_creative_set, payload.static_image_generation, payload.video_generation)}
        ${renderCreativePlan(payload.ads_creative_set, payload.static_image_generation, payload.video_generation)}
        ${renderImageGallery(payload.static_image_generation)}
        ${imageNotice}
        ${videoNotice}
        </div>
        <div class="workspace-band" id="prompt-lab">
          <div class="workspace-band-head">
            <div>
              <div class="result-kicker">Prompt Lab</div>
              <h2>Prompt audit and source trace</h2>
              <p>Provider validation, product understanding, fallback/refined prompts and final payload details.</p>
            </div>
          </div>
        ${renderProviderValidation(payload.provider_validation)}
        ${renderProductUnderstanding(payload.product_analysis)}
        ${renderPromptAuditPanel(payload.prompt_audit)}
        ${renderCreativeBrain(payload.ugc_strategy)}
        ${renderCreativePlanPreview(payload.creative_plan_preview)}
        </div>
        <div class="workspace-band" id="asset-library">
          <div class="workspace-band-head">
            <div>
              <div class="result-kicker">Asset Library</div>
              <h2>Files, copy and generation plan</h2>
              <p>Everything that can be reviewed, exported, rated or regenerated from this session.</p>
            </div>
          </div>
        <div class="section">
          <h2>Soubory</h2>
          <div class="links">
            <a>${escapeHtml(files.json_path || "JSON nebyl uložen")}</a>
            <a>${escapeHtml(files.markdown_path || "Markdown nebyl uložen")}</a>
            ${renderImageAssetLinks(payload.static_image_generation)}
            <a>${escapeHtml(payload.video_generation?.video_path || "Video nebylo vygenerováno")}</a>
          </div>
        </div>
        ${renderAdDescriptionSuggestions(payload.ads_creative_set)}
        ${renderImageGenerationPlan(payload.static_image_generation)}
        </div>
        <div class="workspace-band" id="analytics">
          <div class="workspace-band-head">
            <div>
              <div class="result-kicker">Analytics</div>
              <h2>Quality, memory and raw diagnostics</h2>
              <p>Self critique, Creative Intelligence retrieval, vision QA and troubleshooting audit.</p>
            </div>
          </div>
        ${renderSelfCritique(payload.self_critique)}
        ${renderCreativeMemory(payload.creative_memory)}
        ${renderVisionQualityPanel(payload.static_image_generation)}
        <details class="audit-details audit-collapse">
          <summary>Workflow report detail</summary>
          ${renderWorkflowReport(payload.workflow_report)}
        </details>
        ${section("Hook", payload.ugc_strategy?.hook)}
        ${section("Seedance Prompt", payload.seedance_payload?.prompt)}
        ${renderRawAudit(payload)}
        </div>
      `;
    }

    async function recoverLatestOutput(error) {
      try {
        const response = await fetch("/latest-output", { cache: "no-store" });
        if (!response.ok) return false;
        const payload = await response.json();
        if (!payload || !payload.workflow_sequence) return false;
        renderResult(payload);
        finishProgress(payload);
        statusEl.textContent = "Hotovo z posledniho exportu";
        return true;
      } catch (recoveryError) {
        console.warn("Latest output recovery failed", recoveryError);
        return false;
      }
    }

    function renderRecoveryNotice() {
      return `
        <div class="section">
          <h2>Vysledek obnoven</h2>
          <pre>Prohlizec ztratil spojeni behem dlouheho generovani, ale server stihl ulozit posledni export. Zobrazuji ulozeny vysledek vcetne hotovych obrazku.</pre>
        </div>
      `;
    }

    function metric(name, value, className) {
      return `<div class="metric"><div class="name">${escapeHtml(name)}</div><div class="value ${escapeHtml(className)}">${escapeHtml(String(value))}</div></div>`;
    }

    function section(title, value) {
      const body = typeof value === "string" ? value : JSON.stringify(value || {}, null, 2);
      return `<div class="section"><h2>${escapeHtml(title)}</h2><pre>${escapeHtml(body)}</pre></div>`;
    }

    function workspaceBand(id, title, subtitle, body) {
      if (!body) return "";
      return `
        <section class="workspace-band" id="${escapeHtml(id || "")}">
          <div class="workspace-band-head">
            <div>
              <div class="result-kicker">${escapeHtml(id || "workspace")}</div>
              <h2>${escapeHtml(title)}</h2>
              ${subtitle ? `<p>${escapeHtml(subtitle)}</p>` : ""}
            </div>
          </div>
          ${body}
        </section>
      `;
    }

    function renderOutputHero(payload) {
      const summary = payload.workflow_report?.executive_summary || {};
      const mode = summary.generation_mode || document.getElementById("generation_mode")?.value || "both";
      const productName = summary.product_name || payload.product_analysis?.product_name || "Produkt";
      const category = summary.product_category || payload.ads_creative_set?.selected_product_category || "auto";
      const promptStatus = payload.content_prompt_package?.prompt_generation?.status || "unknown";
      const staticPrompt = payload.ads_creative_set?.static_prompt_generation || {};
      const cost = payload.session_cost_summary?.total_known_cost_display || summary.known_cost || "unknown";
      const staticStatus = payload.static_image_generation?.image_generation_status || "unknown";
      const videoStatus = payload.video_generation?.video_generation_status || "unknown";
      return `
        <div class="output-hero">
          <div class="section">
            <div class="result-kicker">Campaign output</div>
            <h2 class="output-title">${escapeHtml(productName)}</h2>
            <p class="output-subtitle">Vysledek je serazeny podle toho, co se da hned posoudit: nahledy obrazku, ads creative set, duvody generovani a az potom technicky audit.</p>
            <div class="pill-row">
              <span class="pill">${escapeHtml(mode)}</span>
              <span class="pill">${escapeHtml(category)}</span>
              <span class="pill">${escapeHtml(summary.platform || "platform")}</span>
              <span class="pill">${escapeHtml(summary.market || "market")}</span>
              <span class="pill">${escapeHtml(summary.language || "language")}</span>
            </div>
          </div>
          <div class="section">
            <div class="result-kicker">Session status</div>
            <div class="info-table">
              ${infoRows([
                ["Cena", cost],
                ["UGC prompt", promptStatus],
                ["Static prompt model", staticPrompt.status || "unknown"],
                ["Obrazky", staticStatus],
                ["Video", videoStatus],
                ["Slozka", summary.session_folder || ""]
              ])}
            </div>
          </div>
        </div>
      `;
    }

    function renderTopImagePreview(imageGeneration) {
      const assets = imageGeneration?.image_assets || [];
      const status = imageGeneration?.image_generation_status || "unknown";
      const reason = imageGeneration?.failure_reason || imageGeneration?.error || imageGeneration?.next_step || "";
      const generated = assets.slice(0, 6);
      return `
        <div class="section">
          <h2>Nahledy vygenerovanych obrazku</h2>
          <div class="creative-copy"><b>Status:</b> ${escapeHtml(status)} | <b>API requesty:</b> ${escapeHtml(String(imageGeneration?.api_request_count ?? 0))} | <b>Vybrano:</b> ${escapeHtml(String(imageGeneration?.selected_creative_count ?? 0))}</div>
          ${generated.length ? `
            <div class="preview-grid">
              ${generated.map((asset) => `
                <a class="preview-card" href="${escapeHtml(asset.image_url || "#")}" target="_blank">
                  <img src="${escapeHtml(asset.image_url || "")}" alt="${escapeHtml(asset.creative_id || "creative")}">
                  <div class="preview-meta">
                    <strong>${escapeHtml(asset.creative_id || "creative")}</strong>
                    ${escapeHtml(asset.set_id || "")} ${escapeHtml(asset.angle || "")} | ${escapeHtml(asset.asset_type || "")}
                  </div>
                </a>
              `).join("")}
            </div>
          ` : `
            <div class="preview-empty">
              Zatim tu nejsou zadne hotove obrazky. ${escapeHtml(reason || "Duvod najdes v sekci stav obrazku a v prompt model auditu.")}
            </div>
          `}
        </div>
      `;
    }

    function renderProviderValidation(validation) {
      if (!validation) return "";
      const checks = validation.checks || [];
      return `
        <div class="section">
          <h2>Provider capability validation</h2>
          <div class="creative-copy"><b>Status:</b> ${escapeHtml(validation.status || "unknown")}${validation.reason ? ` | <b>Duvod:</b> ${escapeHtml(validation.reason)}` : ""}</div>
          <div class="stage-list">
            ${checks.map((check) => `
              <div class="stage-card">
                <span class="status-chip ${statusClass(check.status)}">${escapeHtml(check.status || "unknown")}</span>
                <h3>${escapeHtml(check.id || "check")}</h3>
                <p>${escapeHtml(check.reason || "")}</p>
                ${check.next_step ? `<p><b>Dalsi krok:</b> ${escapeHtml(check.next_step)}</p>` : ""}
              </div>
            `).join("")}
          </div>
        </div>
      `;
    }

    function renderProductUnderstanding(productAnalysis) {
      const understanding = productAnalysis?.automatic_product_understanding || {};
      if (!Object.keys(understanding).length) return "";
      const chips = [
        ["Category", understanding.category],
        ["Material", understanding.material],
        ["Position", understanding.market_position],
        ["Season", understanding.season],
        ["Style", understanding.fashion_style || understanding.style]
      ];
      return `
        <div class="section">
          <h2>Automatic product understanding</h2>
          <div class="creative-copy"><b>Source:</b> ${escapeHtml(understanding.source || "fallback")} | <b>AI refine:</b> ${escapeHtml(understanding.ai_refinement?.status || "skipped")}</div>
          <div class="report-grid">
            ${chips.map(([label, value]) => reportCard(label, value || "unknown", [], "pass")).join("")}
          </div>
          <div class="creative-copy"><b>Audience:</b> ${escapeHtml(understanding.target_audience || "")}</div>
          <div class="creative-copy"><b>Usage contexts:</b> ${escapeHtml((understanding.usage_contexts || []).join(", "))}</div>
          <details class="audit-details">
            <summary>Category prompt rules and creative implications</summary>
            <pre>${escapeHtml(JSON.stringify({
              category_specific_prompt_rules: understanding.category_specific_prompt_rules || [],
              creative_implications: understanding.creative_implications || [],
              prompt_grounding_details: understanding.prompt_grounding_details || []
            }, null, 2))}</pre>
          </details>
        </div>
      `;
    }

    function renderPromptAuditPanel(audit) {
      if (!audit) return "";
      const ugc = audit.ugc_prompt || {};
      const stat = audit.static_prompt || {};
      const finalImagePrompts = stat.final_image_prompts || {};
      const firstImageKey = Object.keys(finalImagePrompts)[0];
      const firstImagePrompt = firstImageKey ? finalImagePrompts[firstImageKey] : "";
      return `
        <div class="section">
          <h2>Prompt audit panel</h2>
          <div class="report-grid">
            ${reportCard("UGC Prompt", ugc.source_label || "unknown", [
              ["Requested", ugc.requested_model || ""],
              ["Used", ugc.used_model || ""],
              ["Status", ugc.status || ""],
              ["Fallback", ugc.fallback_used ? "ano" : "ne"]
            ], ugc.fallback_used ? "warning" : "pass")}
            ${reportCard("Static Prompt", stat.source_label || "unknown", [
              ["Requested", stat.requested_model || ""],
              ["Used", stat.used_model || ""],
              ["Status", stat.status || ""],
              ["Fallback", stat.fallback_used ? "ano" : "ne"]
            ], stat.fallback_used ? "warning" : "pass")}
            ${reportCard("Structured V2", audit.structured_prompt_v2?.architecture || "not available", [
              ["Scenes", audit.structured_prompt_v2?.scene_count ?? ""],
              ["Compiled chars", audit.structured_prompt_v2?.compiled_prompt_chars ?? ""],
              ["Final chars", audit.structured_prompt_v2?.final_prompt_chars ?? ""],
              ["Limit", audit.structured_prompt_v2?.prompt_size_guard?.hard_limit ?? ""]
            ], audit.structured_prompt_v2?.available ? "pass" : "warning")}
            ${reportCard("Compression", audit.prompt_compression?.fit_strategy || `${audit.prompt_compression?.reduction_percent ?? 0}% saved`, [
              ["Before", audit.prompt_compression?.chars_before ?? ""],
              ["After", audit.prompt_compression?.chars_after ?? ""],
              ["Final", audit.prompt_compression?.chars_provider_final ?? ""],
              ["Saved", audit.prompt_compression?.chars_saved ?? ""]
            ], audit.prompt_compression?.status === "completed" ? "pass" : "warning")}
          </div>
          ${ugc.error ? `<pre>${escapeHtml(ugc.error)}</pre>` : ""}
          ${stat.error ? `<pre>${escapeHtml(stat.error)}</pre>` : ""}
          <details class="audit-details">
            <summary>UGC diff: deterministic -> AI refined -> final payload</summary>
            <div class="grid">
              ${promptBlock("Deterministic video prompt", ugc.deterministic_prompt)}
              ${promptBlock("AI refined video prompt", ugc.ai_refined_prompt)}
            </div>
            ${promptBlock("Final Seedance payload prompt", ugc.final_payload_prompt)}
            ${promptBlock("Diff deterministic -> AI", ugc.diff?.deterministic_to_ai_refined?.unified_diff_preview)}
            ${promptBlock("Diff AI -> final", ugc.diff?.ai_refined_to_final_payload?.unified_diff_preview)}
          </details>
          <details class="audit-details">
            <summary>Static image prompts: deterministic -> AI refined -> final image prompt</summary>
            ${promptMapBlock("Deterministic static prompts", stat.deterministic_prompts)}
            ${promptMapBlock("AI refined static prompts", stat.ai_refined_prompts)}
            ${promptMapBlock("Final image prompts", stat.final_image_prompts)}
            ${firstImagePrompt ? promptBlock(`First final image prompt (${firstImageKey})`, firstImagePrompt) : ""}
          </details>
        </div>
      `;
    }

    function renderSelfCritique(critique) {
      if (!critique) return "";
      return `
        <div class="section">
          <h2>AI Self Critique</h2>
          <div class="report-grid">
            ${reportCard("Scroll stopping", String(critique.scroll_stopping_score ?? "-"), [], scoreClass(critique.scroll_stopping_score))}
            ${reportCard("Realism", String(critique.realism_score ?? "-"), [], scoreClass(critique.realism_score))}
            ${reportCard("Policy risk", String(critique.ad_policy_risk_score ?? "-"), [], (critique.ad_policy_risk_score || 0) > 45 ? "warning" : "pass")}
            ${reportCard("Hook strength", String(critique.hook_strength_score ?? "-"), [], scoreClass(critique.hook_strength_score))}
            ${reportCard("Product clarity", String(critique.product_clarity_score ?? "-"), [], scoreClass(critique.product_clarity_score))}
          </div>
          <div class="creative-copy"><b>Source:</b> ${escapeHtml(critique.source || "unknown")} | <b>AI:</b> ${escapeHtml(critique.ai_critique?.status || "unknown")} | <b>Regenerace doporucena:</b> ${critique.regeneration_recommended ? "ano" : "ne"}</div>
          <details class="audit-details">
            <summary>Duvody a doporuceni</summary>
            <pre>${escapeHtml(JSON.stringify({
              regeneration_reasons: critique.regeneration_reasons || [],
              recommended_changes: critique.recommended_changes || [],
              reviewed_assets: critique.reviewed_assets || {}
            }, null, 2))}</pre>
          </details>
        </div>
      `;
    }

    function renderCreativeMemory(memory) {
      if (!memory) return "";
      const guidance = memory.rag_guidance || {};
      const creatives = memory.creatives || [];
      return `
        <div class="section">
          <h2>Creative Intelligence</h2>
          <div class="report-grid">
            ${reportCard("Memory status", memory.status || "unknown", [
              ["Product", memory.product_id || ""],
              ["Campaign", memory.campaign_id || ""],
              ["Creatives", memory.creative_count ?? ""]
            ], memory.status === "saved" ? "pass" : "warning")}
            ${reportCard("RAG guidance", guidance.status || "unknown", [
              ["Winners", guidance.matching_winner_count ?? 0],
              ["Rejected", guidance.matching_rejected_count ?? 0],
              ["Storage", guidance.storage || ""]
            ], "pass")}
          </div>
          <div class="creative-copy"><b>Prompt recommendations:</b> ${escapeHtml(guidance.prompt_guidance || "Zatim nejsou historicka data. Ohodnot vystupy a dalsi generace se zacne ucit.")}</div>
          <div class="pill-row">
            ${(guidance.winning_patterns || []).slice(0, 8).map((item) => `<span class="pill">Prefer: ${escapeHtml(item)}</span>`).join("")}
            ${(guidance.avoid_patterns || []).slice(0, 8).map((item) => `<span class="pill">Avoid: ${escapeHtml(item)}</span>`).join("")}
          </div>
          ${creatives.length ? `
            <h3>Hodnoceni creative</h3>
            <div class="rating-grid">
              ${creatives.slice(0, 10).map(renderRatingCard).join("")}
            </div>
          ` : ""}
          <details class="audit-details">
            <summary>Creative memory schema</summary>
            <pre>${escapeHtml(JSON.stringify(memory.schema || {}, null, 2))}</pre>
          </details>
        </div>
      `;
    }

    function renderCreativeIntelligenceOverview(summary) {
      const counts = summary?.counts || {};
      const knowledge = summary?.knowledge_base || {};
      const recommendations = summary?.prompt_recommendations || [];
      return `
        <h2>Creative Intelligence</h2>
        <div class="report-grid">
          ${reportCard("Knowledge base", knowledge.status || "active", [
            ["Products", counts.products ?? 0],
            ["Creatives", counts.creatives ?? 0],
            ["Knowledge items", knowledge.item_count ?? 0]
          ], "pass")}
          ${reportCard("Learning loop", counts.ratings ? "learning" : "needs ratings", [
            ["Ratings", counts.ratings ?? 0],
            ["Performance", counts.performance_records ?? 0],
            ["DB", summary?.db_path || ""]
          ], counts.ratings ? "pass" : "warning")}
        </div>
        <div class="pill-row">
          ${(summary?.best_hooks || []).slice(0, 8).map((item) => `<span class="pill">Best: ${escapeHtml(item)}</span>`).join("")}
          ${(summary?.rejected_patterns || []).slice(0, 8).map((item) => `<span class="pill">Avoid: ${escapeHtml(item)}</span>`).join("")}
        </div>
        <div class="creative-copy"><b>Prompt recommendations:</b> ${escapeHtml(recommendations.join(" "))}</div>
        <div class="creative-copy"><b>Learning loop:</b> ${escapeHtml(summary?.learning_loop?.status || "collecting_feedback")} | <b>Prompt learner:</b> ${escapeHtml(summary?.prompt_learning_agent?.confidence || "low")} confidence</div>
        <details class="audit-details">
          <summary>Recent memory records</summary>
          <pre>${escapeHtml(JSON.stringify({
            learning_loop: summary?.learning_loop || {},
            winning_pattern_extractor: summary?.winning_pattern_extractor || {},
            prompt_learning_agent: summary?.prompt_learning_agent || {},
            best_performing_angles: summary?.best_performing_angles || [],
            best_product_categories: summary?.best_product_categories || [],
            market_specific_insights: summary?.market_specific_insights || [],
            recent_creatives: summary?.recent_creatives || [],
            performance_leaders: summary?.performance_leaders || []
          }, null, 2))}</pre>
        </details>
        <div id="memoryGuidancePreview" class="preview-empty">Vypln brief a tady uvidis, co pamet doporuci pro dalsi generaci.</div>
      `;
    }

    async function loadCreativeIntelligenceOverview() {
      const target = document.getElementById("creativeIntelligenceOverview");
      if (!target) return;
      try {
        const response = await fetch("/creative-intelligence", { cache: "no-store" });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const summary = await response.json();
        target.innerHTML = renderCreativeIntelligenceOverview(summary);
        updateDashboardStats(summary);
        loadCreativeGuidancePreview();
      } catch (error) {
        target.innerHTML = `
          <h2>Creative Intelligence</h2>
          <div class="creative-copy">Znalostni baza zatim neni dostupna: ${escapeHtml(String(error.message || error))}</div>
        `;
      }
    }

    function updateDashboardStats(summary) {
      const counts = summary?.counts || {};
      const leaders = summary?.performance_leaders || [];
      const hooks = summary?.best_hooks || [];
      const setText = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
      };
      setText("dashCreatives", String(counts.creatives ?? 0));
      const bestCtr = leaders.find((item) => item.CTR || item.ctr || item.metric === "CTR");
      setText("dashCtr", bestCtr ? String(bestCtr.CTR || bestCtr.ctr || bestCtr.value) : "Need data");
      setText("dashCost", counts.generation_cost ? `$${Number(counts.generation_cost).toFixed(2)}` : "$0.00");
      const hookEl = document.getElementById("dashBestHook");
      if (hookEl && hooks.length) hookEl.textContent = hooks[0].slice(0, 18);
    }

    function scheduleMemoryPreview() {
      clearTimeout(memoryPreviewTimer);
      memoryPreviewTimer = setTimeout(loadCreativeGuidancePreview, 350);
    }

    async function loadCreativeGuidancePreview() {
      const target = document.getElementById("memoryGuidancePreview");
      if (!target) return;
      const payload = {
        product_name: document.getElementById("product_name")?.value || "",
        product_info: document.getElementById("product_info")?.value || "",
        product_category: document.getElementById("product_category")?.value || "auto",
        platform: document.getElementById("platform")?.value || "meta",
        market: document.getElementById("market")?.value || "UK",
        language: document.getElementById("language")?.value || "en"
      };
      try {
        const response = await fetch("/creative-intelligence-preview", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payload)
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const preview = await response.json();
        target.outerHTML = renderMemoryGuidancePreview(preview);
      } catch (error) {
        target.innerHTML = `Memory preview neni dostupny: ${escapeHtml(String(error.message || error))}`;
      }
    }

    function renderMemoryGuidancePreview(preview) {
      const guidance = preview?.next_generation_guidance || {};
      const winners = guidance.winning_patterns || [];
      const avoid = guidance.avoid_patterns || [];
      return `
        <div id="memoryGuidancePreview" class="preview-empty">
          <div class="creative-copy"><b>Live guidance pro dalsi generaci:</b> ${escapeHtml(guidance.prompt_guidance || "Zatim nejsou potvrzene winners/rejects pro tento brief.")}</div>
          <div class="pill-row">
            <span class="pill">${escapeHtml(preview.detected_category || "unknown")}</span>
            <span class="pill">${escapeHtml(preview.platform || "platform")}</span>
            <span class="pill">${escapeHtml(preview.market || "market")}</span>
            <span class="pill">confidence: ${escapeHtml(guidance.confidence || "low")}</span>
          </div>
          <div class="pill-row">
            ${winners.slice(0, 8).map((item) => `<span class="pill">Prefer: ${escapeHtml(item)}</span>`).join("")}
            ${avoid.slice(0, 8).map((item) => `<span class="pill">Avoid: ${escapeHtml(item)}</span>`).join("")}
          </div>
        </div>
      `;
    }

    function renderRatingCard(creative) {
      const id = creative.creative_id || "";
      const safeId = domId(id);
      return `
        <div class="rating-card" data-creative-id="${escapeHtml(id)}">
          <div class="creative-card-title">
            <div>
              <div class="set-id">${escapeHtml(creative.set_id || "C?")}</div>
              <div class="set-name">${escapeHtml(creative.type || "creative")} | ${escapeHtml(creative.angle || "angle")}</div>
            </div>
            <span class="pill">${escapeHtml(creative.status || "saved")}</span>
          </div>
          ${ratingSelect(safeId, "fidelity_score", "Product fidelity")}
          ${ratingSelect(safeId, "realism_score", "Realism")}
          ${ratingSelect(safeId, "hook_score", "Hook strength")}
          ${ratingSelect(safeId, "brand_fit_score", "Brand fit")}
          ${ratingSelect(safeId, "user_rating", "Overall")}
          <div class="rating-reasons">
            ${ratingReason(safeId, "produkt neni presny", "produkt neni presny")}
            ${ratingReason(safeId, "spatny oblicej avatara", "spatny oblicej avatara")}
            ${ratingReason(safeId, "moc AI vzhled", "moc AI vzhled")}
            ${ratingReason(safeId, "slaby hook", "slaby hook")}
            ${ratingReason(safeId, "spatne prostredi", "spatne prostredi")}
            ${ratingReason(safeId, "jine", "jine")}
          </div>
          <label for="${safeId}_comment">Co se ti nelibi?</label>
          <textarea id="${safeId}_comment" rows="3" placeholder="kratka poznamka k creative"></textarea>
          <details class="audit-details">
            <summary>Import performance dat</summary>
            <div class="grid">
              <input id="${safeId}_ctr" placeholder="CTR">
              <input id="${safeId}_cpc" placeholder="CPC">
              <input id="${safeId}_cpa" placeholder="CPA">
              <input id="${safeId}_roas" placeholder="ROAS">
              <input id="${safeId}_spend" placeholder="Spend">
              <input id="${safeId}_impressions" placeholder="Impressions">
              <input id="${safeId}_clicks" placeholder="Clicks">
              <input id="${safeId}_conversions" placeholder="Conversions">
            </div>
            <input id="${safeId}_date_range" placeholder="Date range, napr. 2026-05-01 to 2026-05-14">
            <button type="button" onclick="submitPerformanceImport('${escapeAttr(id)}')">Ulozit performance</button>
          </details>
          <div class="rating-actions">
            <button type="button" onclick="submitCreativeRating('${escapeAttr(id)}','approved')">Approve</button>
            <button type="button" class="reject" onclick="submitCreativeRating('${escapeAttr(id)}','rejected')">Reject</button>
            <button type="button" class="regen" onclick="submitCreativeRating('${escapeAttr(id)}','rated')">Regenerate note</button>
          </div>
          <div class="hint" id="${safeId}_status"></div>
        </div>
      `;
    }

    function ratingSelect(prefix, key, label) {
      return `
        <div class="rating-row">
          <span>${escapeHtml(label)}</span>
          <select id="${prefix}_${key}">
            <option value="5">★★★★★</option>
            <option value="4">★★★★</option>
            <option value="3">★★★</option>
            <option value="2">★★</option>
            <option value="1">★</option>
          </select>
        </div>
      `;
    }

    function ratingReason(prefix, value, label) {
      const id = `${prefix}_reason_${domId(value)}`;
      return `<label for="${id}"><input id="${id}" data-rating-reason="${prefix}" type="checkbox" value="${escapeAttr(value)}">${escapeHtml(label)}</label>`;
    }

    async function submitCreativeRating(creativeId, status) {
      const prefix = domId(creativeId);
      const reasons = Array.from(document.querySelectorAll(`[data-rating-reason="${prefix}"]:checked`)).map((item) => item.value);
      const payload = {
        creative_id: creativeId,
        status,
        user_rating: Number(document.getElementById(`${prefix}_user_rating`)?.value || 0),
        fidelity_score: Number(document.getElementById(`${prefix}_fidelity_score`)?.value || 0),
        realism_score: Number(document.getElementById(`${prefix}_realism_score`)?.value || 0),
        hook_score: Number(document.getElementById(`${prefix}_hook_score`)?.value || 0),
        brand_fit_score: Number(document.getElementById(`${prefix}_brand_fit_score`)?.value || 0),
        comment: document.getElementById(`${prefix}_comment`)?.value || "",
        reasons
      };
      const target = document.getElementById(`${prefix}_status`);
      if (target) target.textContent = "Ukladam hodnoceni...";
      try {
        const response = await fetch("/creative-rating", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payload)
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Rating save failed");
        if (target) target.textContent = `Ulozeno jako ${status}. Pri dalsi generaci se to pouzije v Creative Intelligence.`;
        loadCreativeIntelligenceOverview();
      } catch (error) {
        if (target) target.textContent = `Chyba: ${String(error.message || error)}`;
      }
    }

    async function submitPerformanceImport(creativeId) {
      const prefix = domId(creativeId);
      const target = document.getElementById(`${prefix}_status`);
      const payload = {
        creative_id: creativeId,
        ctr: document.getElementById(`${prefix}_ctr`)?.value || null,
        cpc: document.getElementById(`${prefix}_cpc`)?.value || null,
        cpa: document.getElementById(`${prefix}_cpa`)?.value || null,
        roas: document.getElementById(`${prefix}_roas`)?.value || null,
        spend: document.getElementById(`${prefix}_spend`)?.value || null,
        impressions: document.getElementById(`${prefix}_impressions`)?.value || null,
        clicks: document.getElementById(`${prefix}_clicks`)?.value || null,
        conversions: document.getElementById(`${prefix}_conversions`)?.value || null,
        date_range: document.getElementById(`${prefix}_date_range`)?.value || "",
      };
      if (target) target.textContent = "Ukladam performance...";
      try {
        const response = await fetch("/performance-import", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payload)
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Performance import failed");
        if (target) target.textContent = "Performance ulozena. RAG ji pouzije pro dalsi generaci.";
        loadCreativeIntelligenceOverview();
      } catch (error) {
        if (target) target.textContent = `Chyba: ${String(error.message || error)}`;
      }
    }

    function scoreClass(value) {
      const score = Number(value || 0);
      if (score >= 85) return "pass";
      if (score >= 70) return "warning";
      return "fail";
    }

    function promptBlock(title, value) {
      return `<div class="section"><h2>${escapeHtml(title)}</h2><pre>${escapeHtml(value || "")}</pre></div>`;
    }

    function promptMapBlock(title, map) {
      const rows = Object.entries(map || {}).map(([key, value]) => `${key}\n${value}`).join("\\n\\n---\\n\\n");
      return promptBlock(title, rows);
    }

    function renderCreativePlanPreview(preview) {
      const items = preview?.items || [];
      if (!items.length) return "";
      return `
        <div class="section">
          <h2>Creative plan preview</h2>
          <div class="creative-copy"><b>Pred/po generaci:</b> tady je jasne, ktere C-sety jsou v teto session vybrane, preskocene nebo blokovane. Limit obrazku je cap, ne pozadavek na doplneni duplicit.</div>
          <div class="creative-board">
            ${items.map((item) => {
              const cls = item.status === "YES" ? "generated" : item.status === "BLOCKED" ? "skipped" : "skipped";
              return `
                <div class="creative-set-card ${cls}">
                  <div class="creative-card-title">
                    <div>
                      <div class="set-id">${escapeHtml(item.set_id || "C?")}</div>
                      <div class="set-name">${escapeHtml(item.creative_type || "")}</div>
                    </div>
                    <span class="pill">${escapeHtml(item.status || "unknown")}</span>
                  </div>
                  <div class="pill-row">
                    <span class="pill">${escapeHtml(item.angle || "")}</span>
                    <span class="pill">${escapeHtml(item.aspect_ratio || "")}</span>
                    <span class="pill">${escapeHtml(String(item.budget_share_percent ?? ""))}%</span>
                  </div>
                  <div class="set-purpose">${escapeHtml(item.reason || "")}</div>
                </div>
              `;
            }).join("")}
          </div>
        </div>
      `;
    }

    function renderCreativeBrain(ugcStrategy) {
      if (!ugcStrategy) return "";
      const audience = ugcStrategy.audience_research || {};
      const emotional = ugcStrategy.emotional_angle || {};
      const psychology = ugcStrategy.creative_psychology || {};
      const voice = ugcStrategy.voice_personality || {};
      const hook = ugcStrategy.hook_strategy || {};
      const scene = ugcStrategy.scene_direction || {};
      const chaining = ugcStrategy.scene_chaining || {};
      const memory = ugcStrategy.performance_insights || {};
      if (!audience.primary_archetype && !psychology.primary_driver) return "";
      return `
        <div class="section">
          <h2>Multi-Agent Creative Brain</h2>
          <div class="report-grid">
            ${reportCard("Audience", audience.primary_archetype || "unknown", [
              ["Secondary", (audience.secondary_archetypes || []).join(", ")],
              ["Triggers", (audience.decision_triggers || []).slice(0, 3).join(" | ")],
              ["Objections", (audience.objections || []).slice(0, 2).join(" | ")]
            ], audience.primary_archetype ? "pass" : "warning")}
            ${reportCard("Psychology", psychology.primary_driver || "driver", [
              ["Curve", psychology.behavior_tree?.emotional_curve || ""],
              ["Sequence", (psychology.behavior_tree?.sequence || []).join(" -> ")]
            ], psychology.primary_driver ? "pass" : "warning")}
            ${reportCard("Emotional Angle", emotional.primary_safe_label || emotional.primary_angle || "angle", [
              ["Driver", emotional.driver || ""],
              ["Secondary", (emotional.secondary_angles || []).join(", ")]
            ], emotional.primary_angle ? "pass" : "warning")}
            ${reportCard("Voice", voice.creator_style || "creator style", [
              ["Tone", voice.tone || ""],
              ["Energy", voice.energy || ""],
              ["Accent", voice.accent_profile || ""],
              ["Gestures", voice.gesture_style || ""]
            ], voice.creator_style ? "pass" : "warning")}
            ${reportCard("Hook", hook.selected_pattern || "pattern", [
              ["Selected", hook.selected_hook || ugcStrategy.hook || ""],
              ["Bank", String((hook.hook_bank || []).length)]
            ], hook.selected_hook ? "pass" : "warning")}
            ${reportCard("Memory", `${memory.matching_record_count || 0} records`, [
              ["Winners", memory.winner_count || 0],
              ["Hooks", (memory.winning_hooks || []).join(" | ")],
              ["Shots", (memory.winning_shot_types || []).join(" | ")]
            ], "pass")}
          </div>
          <details class="audit-details">
            <summary>Scene Director plan</summary>
            <pre>${escapeHtml((scene.directed_scenes || []).map((item, index) => `${index + 1}. ${item.purpose} | ${item.shot_type}\\n${item.visual}\\nOverlay: ${item.overlay}`).join("\\n\\n"))}</pre>
          </details>
          <details class="audit-details">
            <summary>True Scene Chaining</summary>
            <pre>${escapeHtml(JSON.stringify(chaining, null, 2))}</pre>
          </details>
        </div>
      `;
    }

    function renderAdsCreativeSetBoard(adsCreativeSet, imageGeneration = {}, videoGeneration = {}) {
      const plan = adsCreativeSet?.creative_plan || [];
      const assets = imageGeneration?.image_assets || [];
      if (!plan.length) return "";
      const staticPrompt = adsCreativeSet?.static_prompt_generation || {};
      const cards = plan.map((item) => creativeBoardCard(item, adsCreativeSet, imageGeneration, videoGeneration, assets)).join("");
      return `
        <div class="section">
          <h2>Ads creative set</h2>
          <div class="creative-copy"><b>Logika:</b> C1 je UGC video anchor, C2 PRODUCT HERO ukaze produkt okamzite a ciste, C3 USE CONTEXT prida realny moment pouziti, C4 DETAIL PROOF ukaze viditelny dukaz a C5 BUYING GUIDE rozlozi vyber do karet. Kdyz je limit obrazku nizsi, generuje se jen vybrany vysek planu.</div>
          <div class="creative-copy"><b>Static prompt model:</b> ${escapeHtml(staticPrompt.model || "n/a")} | ${escapeHtml(staticPrompt.status || "unknown")}${staticPrompt.error ? ` | ${escapeHtml(staticPrompt.error)}` : ""}</div>
          <div class="creative-board">${cards}</div>
        </div>
      `;
    }

    function creativeBoardCard(item, adsCreativeSet, imageGeneration, videoGeneration, assets) {
      const setId = item.set_id || "";
      const detail = creativePlanDetail(adsCreativeSet, item);
      const selected = setId === "C1"
        ? !videoGeneration?.skipped_by_generation_mode
        : (imageGeneration?.generation_plan || []).some((entry) => entry.set_id === setId);
      const generatedAssets = assets.filter((asset) => asset.set_id === setId);
      const status = generatedAssets.length ? "generated" : selected ? "selected" : "skipped";
      const generatedLabel = generatedAssets.length
        ? `${generatedAssets.length} hotovo`
        : selected ? "vybrano" : "mimo aktualni limit";
      return `
        <div class="creative-set-card ${status}">
          <div class="creative-card-title">
            <div>
              <div class="set-id">${escapeHtml(setId || item.creative_id || "C?")}</div>
              <div class="set-name">${escapeHtml(item.creative_type || item.generation_target || "creative")}</div>
            </div>
            <span class="pill">${escapeHtml(generatedLabel)}</span>
          </div>
          <div class="pill-row">
            <span class="pill">${escapeHtml(item.angle || "UGC")}</span>
            <span class="pill">${escapeHtml(item.funnel_stage || "stage")}</span>
            <span class="pill">${escapeHtml(String(item.budget_share_percent || ""))}%</span>
          </div>
          <div class="set-purpose">${escapeHtml(detail.purpose || item.notes || "")}</div>
          <div class="why-card">
            <b>Why this creative exists</b>
            ${escapeHtml(whyCreativeExists(item, detail))}
          </div>
          <div class="creative-copy"><b>Vystup:</b> ${escapeHtml(detail.output || item.generation_target || "")}</div>
          ${detail.overlay ? `<div class="creative-copy"><b>Overlay:</b> ${escapeHtml(detail.overlay)}</div>` : ""}
          ${detail.cards ? `<div class="creative-copy"><b>Karty:</b> ${escapeHtml(detail.cards)}</div>` : ""}
          ${generatedAssets.length ? `
            <div class="mini-thumb-row">
              ${generatedAssets.slice(0, 2).map((asset) => `<img src="${escapeHtml(asset.image_url || "")}" alt="${escapeHtml(asset.creative_id || "creative")}">`).join("")}
            </div>
          ` : ""}
        </div>
      `;
    }

    function whyCreativeExists(item, detail) {
      const setId = item.set_id || "";
      const angle = String(item.angle || "UGC").toLowerCase();
      const funnel = item.funnel_stage || "campaign";
      if (setId === "C1") {
        return "Creator-led anchor: product visible fast, avatar builds trust, and the video can feed retargeting audiences.";
      }
      if (setId === "C5") {
        return "Education asset: turns product details into a swipeable sequence for people who need more context before deciding.";
      }
      if (angle.includes("pain")) {
        return "Pain angle: stops the scroll by naming a buying doubt, then resolves it with visible product detail.";
      }
      if (angle.includes("identity")) {
        return "Identity angle: shows lifestyle fit and helps the audience picture the product in their own day.";
      }
      if (angle.includes("demo")) {
        return "Demonstration angle: gives retargeting a clearer reason to return by showing close-up product evidence.";
      }
      return `${funnel}: ${detail.purpose || "supports the campaign with a distinct visual angle."}`;
    }

    function renderWorkflowReport(report) {
      if (!report) return "";
      const summary = report.executive_summary || {};
      const decision = report.decision_state || {};
      const locks = report.identity_and_product_lock || {};
      return `
        <div class="report-hero">
          <span class="status-chip ${statusClass(summary.final_export_status)}">${escapeHtml(summary.final_export_status || "unknown")}</span>
          <h2>Workflow report</h2>
          <p>${escapeHtml(summary.primary_outcome || report.purpose || "Prehled celeho workflow.")}</p>
        </div>
        <div class="report-grid">
          ${reportCard("Brief", summary.product_name || "Produkt", [
            ["Kategorie", `${summary.product_category || "unknown"} (${summary.product_category_source || "auto"})`],
            ["Platforma", `${summary.platform || "unknown"} | ${summary.market || ""} | ${summary.language || ""}`],
            ["Format", `${summary.duration_seconds || "?"}s | ${summary.aspect_ratio || "?"}`],
            ["Rezim", summary.generation_mode || "both"],
            ["Session", summary.session_folder || ""]
          ], summary.final_export_status)}
          ${reportCard("Rozhodnuti", decision.can_use_export ? "Pouzitelny export" : "Vyresit pred pouzitim", [
            ["Blokace", (decision.blocking_reasons || []).length ? `${decision.blocking_reasons.length}` : "0"],
            ["Varovani", (decision.warnings || []).length ? `${decision.warnings.length}` : "0"],
            ["Cena", `${summary.known_cost || "unknown"} (${summary.cost_status || "unknown"})`]
          ], decision.can_use_export ? "pass" : "warning")}
          ${reportCard("Produkt + osoba", locks.product_reference?.strict_fidelity_present ? "Reference locked" : "Zkontrolovat reference", [
            ["Produkt", locks.product_reference?.path_or_url || ""],
            ["Avatar", locks.avatar_reference?.identity_contract?.identity_mode || "unknown"],
            ["Wardrobe", locks.avatar_reference?.identity_contract?.wardrobe_policy || "unknown"],
            ["Category prompt", locks.category_prompt?.selected_category || ""]
          ], locks.product_reference?.strict_fidelity_present ? "pass" : "warning")}
        </div>
        ${renderDecisionLists(decision)}
        ${renderDeliverables(report.deliverables)}
        ${renderStageList(report.workflow_stages)}
        ${renderPromptPayloadMap(report.prompt_and_payload_map)}
        ${renderRawAuditMap(report.raw_audit_sections)}
      `;
    }

    function reportCard(title, big, rows, status) {
      return `
        <div class="report-card">
          <span class="status-chip ${statusClass(status)}">${escapeHtml(status || "info")}</span>
          <h3>${escapeHtml(title)}</h3>
          <div class="big">${escapeHtml(String(big || ""))}</div>
          <div class="info-table">${infoRows(rows)}</div>
        </div>
      `;
    }

    function infoRows(rows) {
      return (rows || []).map(([label, value]) => `
        <div class="info-row"><span>${escapeHtml(label)}</span><span>${escapeHtml(String(value || ""))}</span></div>
      `).join("");
    }

    function renderDecisionLists(decision) {
      const blockers = decision.blocking_reasons || [];
      const warnings = decision.warnings || [];
      const actions = decision.next_actions || [];
      if (!blockers.length && !warnings.length && !actions.length) return "";
      return `
        <div class="report-grid">
          ${listCard("Blokace", blockers, blockers.length ? "blocked" : "pass", "Nic neblokuje export.")}
          ${listCard("Varovani", warnings, warnings.length ? "warning" : "pass", "Bez varovani.")}
          ${listCard("Dalsi kroky", actions, "pass", "Neni potreba dalsi akce.")}
        </div>
      `;
    }

    function listCard(title, items, status, emptyText) {
      return `
        <div class="report-card">
          <span class="status-chip ${statusClass(status)}">${escapeHtml(status)}</span>
          <h3>${escapeHtml(title)}</h3>
          ${(items || []).length ? `<ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>` : `<p>${escapeHtml(emptyText)}</p>`}
        </div>
      `;
    }

    function renderDeliverables(deliverables) {
      if (!deliverables) return "";
      const video = deliverables.ugc_video || {};
      const images = deliverables.static_images || {};
      const carousel = deliverables.carousel || {};
      const copy = deliverables.ad_copy || {};
      const cost = deliverables.cost || {};
      return `
        <div class="section">
          <h2>Co workflow vyrobil</h2>
          <div class="report-grid">
            ${reportCard("C1 UGC video", video.status || "unknown", [
              ["Job", video.job_id || "none"],
              ["Soubor", video.video_path || "neni"],
              ["Prompt ready", video.prompt_ready ? "ano" : "ne"],
              ["Duvod", video.failure_reason || ""]
            ], video.status)}
            ${reportCard("Staticke obrazky", `${images.generated_count || 0}/${images.planned_count || 0}`, [
              ["Status", images.status || "unknown"],
              ["Vybrano z planu", `${images.planned_count || 0} / ${images.source_creative_count ?? "?"}`],
              ["Mimo limit", images.skipped_count ?? 0],
              ["API requesty", images.api_request_count ?? 0],
              ["Duplicitni skipy", images.duplicate_skips ?? 0],
              ["Duvod", images.failure_reason || ""]
            ], images.status)}
            ${reportCard("C5 Carousel", `${carousel.card_count || 0} karet`, [
              ["Set", carousel.set_id || "C5"],
              ["Cards ready", carousel.cards_ready ? "ano" : "ne"]
            ], carousel.cards_ready ? "pass" : "warning")}
            ${reportCard("Copy + cena", cost.known_total || "unknown", [
              ["Popisy reklam", copy.description_variant_count || 0],
              ["Primary texty", copy.primary_text_variant_count || 0],
              ["Google headlines", copy.google_headline_count || 0],
              ["Nezname costy", (cost.unknown_components || []).join(", ") || "none"]
            ], cost.status)}
          </div>
        </div>
      `;
    }

    function renderStageList(stages) {
      if (!stages || !stages.length) return "";
      return `
        <div class="section">
          <h2>Faze workflow</h2>
          <div class="stage-list">
            ${stages.map((stage) => `
              <div class="stage-card">
                <span class="status-chip ${statusClass(stage.status)}">${escapeHtml(stage.status || "unknown")}</span>
                <h3>${escapeHtml(stage.title || stage.stage_id || "stage")}</h3>
                <p><b>Vstup:</b> ${escapeHtml(stage.input_summary || "")}</p>
                <p><b>Vystup:</b> ${escapeHtml(stage.output_summary || "")}</p>
                <p><b>Detail:</b> ${escapeHtml(stage.inspect_key || "")}</p>
              </div>
            `).join("")}
          </div>
        </div>
      `;
    }

    function renderPromptPayloadMap(map) {
      if (!map) return "";
      const promptModel = map.prompt_model || {};
      const staticPromptModel = map.static_creative_prompt_model || {};
      const videoPayload = map.seedance_video_payload || {};
      const imagePrompts = map.static_image_prompts || {};
      const layers = map.editable_prompt_layers || {};
      return `
        <div class="section">
          <h2>Prompty a payloady</h2>
          <div class="report-grid">
            ${reportCard("Prompt model", promptModel.status || "unknown", [
              ["Model", promptModel.model || ""],
              ["Fallback", promptModel.fallback_used ? "ano" : "ne"],
              ["Error", promptModel.error || ""]
            ], promptModel.status)}
            ${reportCard("Static prompt model", staticPromptModel.status || "unknown", [
              ["Model", staticPromptModel.model || ""],
              ["Fallback", staticPromptModel.fallback_used ? "ano" : "ne"],
              ["Error", staticPromptModel.error || ""]
            ], staticPromptModel.status)}
            ${reportCard("Seedance payload", videoPayload.model || "model", [
              ["Duration", videoPayload.duration || ""],
              ["Aspect", videoPayload.aspect_ratio || ""],
              ["Reference", `${videoPayload.avatar_reference_mode || ""} | ${videoPayload.input_reference_count || 0} refs`],
              ["Resolution", videoPayload.resolution || ""]
            ], "pass")}
            ${reportCard("Image prompts", imagePrompts.model || "model", [
              ["Selected", imagePrompts.selected_creative_count ?? ""],
              ["Source", imagePrompts.source_creative_count ?? ""],
              ["Limit policy", imagePrompts.max_images_policy || ""]
            ], "pass")}
            ${reportCard("Editable layers", layers.category_prompt_present ? "Category on" : "Category off", [
              ["Category prompt", layers.category_prompt_present ? "ano" : "ne"],
              ["Avatar contract", layers.avatar_identity_contract_present ? "ano" : "ne"],
              ["Negative prompt", layers.negative_prompt_overridden ? "nastaven" : "default"]
            ], layers.avatar_identity_contract_present ? "pass" : "warning")}
          </div>
          ${videoPayload.prompt_preview ? `<details class="audit-details"><summary>Seedance prompt preview</summary><pre>${escapeHtml(videoPayload.prompt_preview)}</pre></details>` : ""}
          ${imagePrompts.prompt_contract ? `<details class="audit-details"><summary>Image prompt contract</summary><pre>${escapeHtml(imagePrompts.prompt_contract)}</pre></details>` : ""}
        </div>
      `;
    }

    function renderRawAuditMap(sections) {
      if (!sections || !sections.length) return "";
      return `
        <details class="audit-details">
          <summary>Mapa raw audit sekci</summary>
          <div class="stage-list">
            ${sections.map((item) => `
              <div class="stage-card">
                <h3>${escapeHtml(item.title || item.key || "section")}</h3>
                <p><b>JSON key:</b> ${escapeHtml(item.key || "")}</p>
                <p>${escapeHtml(item.why_it_matters || "")}</p>
              </div>
            `).join("")}
          </div>
        </details>
      `;
    }

    function renderRawAudit(payload) {
      return `
        <details class="audit-details">
          <summary>Raw JSON audit celeho workflow</summary>
          ${section("Analýza produktu", payload.product_analysis)}
          ${section("UGC strategie", payload.ugc_strategy)}
          ${section("Balíček promptů", payload.content_prompt_package)}
          ${section("Ads creative set", payload.ads_creative_set)}
          ${section("Staticke obrazky", payload.static_image_generation)}
          ${section("Video generování", payload.video_generation)}
          ${section("Cena session", payload.session_cost_summary)}
          ${section("Kontroly", {
            product_fidelity_result: payload.product_fidelity_result,
            compliance_result: payload.compliance_result
          })}
        ${section("Kvalita", payload.quality_result)}
          ${section("Provider validace", payload.provider_validation)}
          ${section("Prompt audit", payload.prompt_audit)}
          ${section("Creative plan preview", payload.creative_plan_preview)}
          ${section("Workflow report JSON", payload.workflow_report)}
        </details>
      `;
    }

    function statusClass(value) {
      const status = String(value || "unknown").toLowerCase();
      if (["approved", "pass", "passed", "completed", "complete", "yes"].includes(status)) return "pass";
      if (["blocked", "fail", "failed"].includes(status)) return "blocked";
      if (["warning", "partial", "skipped", "unknown"].includes(status)) return "warning";
      return status;
    }

    function renderAdDescriptionSuggestions(adsCreativeSet) {
      const pack = adsCreativeSet?.ad_description_suggestions || {};
      const variants = pack.variants || [];
      if (!variants.length) return "";
      return `
        <div class="section">
          <h2>Navrhy popisu reklam</h2>
          <pre>${escapeHtml(pack.usage_note || "")}</pre>
          <div class="asset-grid">
            ${variants.map((variant) => `
              <div class="asset-card">
                <div class="asset-meta">
                  <strong>${escapeHtml(variant.variant_id || "description")}</strong>
                  ${escapeHtml(variant.angle || "")} | ${escapeHtml(variant.validation_status || "")}
                </div>
                <pre>${escapeHtml(renderAdDescriptionText(variant))}</pre>
              </div>
            `).join("")}
          </div>
        </div>
      `;
    }

    function renderCreativePlan(adsCreativeSet, imageGeneration = {}, videoGeneration = {}) {
      const plan = adsCreativeSet?.creative_plan || [];
      const selectedImages = imageGeneration?.generation_plan || [];
      const skipped = imageGeneration?.skipped_creatives || [];
      const videoSelected = !videoGeneration?.skipped_by_generation_mode;
      if (!plan.length && !selectedImages.length && !videoSelected) return "";
      const generatedCards = [];
      if (videoSelected) {
        const ugc = adsCreativeSet?.ugc_video_ad || {};
        generatedCards.push({
          creative_id: "C1_ugc_video",
          set_id: "C1",
          creative_type: "UGC video",
          angle: "UGC",
          funnel_stage: ugc.funnel_stage || "TOFU + retargeting",
          aspect_ratio: ugc.aspect_ratio || "",
          status: videoGeneration?.video_generation_status || "ready",
          layout: "Seedance UGC video with avatar, hook, product detail, and closing beat",
          overlay_text: ugc.hook || "",
          visual_prompt: ugc.seedance_prompt || ""
        });
      }
      selectedImages.forEach((item) => generatedCards.push({
        ...item,
        status: imageGeneration?.image_generation_status || "selected"
      }));
      return `
        <div class="section">
          <h2>Vybrane kreativy pro generovani</h2>
          <div class="creative-copy"><b>Co vidis:</b> Jen kreativy, ktere se v teto session opravdu vybraly pro video/image generovani. Full ads plan zustava dole v raw auditu.</div>
          ${imageGeneration?.max_images_policy_note ? `<div class="creative-copy"><b>Limit:</b> ${escapeHtml(imageGeneration.max_images_policy_note)}</div>` : ""}
          ${adsCreativeSet?.selected_product_category ? `<div class="creative-copy"><b>Category layer:</b> ${escapeHtml(adsCreativeSet.selected_product_category)}${adsCreativeSet.category_image_directive ? ` - ${escapeHtml(adsCreativeSet.category_image_directive.slice(0, 220))}` : ""}</div>` : ""}
          <div class="asset-grid">
            ${generatedCards.map((item) => {
              const detail = generatedCreativeDetail(item);
              return `
              <div class="asset-card">
                <div class="asset-meta">
                  <div class="creative-card-title">
                    <strong>${escapeHtml(item.creative_id || item.set_id || "creative")}</strong>
                    <span class="pill">${escapeHtml(item.status || "selected")}</span>
                  </div>
                  <div class="pill-row">
                    <span class="pill">${escapeHtml(item.set_id || "set")}</span>
                    <span class="pill">${escapeHtml(item.angle || "angle")}</span>
                    <span class="pill">${escapeHtml(item.asset_type || item.creative_type || "asset")}</span>
                    <span class="pill">${escapeHtml(item.aspect_ratio || "ratio")}</span>
                  </div>
                  <div class="creative-copy"><b>Proc se generuje:</b> ${escapeHtml(detail.purpose)}</div>
                  <div class="creative-copy"><b>Co se generuje:</b> ${escapeHtml(detail.output)}</div>
                  ${detail.overlay ? `<div class="creative-copy"><b>Overlay:</b> ${escapeHtml(detail.overlay)}</div>` : ""}
                </div>
                ${detail.prompt ? `<pre class="prompt-preview">${escapeHtml(detail.prompt)}</pre>` : ""}
              </div>
            `;
            }).join("")}
          </div>
          ${skipped.length ? `
            <details>
              <summary>Kreativy mimo generovani (${skipped.length})</summary>
              <pre>${escapeHtml(skipped.map((item) => `${item.creative_id || item.asset_type} | ${item.set_id || ""} | ${item.reason || ""}`).join("\\n"))}</pre>
            </details>
          ` : ""}
        </div>
      `;
    }

    function generatedCreativeDetail(item) {
      if ((item.set_id || "") === "C1") {
        return {
          purpose: "Video bylo zvolene v rezimu generovani.",
          output: item.layout || "Seedance UGC video",
          overlay: item.overlay_text || "",
          prompt: item.visual_prompt || ""
        };
      }
      return {
        purpose: "Tahle image kreativa je ve vyberu image generation planu a pocita se do limitu.",
        output: `${item.format || item.asset_type || "Image creative"}: ${item.layout || ""}`,
        overlay: item.overlay_text || "",
        prompt: item.prompt_preview || item.visual_prompt || ""
      };
    }

    function creativePlanDetail(adsCreativeSet, item) {
      const setId = item.set_id || "";
      const staticItem = (adsCreativeSet?.static_image_ads || []).find((entry) => entry.set_id === setId) || {};
      const carousel = adsCreativeSet?.carousel_ad || {};
      const ugc = adsCreativeSet?.ugc_video_ad || {};
      if (setId === "C1") {
        return {
          purpose: "Hlavni creator-led video pro rychle pochopeni produktu a retargeting anchor.",
          output: "Seedance UGC video s avatarem, hookem, product detailem a zaverecnym beatem bez tlacitka.",
          overlay: ugc.hook || "",
          prompt: ugc.seedance_prompt || item.notes || ""
        };
      }
      if (setId === "C5") {
        const cardLabels = (carousel.cards || [])
          .map((card) => `${card.card_number}: ${card.overlay_text}`)
          .join(" | ");
        return {
          purpose: "MOFU edukace: rozdelit produktove detaily do kratkeho swipe flow.",
          output: `${carousel.card_count || (carousel.cards || []).length || 5} samostatnych 1:1 carousel karet.`,
          cards: cardLabels,
          prompt: (carousel.cards || []).map((card) => `${card.card_number}. ${card.visual_prompt}`).join("\\n\\n")
        };
      }
      const fallbackPurpose = item.notes || "Podpurna kreativni varianta v ramci ads setu.";
      return {
        purpose: purposeForStaticSet(setId, fallbackPurpose),
        output: `${staticItem.format || item.generation_target || "Static image"}: ${staticItem.layout || item.notes || ""}`,
        overlay: staticItem.overlay_text || "",
        prompt: staticItem.visual_prompt || item.notes || ""
      };
    }

    function purposeForStaticSet(setId, fallback) {
      const purposes = {
        C2: "PRODUCT HERO creative: okamzite ukazat produkt, tvar, meritko a jeden viditelny duvod ke kliknuti.",
        C3: "USE CONTEXT creative: ukazat produkt v realnem momentu pouziti, outfitu nebo denni rutine.",
        C4: "DETAIL PROOF creative: retargeting detail, ktery ukazuje material, tvar nebo konstrukci zblizka."
      };
      return purposes[setId] || fallback;
    }

    function renderAdDescriptionText(variant) {
      const parts = [];
      if (variant.primary_text) parts.push(`Primary text:\n${variant.primary_text}`);
      if (variant.headline) parts.push(`Headline: ${variant.headline}`);
      if (variant.description) parts.push(`Description: ${variant.description}`);
      if (variant.cta && variant.cta !== "handled_by_ad_platform") parts.push(`Platform CTA metadata: ${variant.cta}`);
      if (variant.hypothesis) parts.push(`Hypothesis: ${variant.hypothesis}`);
      return parts.join("\\n\\n");
    }

    function renderVideoNotice(payload) {
      const video = payload.video_generation || {};
      const status = video.video_generation_status || "unknown";
      if (status === "completed") {
        return `<div class="section"><h2>Video stav</h2><pre>Video bylo vygenerováno úspěšně.</pre></div>`;
      }
      const reason = video.failure_reason || video.error || "Důvod nebyl vrácen.";
      const nextStep = video.next_step || "Zkontroluj sekci Video generování a OpenRouter logs.";
      return `
        <div class="section">
          <h2>Proč video nebylo vygenerováno</h2>
          <pre>Status: ${escapeHtml(status)}

Důvod: ${escapeHtml(reason)}

Další krok: ${escapeHtml(nextStep)}</pre>
        </div>
      `;
    }

    function renderImageNotice(payload) {
      const image = payload.static_image_generation || {};
      const status = image.image_generation_status || "unknown";
      const reused = image.reused_count || 0;
      const duplicates = (image.duplicate_skips || []).length;
      const apiRequests = image.api_request_count ?? 0;
      const attempted = image.selected_creative_count ?? image.attempted_count ?? 0;
      const capPolicy = image.max_images_policy_note ? `\nLimit: ${image.max_images_policy_note}` : "";
      const reuseNote = reused ? `\nZnovu pouzito bez API volani: ${reused}` : "";
      const duplicateNote = duplicates ? `\nDuplicitni prompty preskoceny: ${duplicates}` : "";
      const requestNote = `\nAPI requesty: ${apiRequests} / kreativ vybrano: ${attempted}`;
      if (status === "completed") {
        return `<div class="section"><h2>Obrazky stav</h2><pre>Staticke ads obrazky byly vygenerovany uspesne.${requestNote}${duplicateNote}${reuseNote}${capPolicy}</pre></div>`;
      }
      if (status === "partial") {
        return `<div class="section"><h2>Obrazky stav</h2><pre>Cast obrazku byla vygenerovana, cast skoncila chybou. Detail je nize.${requestNote}${duplicateNote}${reuseNote}${capPolicy}</pre></div>`;
      }
      const reason = image.failure_reason || image.error || "Duvod nebyl vracen.";
      const nextStep = image.next_step || "Zkontroluj sekci Staticke obrazky a OpenRouter logs.";
      return `
        <div class="section">
          <h2>Proc obrazky nebyly vygenerovany</h2>
          <pre>Status: ${escapeHtml(status)}

Duvod: ${escapeHtml(reason)}

Dalsi krok: ${escapeHtml(nextStep)}</pre>
        </div>
      `;
    }

    function renderImageAssetLinks(imageGeneration) {
      const assets = imageGeneration?.image_assets || [];
      if (!assets.length) return "";
      return assets.map((asset) => `<a href="${escapeHtml(asset.image_url || "#")}" target="_blank">${escapeHtml(asset.image_path || asset.image_url || "obrazek")}</a>`).join("");
    }

    function renderImageGenerationPlan(imageGeneration) {
      const plan = imageGeneration?.generation_plan || [];
      const skipped = imageGeneration?.skipped_creatives || [];
      if (!plan.length && !skipped.length) return "";
      return `
        <div class="section">
          <h2>Plan statickych obrazku</h2>
          <div class="creative-copy">${escapeHtml(imageGeneration?.max_images_policy_note || imageGeneration?.prompt_respect_contract || "")}</div>
          ${plan.length ? `
            <div class="asset-grid">
              ${plan.map((item) => `
                <div class="asset-card">
                  <div class="asset-meta">
                    <div class="creative-card-title">
                      <strong>${escapeHtml(item.creative_id || "creative")}</strong>
                      <span class="pill">${escapeHtml(item.set_id || item.asset_type || "")}</span>
                    </div>
                    <div class="pill-row">
                      <span class="pill">${escapeHtml(item.angle || "angle")}</span>
                      <span class="pill">${escapeHtml(item.asset_type || "asset")}</span>
                      <span class="pill">${escapeHtml(item.aspect_ratio || "ratio")}</span>
                    </div>
                    <div class="creative-copy"><b>Layout:</b> ${escapeHtml(item.layout || "")}</div>
                    ${item.overlay_text ? `<div class="creative-copy"><b>Overlay:</b> ${escapeHtml(item.overlay_text)}</div>` : ""}
                  </div>
                  <details>
                    <summary>Prompt preview</summary>
                    <pre class="prompt-preview">${escapeHtml(item.prompt_preview || item.visual_prompt || "")}</pre>
                  </details>
                </div>
              `).join("")}
            </div>
          ` : ""}
          ${skipped.length ? `
            <details>
              <summary>Preskocene kreativy (${skipped.length})</summary>
              <pre>${escapeHtml(skipped.map((item) => `${item.creative_id || item.asset_type}: ${item.reason || ""}`).join("\\n"))}</pre>
            </details>
          ` : ""}
        </div>
      `;
    }

    function renderVisionQualityPanel(imageGeneration) {
      const checks = imageGeneration?.vision_quality_checks || [];
      const rejections = imageGeneration?.vision_quality_rejections || [];
      if (!checks.length && !rejections.length && !imageGeneration?.vision_quality_status) return "";
      return `
        <div class="section">
          <h2>Vision QA: product fidelity + human realism</h2>
          <div class="creative-copy"><b>Status:</b> ${escapeHtml(imageGeneration?.vision_quality_status || "unknown")} | <b>Model:</b> ${escapeHtml(imageGeneration?.vision_model || "")} | <b>Regenerace:</b> ${escapeHtml(String(imageGeneration?.regeneration_attempts || 0))}</div>
          ${checks.length ? `
            <div class="asset-grid">
              ${checks.map((check) => {
                const result = check.result || {};
                const fidelity = result.product_fidelity || {};
                const realism = result.human_realism || {};
                return `
                  <div class="asset-card">
                    <div class="asset-meta">
                      <strong>${escapeHtml(check.creative_id || "creative")}</strong>
                      <span class="pill">${escapeHtml(check.attempt || "attempt")}</span>
                      <span class="pill ${statusClass(result.status)}">${escapeHtml(result.status || "unknown")}</span>
                      <div class="creative-copy">
                        Shape ${escapeHtml(fidelity.shape_match ?? "-")} | Color ${escapeHtml(fidelity.color_match ?? "-")} | Branding ${escapeHtml(fidelity.branding_match ?? "-")} | Material ${escapeHtml(fidelity.material_finish_match ?? "-")}
                      </div>
                      <div class="creative-copy">
                        Human ${escapeHtml(realism.overall ?? "-")} | Hands ${escapeHtml(realism.hands_fingers ?? "-")} | Anatomy ${escapeHtml(realism.anatomy ?? "-")} | Light ${escapeHtml(realism.lighting_realism ?? "-")}
                      </div>
                      ${result.reason ? `<div class="creative-copy"><b>Duvod:</b> ${escapeHtml(result.reason)}</div>` : ""}
                    </div>
                    <details>
                      <summary>Vision JSON</summary>
                      <pre>${escapeHtml(JSON.stringify(result, null, 2))}</pre>
                    </details>
                  </div>
                `;
              }).join("")}
            </div>
          ` : `<div class="preview-empty">Vision QA neprobehla nebo nebyla potreba.</div>`}
          ${rejections.length ? `
            <details class="audit-details">
              <summary>Odmítnute pokusy pred regeneraci (${rejections.length})</summary>
              <pre>${escapeHtml(JSON.stringify(rejections, null, 2))}</pre>
            </details>
          ` : ""}
        </div>
      `;
    }

    function renderImageGallery(imageGeneration) {
      const assets = imageGeneration?.image_assets || [];
      if (!assets.length) return "";
      return `
        <div class="section">
          <h2>Vygenerovane ads obrazky</h2>
          <div class="asset-grid">
            ${assets.map((asset) => `
              <div class="asset-card">
                <img src="${escapeHtml(asset.image_url || "")}" alt="${escapeHtml(asset.creative_id || "creative")}">
                <div class="asset-meta">
                  <strong>${escapeHtml(asset.creative_id || "creative")}</strong>
                  ${escapeHtml(asset.set_id || "")} ${escapeHtml(asset.angle || "")} | ${escapeHtml(asset.asset_type || "")} | ${escapeHtml(asset.aspect_ratio || "")} | ${escapeHtml(asset.image_size || "")}${asset.generation_reused ? " | reused" : ""}
                  <div>${escapeHtml(asset.layout || "")}</div>
                </div>
                <details>
                  <summary>Prompt pro obrazek</summary>
                  <pre class="prompt-preview">${escapeHtml(asset.prompt || "")}</pre>
                </details>
              </div>
            `).join("")}
          </div>
        </div>
      `;
    }

    async function parseResponse(response) {
      const contentType = response.headers.get("content-type") || "";
      if (contentType.includes("application/json")) {
        return await response.json();
      }
      const text = await response.text();
      return {
        error: text || `Server returned HTTP ${response.status}`,
        status: response.status
      };
    }

    function escapeHtml(value) {
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }

    function escapeAttr(value) {
      return escapeHtml(value).replaceAll("\\n", " ");
    }

    function domId(value) {
      return String(value || "creative").replace(/[^a-zA-Z0-9_-]+/g, "_").slice(0, 80);
    }

    async function loadPromptSettings() {
      try {
        const response = await fetch("/prompt-settings");
        if (!response.ok) return;
        const settings = await response.json();
        setPromptDefault("content_prompt_system", settings.content_prompt_system);
        setPromptDefault("content_prompt_task", settings.content_prompt_task);
        setPromptDefault("base_video_prompt_template", settings.base_video_prompt_template);
        setPromptDefault("negative_prompt", settings.negative_prompt);
        const categoryPresets = settings.category_prompt_presets || {};
        setPromptDefault("category_prompt_handbag", formatCategoryPreset(categoryPresets.handbag));
        setPromptDefault("category_prompt_shoes", formatCategoryPreset(categoryPresets.shoes));
        setPromptDefault("category_prompt_apparel", formatCategoryPreset(categoryPresets.apparel));
        const sourceInventory = document.getElementById("prompt_source_inventory");
        if (sourceInventory) {
          sourceInventory.textContent = JSON.stringify(settings.prompt_source_inventory || {}, null, 2);
        }
      } catch (error) {
        console.warn("Prompt settings could not be loaded", error);
      }
    }

    function formatCategoryPreset(preset) {
      if (!preset) return "";
      const parts = [];
      if (preset.system_prompt) parts.push(`System:\n${preset.system_prompt}`);
      if (preset.video_directive) parts.push(`Video:\n${preset.video_directive}`);
      if (preset.image_directive) parts.push(`Static images:\n${preset.image_directive}`);
      return parts.join("\\n\\n");
    }

    function setPromptDefault(id, value) {
      const el = document.getElementById(id);
      if (el && !el.value) {
        el.value = value || "";
      }
    }

    function applyQueryParams() {
      const params = new URLSearchParams(window.location.search);
      if (!window.location.search) return;
      const booleanFields = new Set([
        "testimonial_mode",
        "use_avatar_image_reference",
        "avatar_own_person_consent",
        "generate_static_images"
      ]);
      const skipEmptyFields = new Set([
        "product_image",
        "openrouter_api_key",
        "content_prompt_system",
        "content_prompt_task",
        "base_video_prompt_template",
        "negative_prompt",
        "category_prompt_handbag",
        "category_prompt_shoes",
        "category_prompt_apparel"
      ]);

      params.forEach((value, key) => {
        const el = document.getElementById(key);
        if (!el) return;
        if (el.type === "file") return;
        if (value === "" && skipEmptyFields.has(key)) return;
        if (booleanFields.has(key)) {
          el.checked = ["1", "true", "yes", "on"].includes(value.toLowerCase());
          return;
        }
        el.value = value;
      });
    }

    function setupTabs() {
      const tabButtons = Array.from(document.querySelectorAll(".tab-button"));
      const panels = Array.from(document.querySelectorAll(".tab-panel"));
      tabButtons.forEach((tabButton) => {
        tabButton.addEventListener("click", () => {
          const target = tabButton.dataset.tab;
          tabButtons.forEach((button) => button.classList.toggle("active", button === tabButton));
          panels.forEach((panel) => panel.classList.toggle("active", panel.id === `tab-${target}`));
        });
      });
    }
  </script>
</body>
</html>"""
