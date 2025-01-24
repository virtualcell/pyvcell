#!/bin/bash

set -ex

ROOT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && cd .. && pwd )"

cd ${ROOT_DIR} || (echo "Failed to cd into ${ROOT_DIR}" && exit 1)

python -m venv .venv_jupyter
source .venv_jupyter/bin/activate
pip install jupyter ipython matplotlib
poetry install
jupyter notebook