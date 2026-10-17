#!/usr/bin/env bash
# Сборка PDF-версии секторного отчёта из HTML.
# Печатный лист A3 (297×420 мм): ширина полосы ~1016 px удерживает вёрстку в две
# колонки, иначе сетка графиков схлопывается на точке 820 px и рисунки растягиваются.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="$HERE/tsod-kazakhstan-2026-2036.html"
OUT="$HERE/tsod-kazakhstan-2026-2036.pdf"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
CHROME="${CHROME:-/opt/pw-browsers/chromium-1194/chrome-linux/chrome}"

python3 - "$SRC" "$TMP/print.html" <<'PY'
import io, sys
src, dst = sys.argv[1], sys.argv[2]
s = io.open(src, encoding='utf-8').read()
style = """<style>
@page{size:297mm 420mm;margin:14mm 14mm 16mm}
html,body{-webkit-print-color-adjust:exact;print-color-adjust:exact}
@media print{
  .page{padding:0}
  .grid2{display:grid!important;grid-template-columns:1fr 1fr!important;gap:14px!important}
  figure,table,.callout,.kpis,.findings{break-inside:avoid}
  .seclabel{break-before:page}
  .seclabel:first-of-type{break-before:auto}
  h2,h3{break-after:avoid}
}
</style></head>"""
io.open(dst, 'w', encoding='utf-8').write(s.replace('</head>', style, 1))
PY

"$CHROME" --headless=new --no-sandbox --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="$OUT" --virtual-time-budget=8000 "file://$TMP/print.html"
echo "→ $OUT"
