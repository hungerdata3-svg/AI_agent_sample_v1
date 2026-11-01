"""Step 1: create a sample dictionary of orders with some planted problems."""
import random
from datetime import date, timedelta

from config import N_RECORDS, BAD_RATE, RANDOM_SEED, VALID_STATUSES, EXPECTED_COLUMNS

PROBLEMS = ["missing_customer", "negative_amount", "bad_status", "bad_date", "duplicate_id"]


def generate_sample_data():
    """Return (raw_data, truth).

    raw_data: a dictionary of lists, one list per column, like a table.
    truth:    1 if the row has a planted problem, 0 if it is clean.
              The pipeline never sees this. It is only used to measure accuracy.
    """
    rng = random.Random(RANDOM_SEED)
    start = date(2026, 1, 1)

    raw_data = {col: [] for col in EXPECTED_COLUMNS}
    truth = []

    for i in range(1, N_RECORDS + 1):
        order_id = f"ORD{i:05d}"
        customer_id = f"CUST{rng.randint(1, 60):04d}"
        order_date = (start + timedelta(days=rng.randint(0, 300))).isoformat()
        amount = round(rng.uniform(5, 500), 2)
        status = rng.choice(VALID_STATUSES)

        is_bad = rng.random() < BAD_RATE
        if is_bad:
            problem = rng.choice(PROBLEMS)
            if problem == "duplicate_id" and i == 1:
                problem = "missing_customer"  # the first row has no earlier row to copy

            if problem == "missing_customer":
                customer_id = None
            elif problem == "negative_amount":
                amount = -abs(amount)
            elif problem == "bad_status":
                status = "UNKNOWN"
            elif problem == "bad_date":
                order_date = "2026-13-45"
            elif problem == "duplicate_id":
                order_id = f"ORD{i - 1:05d}"  # reuse the previous row's ID

        raw_data["order_id"].append(order_id)
        raw_data["customer_id"].append(customer_id)
        raw_data["order_date"].append(order_date)
        raw_data["amount"].append(amount)
        raw_data["status"].append(status)
        truth.append(1 if is_bad else 0)

    return raw_data, truth
