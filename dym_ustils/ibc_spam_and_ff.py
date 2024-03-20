from subprocess import Popen, PIPE, run
from collections import defaultdict
from requests import get, post
from os import _exit as exit
from random import randint
from sys import stdout
from time import sleep
import logging.config
import threading
import traceback
import tomllib
import logging
import signal
import json

STATS = defaultdict(int) # collect stats and some debug info 
EIBC = dict()  # EIBC is a dict with all eibc events we have seen


# accounts info. sequence, account number, start_sequence
# format {addr: {cur_seq:0, acc_num:0}}
ACCOUNTS_INFO = dict()  

# disable logging from imported modules
logging.config.dictConfig({'version': 1, 'disable_existing_loggers': True})
logger = logging.getLogger()

# log format
formatter = logging.Formatter(fmt='%(asctime)s | %(levelname)-6s | %(threadName)-13s | %(funcName)-17s | %(message)s', datefmt='%m/%d %I:%M:%S')
# stdout logger
stdout_handler = logging.StreamHandler(stdout)
stdout_handler.setFormatter(formatter)
# file logger
file_handler = logging.FileHandler('logs.log')
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stdout_handler)


def load_config():
    """
    load config.toml
    perform structure and content checks
    apply log_level immediate
    """
    try:
        global CONFIG
        
        try:
            with open("config.toml", "rb") as f:
                CONFIG = tomllib.load(f)
        except (tomllib.TOMLDecodeError, ValueError) as err:
            logger.critical(f"config.toml invalid configuration: {err}")
            exit(1)

        match CONFIG:
            case {'rollapp': {'ROLLAP_RPC': str(), 'ROLLAP_REST': str(), 'ROLLAP_CHAIN_ID': str(), 'ROLLAP_DENOM': str(), 'IBC_SPAM_ADDRS': list()}, 
                  'hub': {'REST': str(), 'RPC': str(), 'CHAIN_ID': str(), 'GAS_PRICE': int(), 'FULFILL_ADDR': str(), 'BINARY_NAME': str()}, 
                  'misc': {'log_level': ('INFO'| 'DEBUG' | 'CRITICAL' | 'ERROR' | 'WARNING' | 'FATAL'),
                  'BROADCAST_MODE': ('sync' | 'async'| 'block'),
                  'ENABLE_SPAM': (True | False)}}:
                pass
            case _:
                # raise ValueError(f"config.toml invalid configuration: {CONFIG}")
                logger.critical(f"{err}\nEXITING...\nconfig.toml Invalid configuration:\n{CONFIG}")
                exit(1)
        logger.setLevel(CONFIG['misc']['log_level'])
        stdout_handler.setLevel(CONFIG['misc']['log_level'])
        file_handler.setLevel(CONFIG['misc']['log_level'])
        logger.debug(f"Config Loaded. Logger configured")
        return CONFIG
    except FileNotFoundError:
        logger.critical(f"{err}\nEXITING... config.toml not found!")
        exit(1)

load_config()


def acc_info(addr, REST=CONFIG['hub']['REST']):
    # get acc_num and sequence
    url = f"{REST}/cosmos/auth/v1beta1/accounts/{addr}"
    try:
        response = get(url).json()['account']
        ACCOUNTS_INFO = int(response['sequence'])
        acc_num = response['account_number']
        logger.debug(f"Refreshing account. {addr} sequence: {ACCOUNTS_INFO} account_number: {acc_num}")
    except KeyError:
        response = get(url).json()
        response = response['account']['base_account']
        ACCOUNTS_INFO = int(response['sequence'])
        acc_num = response['account_number']
        logger.debug(f"Refreshing account. {addr} sequence: {ACCOUNTS_INFO} account_number: {acc_num}")
    except KeyError as err:
        logger.critical(f"ADDR: {addr} NOT EXIST! fund this account")
        exit(1)
    return ACCOUNTS_INFO, acc_num


