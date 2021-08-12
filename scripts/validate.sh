#!/usr/bin/env bash
TOP="$(cd $(dirname $0)/.. && pwd -L)"
cd "${TOP}"
pytest "${TOP}"
pycodestyle "${TOP}"
mypy "${TOP}/heare" "${TOP}/tests"
rst2html.py --exit-status 3 --report 3 README.md > /dev/null