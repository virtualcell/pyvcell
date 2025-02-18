import os
import shutil
import tempfile
from pathlib import Path

temp_dir = tempfile.mkdtemp(prefix='pyvcell_test_data_')
test_data_dir = Path(os.getcwd()) / "solver_input"

# move all files from test_data_dir to temp_dir
for file in test_data_dir.iterdir():
    shutil.copy(file, temp_dir)


import shutil
from pathlib import Path

test_data_dir = Path(temp_dir)
fv_input_file = test_data_dir / "SimID_946368938_0_.fvinput"
vcg_file = test_data_dir / "SimID_946368938_0_.vcg"
functions_file = test_data_dir / "SimID_946368938_0_.functions"
test_output_dir = Path(os.getcwd()) / "test_output"

shutil.copy(functions_file, test_output_dir)

from pyvcell.solvers.fvsolver import solve
try:
  ret_code = solve(input_file=fv_input_file, vcg_file=vcg_file, output_dir=test_output_dir)
  print(f"Return code: {ret_code}")
except ValueError as e:
  print(f"Error: {e}")


import os
with os.scandir(test_output_dir) as entries:
    for entry in entries:
        print(entry.name)