def ibc_broadcast(addr):
    # cmd to execute ibc_transfer. random amount, random eibc fee 
    cmd = [CONFIG['rollapp']['BINARY_NAME'], "tx", "ibc-transfer", "transfer", "transfer", "channel-0", F"{CONFIG['hub']['FULFILL_ADDR']}",
        f"{randint(1001,10000)}{CONFIG['rollapp']['ROLLAP_DENOM']}", "--keyring-backend", "test",
        "--chain-id", F"{CONFIG['rollapp']['ROLLAP_CHAIN_ID']}", "--home", CONFIG['rollapp']['HOME'],
        "--memo", f"{{\"eibc\": {{\"fee\": \"{randint(10,1000)}\"}}}}", "--broadcast-mode", f"{CONFIG['misc']['BROADCAST_MODE']}",
        f"--from", f"{addr}", "-o", "json", "-y", f"--sequence", f"{ACCOUNTS_INFO[addr]['cur_seq']}"]
    try:
        tx = run(cmd, capture_output=True, text=True)
        tx = json.loads(tx.stdout)
    # except (json.decoder.JSONDecodeError, FileNotFoundError) as err:
    except Exception as err:
        logger.critical(f"Traceback: {traceback.format_exc()}")
        logger.critical(f"{err}\nEXITING NOW! Unpredictable error Traceback^^")
        exit(1)
    ACCOUNTS_INFO[addr]['cur_seq'] += 1

    if tx['code'] == 32:
        new_seq = int(tx['raw_log'].split("expected ")[1].split(',')[0])
        logger.debug(f"simulate failed. sequence mismatch: got {ACCOUNTS_INFO[addr]['cur_seq']} expected: {new_seq}")
        ACCOUNTS_INFO[addr]['cur_seq'] = new_seq
        return ibc_broadcast(addr)
    elif tx['code'] == 0:
        logger.debug(f"ibc_tx successfully broadcasted. tx_hash: {tx['txhash']} code: {tx['code']} ")
    elif tx['code'] != 0:
        logger.error(f"failed to broadcast tx: {tx['txhash']} code: {tx['code']} log: {tx['raw_log']}")

    return tx['code']


def ibc_spam(addr):
    """rollap ibc spam"""
    while 1:
        # sleep(1)
        if addr not in ACCOUNTS_INFO:
            ACCOUNTS_INFO[addr] = dict()
            ACCOUNTS_INFO[addr]['cur_seq'], _ = acc_info(addr, CONFIG['rollapp']['ROLLAP_REST'])
            # sequence as a check_point
            ACCOUNTS_INFO[addr]['start_seq'] = ACCOUNTS_INFO[addr]['cur_seq']

        # refresh addr sequence
        elif ACCOUNTS_INFO[addr]['cur_seq'] % 100 == 0:
            ACCOUNTS_INFO[addr]['cur_seq'], _ = acc_info(addr, CONFIG['rollapp']['ROLLAP_REST'])
            # calculate how many txs sent by an addr. just subtract sequnce and we will get res
            txs_sent = ACCOUNTS_INFO[addr]['cur_seq'] - ACCOUNTS_INFO[addr]['start_seq']
            logger.info(f"ibc_txs_sent by {addr} at the moment: {txs_sent}")

        ibc_broadcast(addr)


def get_latest_height():
    # just return latest height from the hub
    url = f"{CONFIG['hub']['RPC']}/abci_info?"
    response = get(url).json()
    height = int(response['result']['response']['last_block_height'])
    logger.debug(f"height: {height}")
    return height

