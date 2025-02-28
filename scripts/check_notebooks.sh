#!/bin/bash
set -e

# script directory as a path
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
NOTEBOOK_DIR="${SCRIPT_DIR}/../examples/notebooks"

# Convert all Jupyter notebooks to Python scripts
find ${NOTEBOOK_DIR} -name "*.ipynb" -exec jupyter nbconvert --to script {} \;

# Run mypy on the converted Python scripts
find . -name "*.py" -not -path "./.venv/*" -not -path "./.venv_jupyter/*" -exec mypy {} \; | grep -v "Success"

# prompt for user input [enter] to proceed
read -p "Press [Enter] to remove temporary files ..."

# Remove all the converted Python scripts
find ${NOTEBOOK_DIR} -name "*.py" -exec rm {} \;
