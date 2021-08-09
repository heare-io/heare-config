#!/usr/bin/env bash
TOP="$(cd $(dirname $0)/.. && pwd -L)"
cd "${TOP}"
pytest "${TOP}"
pycodestyle "${TOP}"
mypy "${TOP}"
rst2html.py --exit-status 3 --report 3 "${TOP}/README.md" > /dev/null