def scan_txs_events(height):
    """ iterate through txs events. 
    "total_orders" - total orders we fullfilled since start
    "total_tx" - total txs we observed since start
    "success_fullfilled_responses" - orders included in block with status is_fullfill == true
    "failed_txs" failed txs code != 0
    IMO more readable than block_results. by default return first 100 events. 
    in case there is > 100 events we should use pagination(NOT YET IMPLEMENTED) or patch tendermint"""


    url = f"{CONFIG['hub']['REST']}/cosmos/tx/v1beta1/txs?events=tx.height={height}"
    response = get(url).json()
    orders = []
    
    for tx in response['tx_responses']:
        STATS['total_tx'] += 1
        tx_hash = tx['txhash']
        code = int(tx['code'])
        if code != 0:
            logger.error(f"failed tx: {tx_hash} code: {code}")
            STATS['failed_txs'] += 1

        # iterate through tx logs
        for events in tx['logs']:
            for event in events['events']:
                # collect required info once we found eibc
                match event:
                    case {"type": eibc} if eibc == 'eibc':

                        for attrib in event['attributes']:

                            match attrib:

                                case {'key': key, 'value': value} if key == 'id':
                                    order_id = value

                                case {'key': key, 'value': value} if key == 'is_fulfilled':
                                    is_fulfilled = value

                                case {'key': key, 'value': value} if key == 'packet_status':
                                    packet_status = value

                                case {'key': key, 'value': value} if key == 'price':
                                    price = value

                                case {'key': key, 'value': value} if key == 'fee':
                                    fee = value

                        if is_fulfilled == 'false':
                            STATS['count_orders'] += 1
                            order = dict(order_id=order_id, is_fulfilled=is_fulfilled, packet_status=packet_status, price=price, fee=fee, tx_hash=tx_hash)
                            orders.append(order)
                        else:
                            # sometimes bihind. code != 0 or order already finalized and doesnt exist. re-check
                            # probably fixed
                            STATS['success_fullfilled_responses'] += 1
                            logger.debug(f"order successfully fullfilled! order id: {order_id}")
                            # process one order at a time
                            # filter_orders([order])

    # processing multiple orders in one tx - more than one message
    if len(orders) > 0:
        # pass newly collected orders to the filter_orders
        filter_orders(orders)

    # lazy way to calculate filled orders
    # success_fullfilled2 += dumps(response['tx_responses']).count(f'"value": "true"')
    tx_in_block = response['total']
    logger.debug(f"height: {height} txs in block: {tx_in_block}")

    # EIBC is a dict with all eibc we have seen before
    total_orders = len(EIBC) 
    orders_per_block = total_orders / (height - STATS['START_HEIGHT'])
    # print(f"[{height}] total_orders: {total_orders:<5} success_fullfilled_responses: {STATS['success_fullfilled_responses']:<5} success_fullfilled: {STATS['success_fullfilled']:<5} failed_to_fullfill: {STATS['failed_to_fullfill']:<5} failed_txs: {STATS['failed_txs']:<5} txs_in_block: {response['total']:<5} total_txs: {STATS['total_tx']:<5} orders_per_block: {orders_per_block:.2f}")
    logger.info(f"height:{height} total_orders: {total_orders:<5} success_fullfilled_responses: {STATS['success_fullfilled_responses']:<5} success_fullfilled: {STATS['success_fullfilled']:<5} failed_to_fullfill: {STATS['failed_to_fullfill']:<5} failed_txs: {STATS['failed_txs']:<5} txs_in_block: {tx_in_block:<5} total_txs: {STATS['total_tx']:<5} orders_per_block: {orders_per_block:.2f}")


def filter_orders(orders):
    # processing multiple orders in one tx - more than one message
    filtered_orders = [] # filtered is the orders we never seen before. double_check
    for order in orders:
        if order['order_id'] not in EIBC:
            # add order
            # EIBC is a dict with all eibc events we have seen
            EIBC[order['order_id']] = order
            filtered_orders.append(order)
            logger.debug(f"new order id: {order['order_id']}")

    order_status = fill_orders(filtered_orders)
    if order_status == 0:
        STATS['success_fullfilled'] += len(orders)
        logger.debug(f"success fullfilled code: {order_status} fullfilled: {len(filtered_orders)}")
    else:
        STATS['failed_to_fullfill'] += len(orders)
        logger.error(f"failed to fullfill code: {order_status} tried to fullfill: {len(filtered_orders)}")


