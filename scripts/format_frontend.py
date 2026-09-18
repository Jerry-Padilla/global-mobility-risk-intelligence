"""Normalize source formatting without changing generated frontend assets."""

import re
import subprocess
import sys
from pathlib import Path

import cssbeautifier
import jsbeautifier

for path in Path("templates").rglob("*.html"):
    text = path.read_text(encoding="utf-8")
    text = text.replace("{% for field in 'make,model,year,component'|cut:' ' %}{% endfor %}", "")
    text = re.sub(r">(?=<|\{%|\{\{)", ">\n", text)
    text = re.sub(r"%}(?=<|\{%|\{\{)", "%}\n", text)
    path.write_text(text, encoding="utf-8")
result = subprocess.run(
    [sys.executable, "-m", "djlint", "templates", "--reformat", "--profile=django", "--quiet"]
)
if result.returncode not in (0, 1):
    raise SystemExit(result.returncode)
for name, formatter in [("assets/app.css", cssbeautifier), ("static/app.js", jsbeautifier)]:
    path = Path(name)
    path.write_text(formatter.beautify(path.read_text(encoding="utf-8")) + "\n", encoding="utf-8")
