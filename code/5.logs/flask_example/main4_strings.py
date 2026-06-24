# Code based on answer by mhawke at https://stackoverflow.com/a/32001771/827927

import quadratic, logging
from quadratic import quadratic_formula
from io import StringIO

print("\n\n### Running with only a string handler\n")
log_stream = StringIO()
quadratic.logger.addHandler(logging.StreamHandler(log_stream))
quadratic.logger.setLevel(logging.DEBUG)

print(quadratic_formula(1, 0, -4))
print(quadratic_formula(1, 0, 4))

log_string = log_stream.getvalue()
print(f"\n\nLOGS:\n{log_string}")