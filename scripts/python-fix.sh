#!/bin/bash

# This script applies fixes to the generated Python REST client code.
# Run this after generate.sh to patch known code-generator bugs.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

BIO_MODEL_API="${ROOT_DIR}/pyvcell/_internal/api/vcell_client/api/bio_model_resource_api.py"
API_CLIENT="${ROOT_DIR}/pyvcell/_internal/api/vcell_client/api_client.py"

# Fix 1: saveBioModel Accept header — the generator incorrectly includes application/json
# (from error response content types) in the Accept header for a method that only
# @Produces(APPLICATION_XML). This causes a NotAcceptableException on the server.
sed -i '' "/_save_bio_model_serialize/,/return self.api_client.param_serialize/ {
    s|'application/xml', *$|'application/xml'|
    /^ *'application\/json'$/d
}" "$BIO_MODEL_API"

# Fix 2: deserializer application/xml support — the generated client only handles
# application/json and text/* content types, but the server returns
# application/xml;charset=UTF-8 for VCML endpoints.
python3 -c "
import pathlib, re
p = pathlib.Path('$API_CLIENT')
src = p.read_text()
old = \"        elif re.match(r'^text\\\\/[a-z.+-]+\\\\s*(;|\$)', content_type, re.IGNORECASE):\\n            data = response_text\\n        else:\"
new = old.replace('        else:', \"        elif re.match(r'^application\\\\/xml\\\\s*(;|\$)', content_type, re.IGNORECASE):\\n            data = response_text\\n        else:\")
if old in src:
    p.write_text(src.replace(old, new))
    print('  - Patched api_client.py: added application/xml deserialization support')
elif 'application\\\\/xml' in src:
    print('  - api_client.py: application/xml fix already applied')
else:
    print('  - WARNING: could not find expected pattern in api_client.py')
"

echo "Applied fixes to generated Python client."
