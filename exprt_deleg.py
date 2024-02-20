
from collections import defaultdict, OrderedDict
from operator import itemgetter
import json


DELEGATORS = defaultdict(float)
EXPONENT = 10**18
FILE_NAME = "temp_1000.json"


def load_state():
    with open(f"{FILE_NAME}") as f:
        d = json.load(f)
        return d

def save_to_csv(sorted_delegators):
    FILE_NAME_CSV = f"{FILE_NAME.split('.')[0]}.csv"
    with open(f"{FILE_NAME_CSV}", 'w', newline="\n") as f:
        for k, v in sorted_delegators.items():
            f.write(f"{k},{v}\n") 
    print(f"[OK] delegatrs saved to {FILE_NAME_CSV}")

def main():
    data = load_state()
    TOTAL_DELEGATORS_RECORDS = 0
    print(f"[OK] STATE LOADED")
    for record in data["app_state"]['distribution']['delegator_starting_infos']:
        TOTAL_DELEGATORS_RECORDS += 1
        match record:
            case {"delegator_address": delegator_address}:
                stake = float(record['starting_info']['stake']) / EXPONENT
                stake = round(stake, 3)
                DELEGATORS[delegator_address] += stake

    print(f"[OK] Unique delegators: {len(DELEGATORS)} total records: {TOTAL_DELEGATORS_RECORDS}")
    sorted_delegators = OrderedDict(sorted(DELEGATORS.items(), key=itemgetter(1), reverse=True))
    return save_to_csv(sorted_delegators)

if __name__ == '__main__':
    main()