def fill_orders(orders, gas=0, count=0):
    # iterate throgh orders. fullfill them, build tx and broadcast it
    # global ACCOUNTS_INFO

    tx = {"body":{"messages":[]},"auth_info":{"fee":{"amount":[{"denom":"adym","amount":f"{int(CONFIG['hub']['GAS_PRICE']*gas)}"}],"gas_limit":f"{gas}"}}}

    for order in orders:
        msg = {"@type":"/dymensionxyz.dymension.eibc.MsgFulfillOrder", "fulfiller_address": CONFIG['hub']['FULFILL_ADDR'], "order_id":order['order_id']}
        tx['body']['messages'].append(msg)

    total_messages = len(tx['body']['messages'])
    
    SIGN_TEMPLATE = f"{CONFIG['hub']['BINARY_NAME']} tx sign - --chain-id={CONFIG['hub']['CHAIN_ID']} --keyring-backend=test --from={CONFIG['hub']['FULFILL_ADDR']} " \
    f"--sequence={ACCOUNTS_INFO[CONFIG['hub']['FULFILL_ADDR']]['cur_seq']} --account-number={ACCOUNTS_INFO[CONFIG['hub']['FULFILL_ADDR']]['acc_num']} -y"

    tx = json.dumps(tx)
    # sign tx document
    p = Popen(SIGN_TEMPLATE, stdout=PIPE, shell=True, stdin=PIPE, stderr=PIPE)
    p.stdin.write(str.encode(tx))
    p.stdin.flush()
    encoded_tx = json.loads(p.communicate()[0].decode())

    if gas == 0:
        # simulate and calculate gas 
        p = Popen(f'{CONFIG['hub']['BINARY_NAME']} tx encode -', stdout=PIPE, shell=True, stdin=PIPE, stderr=PIPE)
        p.stdin.write(str.encode(json.dumps(encoded_tx)))
        p.stdin.flush()
        signed_tx = p.communicate()[0].decode().strip()

        data = json.dumps({"tx_bytes": signed_tx, "mode": "CONFIG['misc']['BROADCAST_MODE']_SYNC"})
        try:
            response = post(f'{CONFIG['hub']['REST']}/cosmos/tx/v1beta1/simulate', data=data).json()

            if 'code' in response and response['code'] == 2:
                # "account sequence mismatch, expected 27587, got 27586"
                # hapens sometimes. this will ovverride global ACCOUNTS_INFO
                new_seq = int(response['message'].split("expected ")[1].split(',')[0])
                logger.debug(f"simulate failed. sequence mismatch: got {ACCOUNTS_INFO[CONFIG['hub']['FULFILL_ADDR']]['cur_seq']} expected: {new_seq}")
                ACCOUNTS_INFO[CONFIG['hub']['FULFILL_ADDR']]['cur_seq'] = new_seq
                return fill_orders(orders, gas)

            # gas multiplier 1.11 
            gas = int(int(response['gas_info']['gas_used']) * 1.11)
            logger.debug(f"simulate success. messages in tx: {total_messages} gas required: {gas}")
            return fill_orders(orders, gas)

        except KeyError as err:
            if count <= 3:
                logger.error(f"simulate failed {err}\n{response}")
                # print(f"simulate failed {err}\n{response}")
                count += 1
                return fill_orders(orders, gas, count)
            # check this
            logger.critical(f"Traceback: {traceback.format_exc()}")
            logger.critical(f"{err}\nEXITING NOW! Unpredictable error Traceback^^")
            exit(1)

    # broadcast signed tx document
    cmd = f"{CONFIG['hub']['BINARY_NAME']} tx broadcast - --broadcast-mode={CONFIG['misc']['BROADCAST_MODE']} --node={CONFIG['hub']['RPC']} -y -o json"
    p = Popen(cmd, stdout=PIPE, shell=True, stdin=PIPE, stderr=PIPE)
    p.stdin.write(str.encode(json.dumps(encoded_tx)))
    p.stdin.flush()
    tx = json.loads(p.communicate()[0].decode())
    
    if tx['code'] == 32:
        new_seq = int(tx['raw_log'].split("expected ")[1].split(',')[0])
        ACCOUNTS_INFO[CONFIG['hub']['FULFILL_ADDR']]['cur_seq'] = new_seq
        logger.debug(f"failed to broadcast tx: sequence mismatch: got {ACCOUNTS_INFO[CONFIG['hub']['FULFILL_ADDR']]['cur_seq']} expected: {new_seq}")
        return fill_orders(orders, gas)

    elif tx['code'] != 0:
        logger.error(f"failed to broadcast tx: {tx['txhash']} code: {tx['code']} log: {tx['raw_log']}")
        # print(f"[FAIL] {ACCOUNTS_INFO[CONFIG['hub']['FULFILL_ADDR']]['cur_seq']} code: {tx['code']} {tx['raw_log']} {order_id}")

    ACCOUNTS_INFO[CONFIG['hub']['FULFILL_ADDR']]['cur_seq'] += 1
    logger.debug(f"fullfill_order tx successfully broadcasted. tx_hash: {tx['txhash']} code: {tx['code']} ")

    return tx['code']


