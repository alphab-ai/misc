from collections import defaultdict, OrderedDict
from operator import itemgetter
import json
import bech32
import binascii
from datetime import datetime

DELEGATORS_ALL = defaultdict(float)
DELEGATORS_ACTIVE = defaultdict(float)
EXPONENT = 10**18
FILE_NAME = "temp_1000.json"


def load_state():
    with open(f"{FILE_NAME}") as f:
        d = json.load(f)
        return d


def get_bonded_vals(d):
    bonded = set()
    for record in d["app_state"]['staking']['validators']:
        match record:
            case {"status": status, "operator_address": operator_address} if status == 'BOND_STATUS_BONDED':
                bonded.add(operator_address)
    return bonded


def save_to_csv(data):
    for deleg_type, delegators in data.items():
        dt = datetime.now().strftime('%Y%m%d')
        FILE_NAME_CSV = f"validator_{dt}_{deleg_type}.csv"
        with open(f"{FILE_NAME_CSV}", 'w') as f:
            for k, v in delegators.items():
                f.write(f"{k},{v}\n") 
        print(f"[OK] saved to {FILE_NAME_CSV} total entries: {len(delegators)}")


def main():
    TOTAL_DELEGATORS_RECORDS = 0
    data = load_state()
    bonded = get_bonded_vals(data)
    print(f"[OK] STATE LOADED")
    for record in data["app_state"]['distribution']['delegator_starting_infos']:
        TOTAL_DELEGATORS_RECORDS += 1
        match record:
            case {"delegator_address": delegator_address, "validator_address": validator_address}:
                stake = float(record['starting_info']['stake']) / EXPONENT
                stake = round(stake, 3)
                b = bech32.bech32_decode(delegator_address)[1]
                b = bech32.convertbits(b, 5, 8, False)
                b = f"0x{binascii.hexlify(bytearray(b)).decode('ascii')}"
                if validator_address in bonded:
                    DELEGATORS_ACTIVE[b] += stake
                DELEGATORS_ALL[b] += stake

    print(f"[OK] Total delegations records: {TOTAL_DELEGATORS_RECORDS}")
    sorted_delegators_all = OrderedDict(sorted(DELEGATORS_ALL.items(), key=itemgetter(1), reverse=True))
    sorted_delegators_active = OrderedDict(sorted(DELEGATORS_ACTIVE.items(), key=itemgetter(1), reverse=True))
    delegators = {"all": sorted_delegators_all, "active_only": sorted_delegators_active}
    return save_to_csv(delegators)


if __name__ == '__main__':
    main()
