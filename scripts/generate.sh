#!/usr/bin/env bash

ROOT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && cd .. && pwd )"

echo "ROOT_DIR: ${ROOT_DIR}"

openapi-generator validate -i ${ROOT_DIR}/scripts/openapi.yaml --recommend
if [ $? -ne 0 ]; then
    echo "openapi.yaml is not valid"
    exit 1
fi

openapi-generator generate \
    -g python \
    -i ${ROOT_DIR}/scripts/openapi.yaml \
    -o ${ROOT_DIR}/pyvcell/api/vcell \
    -c ${ROOT_DIR}/scripts/openapi_config.yaml

