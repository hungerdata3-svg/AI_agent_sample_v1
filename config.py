from pathlib import Path

# Where the CSV files and the report are saved (your Mac Desktop)
OUTPUT_DIR = Path.home() / "Desktop" / "pipeline_output"

RANDOM_SEED = 42      # same seed = same sample data every run
N_RECORDS = 200       # number of sample orders to generate
BAD_RATE = 0.15       # about 15% of rows get a planted problem

EXPECTED_COLUMNS = ["order_id", "customer_id", "order_date", "amount", "status"]
VALID_STATUSES = ["NEW", "SHIPPED", "DELIVERED", "CANCELLED"]

# Weights for the overall score (must add up to 1.0)
STAGE_WEIGHTS = {"extract": 0.30, "transform": 0.30, "load": 0.40}
