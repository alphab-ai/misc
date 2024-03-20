Requirements:  

`python3.11+`


- Configure env and install deps:
`sudo apt -y install python3.12-venv` or `apt -y install python3.11-venv`
`python3.12 -m venv ~/eibc`
`source ~/eibc/bin/activate`
`pip install -r  requirements.txt`


- replace vars in config.toml  
example:

```
[rollapp]
# rollapp RPC endpoint. def 26657
ROLLAP_RPC = "http://127.0.0.1:26657"

# rollapp LSD\REST endpoint. def 1317
ROLLAP_REST = "http://127.0.0.1:1317"

# rollapp chain-id
ROLLAP_CHAIN_ID = "tstmksa_7443605-1"
# rollapp denom
ROLLAP_DENOM = "afff"

# replace with your addrs.
# example: rollapp_evm keys add local-user2 --keyring-backend test --home ~/.roller/rollapp
# each addr will spam in a separate thread. the more addrs you will add the more threads there will be
IBC_SPAM_ADDRS = ["ethm1k3jr8ps67jnfjk6kqqkdyfnqgrnw0cljhr3csg", "ethm12c9mhtf0maysxdkq66wphr2re0v002a9fmw9ap", "ethm18xy60gz3f95546tduh35jslpcgsgm3msvues62"]

# binary location must be in PATH or absolete path
# example 'rollapp_evm' or '/usr/local/bin/rollapp_evm'
BINARY_NAME = 'rollapp_evm'
HOME = "~/.roller/rollapp"


[hub]
# hub LSD\REST endpoint. def 1318
REST = "http://127.0.0.1:1318"

# hub RPC endpoint. def 36657
RPC = "http://127.0.0.1:36657"

# hub chain-id
CHAIN_ID = "dymension_100-1"

# hub gas price
GAS_PRICE = 100_000_000

FULFILL_ADDR = "dym1srdh4kp66a00l76rk084lkylx9l0pg3ydue30e"
# binary location must be in PATH or absolete path
# example 'dymd' or '/usr/local/bin/dymd'
BINARY_NAME = '/usr/local/bin/dymd'


[misc]
# log level INFO'| 'DEBUG' | 'CRITICAL' | 'ERROR' | 'WARNING' | 'FATAL
log_level = 'INFO' 
BROADCAST_MODE = 'sync'
# disable\enale spam opts: true or false
ENABLE_SPAM = false

```

- usage

`python3.11 ibc_spam_and_ff.py`


example of output:  

```
03/20 02:00:51 | DEBUG  | MainThread    | load_config       | Config Loaded. Logger configured
03/20 02:00:51 | INFO   | MainThread    | create_threads    | ibc spam ENABLED. You can turn it OFF in config.toml under misc configuration
03/20 02:00:51 | INFO   | MainThread    | create_threads    | Thread ibc_spam-0 started. addr: ethm1k3jr8ps67jnfjk6kqqkdyfnqgrnw0cljhr3csg
03/20 02:00:51 | INFO   | MainThread    | create_threads    | Thread ibc_spam-1 started. addr: ethm12c9mhtf0maysxdkq66wphr2re0v002a9fmw9ap
03/20 02:00:51 | INFO   | MainThread    | create_threads    | Thread ibc_spam-2 started. addr: ethm18xy60gz3f95546tduh35jslpcgsgm3msvues62
03/20 02:00:51 | INFO   | MainThread    | create_threads    | Thread check_ordrs started. addr: dym1srdh4kp66a00l76rk084lkylx9l0pg3ydue30e
03/20 02:00:51 | DEBUG  | check_ordrs   | get_latest_height | height: 112124
03/20 02:00:51 | DEBUG  | ibc_spam-1    | acc_info          | Refreshing account. ethm12c9mhtf0maysxdkq66wphr2re0v002a9fmw9ap sequence: 59908 account_number: 14
03/20 02:00:51 | DEBUG  | ibc_spam-0    | acc_info          | Refreshing account. ethm1k3jr8ps67jnfjk6kqqkdyfnqgrnw0cljhr3csg sequence: 71065 account_number: 10
03/20 02:00:51 | DEBUG  | ibc_spam-2    | acc_info          | Refreshing account. ethm18xy60gz3f95546tduh35jslpcgsgm3msvues62 sequence: 47196 account_number: 15
03/20 02:00:51 | DEBUG  | check_ordrs   | acc_info          | Refreshing account. dym1srdh4kp66a00l76rk084lkylx9l0pg3ydue30e sequence: 28203 account_number: 16
03/20 02:00:51 | DEBUG  | check_ordrs   | get_latest_height | height: 112124
03/20 02:00:52 | DEBUG  | ibc_spam-2    | acc_info          | Refreshing account. ethm18xy60gz3f95546tduh35jslpcgsgm3msvues62 sequence: 47199 account_number: 15
03/20 02:00:52 | INFO   | ibc_spam-2    | ibc_spam          | ibc_txs_sent by ethm18xy60gz3f95546tduh35jslpcgsgm3msvues62 at the moment: 3
03/20 02:00:52 | DEBUG  | ibc_spam-1    | ibc_broadcast     | ibc_tx successfully broadcasted. tx_hash: 695293459CB43D91B3B79971BFF82922589A27A64B61B7AFFC7C50871BC4E808 code: 0
03/20 02:00:56 | DEBUG  | check_ordrs   | filter_orders     | new order id: 26aa1edbf4e3e45072621953cda0420698cdfc6e52e8a8eb2643492affa5a145
03/20 02:00:56 | DEBUG  | check_ordrs   | filter_orders     | new order id: 19d7677e4e0cb6205ae25dc2c9e58c6de6a8f1a86a284179def38371f7508b59
03/20 02:00:56 | DEBUG  | check_ordrs   | filter_orders     | new order id: 254f44c174d6b488b0959d5de495ab1ab9a9e8635879ddfac3af6063b735ceb1
03/20 02:00:56 | DEBUG  | check_ordrs   | filter_orders     | new order id: fcbf975f363e6d9f1db5886969fbed5f57a1f8234b192a3f1b913756074c82a3
03/20 02:00:56 | DEBUG  | check_ordrs   | filter_orders     | new order id: 90d40aaec3bda8648a1c86ed007d5934dbb9046f83cbe28cab9b5d154d0929fd
03/20 02:00:57 | INFO   | check_ordrs   | scan_txs_events   | height:112125 total_orders: 95    success_fullfilled_responses: 0     success_fullfilled: 95    failed_to_fullfill: 0     failed_txs: 0     txs_in_block: 3     total_txs: 3     orders_per_block: 95.00
```