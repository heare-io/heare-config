#!/usr/bin/env bash
TOP="$(cd $(dirname $0)/.. && pwd -L)"
cd "${TOP}"
pytest "${TOP}"
pycodestyle "${TOP}"
mypy "${TOP}"
