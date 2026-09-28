import json
import os

# Helper for passing an order/quote ID from a "producer" test run to a separate "consumer" run (amend/withdraw).

STATE_DIR = 'tests/idx_mme_data/state'


def save_state(name, data):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(os.path.join(STATE_DIR, f'{name}.json'), 'w') as f:
        json.dump(data, f)


def load_state(name):
    with open(os.path.join(STATE_DIR, f'{name}.json'), 'r') as f:
        return json.load(f)
