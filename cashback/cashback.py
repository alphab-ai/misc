from requests import get

LCD = 'https://rest.cosmos.directory/dymension'
VALOPER_ADDRS = "dymvaloper1tdwdzhyxqd9mdnywfh6sc3dl3926rvnuqq98fh"
DELEGATORS = ["dym1fnn0y2aq78vq9raqastf0tahcxvzll76g94vdn", "dym1xnypq70h2vc2a8ajd4rd5sk2ncy8kx348jm5td", "dym1efnfxghfrlsnxz0hydsklurldwwwjz6hh38zgd"]
EXPONENT = 10**18 # def 10**6


def main():
    # calculate cahsback for a given list of a delegators
    validator_coms = float(get(f"{LCD}/cosmos/staking/v1beta1/validators/{VALOPER_ADDRS}").json()['validator']['commission']['commission_rates']['rate'])
    for delegator in DELEGATORS:
        rewards = int(float(get(f"{LCD}/cosmos/distribution/v1beta1/delegators/{delegator}/rewards/{VALOPER_ADDRS}").json()['rewards'][0]['amount']))
        delegator_reward_fraction = 1 - validator_coms
        cash_back = int(((rewards/delegator_reward_fraction)/EXPONENT) - rewards/EXPONENT)
        print(f"Delegator: {delegator} rewards: {int(rewards/EXPONENT):<7} cashback_perc: {validator_coms} cashback: {cash_back}")


if __name__ == '__main__':
    main()