def check_ordrs():
    """
    each second check for the new height
    once new height apeared scan_txs_events
    """
    try:
        STATS['START_HEIGHT'] = height = get_latest_height()
        ACCOUNTS_INFO[CONFIG['hub']['FULFILL_ADDR']] = dict()
        ACCOUNTS_INFO[CONFIG['hub']['FULFILL_ADDR']]['cur_seq'], ACCOUNTS_INFO[CONFIG['hub']['FULFILL_ADDR']]['acc_num'] = acc_info(CONFIG['hub']['FULFILL_ADDR'])

        while 1:
            new_height = get_latest_height()
            if height < new_height:
                # ACCOUNTS_INFO, acc_num = acc_info(CONFIG['hub']['FULFILL_ADDR'])
                # ACCOUNTS_INFO[CONFIG['hub']['FULFILL_ADDR']] = dict()
                # before process txs events refresh account
                ACCOUNTS_INFO[CONFIG['hub']['FULFILL_ADDR']]['cur_seq'], _ = acc_info(CONFIG['hub']['FULFILL_ADDR'])
                # check_point
                height += 1
                scan_txs_events(height)
            sleep(1)
    except Exception as err:
        # catch crit err traceback and log it
        logger.critical(f"Traceback: {traceback.format_exc()}")
        logger.critical(f"{err}\nEXITING NOW! Unpredictable error Traceback^^")
        exit(1)


def create_threads():
    """
    create threads for each task.

    """
    try:
        threads = list()
        if CONFIG['misc']['ENABLE_SPAM']:
            logger.info(f"ibc spam ENABLED. You can turn it OFF in config.toml under misc configuration")
            # rolaap spam. each addr will be spawned and spam ibc as a thread 
            for num, addr in enumerate(CONFIG['rollapp']['IBC_SPAM_ADDRS']):
                th = threading.Thread(target=ibc_spam,args=(addr,), name=f"ibc_spam-{num}")
                threads.append(th)
                th.start()
                logger.info(f"Thread {th.name:<10} started. addr: {addr}")
        else:
            logger.info(f"ibc spam DISABLED. You can turn it ON in config.toml under misc configuration")

        # add check_ordrs to the threads list
        th = threading.Thread(target=check_ordrs, name='check_ordrs')
        threads.append(th)
        th.start()
        logger.info(f"Thread {th.name:<10} started. addr: {CONFIG['hub']['FULFILL_ADDR']}")

        # without join catch KeyboardInterrupt not working
        for th in threads:
            th.join()
    except KeyboardInterrupt:
        logger.info(f"Exit signal... Stopped")
        exit(1)
    except Exception as err:
        # catch crit err traceback and log it
        logger.critical(f"Traceback: {traceback.format_exc()}")
        logger.critical(f"{err}\nEXITING NOW! Unpredictable error Traceback^^")
        exit(1)

if __name__ == '__main__':
    create_threads()