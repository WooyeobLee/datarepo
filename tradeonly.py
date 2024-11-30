%%writefile tradeonly.py
import time
import sys
import pyupbit
import pandas as pd
import requests
import os

def get_candle(ticker, unit, count=200, tick='minutes',):
    url = f"https://api.upbit.com/v1/candles/{tick}/{unit}"
    response = requests.request('GET', url, params={'market':ticker, 'count':str(count)})
    return pd.DataFrame(response.json())[::-1].reset_index()

def rsi_calculator(data, period=14, col='trade_price'):
    up = data[col].diff()
    down = up.copy()
    up[up < 0] = 0
    down[down > 0] = 0
    gain = up.ewm(alpha=1/period).mean()
    loss = down.abs().ewm(alpha=1/period).mean()
    rs = gain/loss
    return float((100 - 100/(1+rs)).iloc[-1])

def get_rsis(tickers, unit):
    while True:
        rsis = {}
        try:
            for ticker in tickers:
                data = get_candle(ticker, unit)
                rsis[ticker] = rsi_calculator(data)
                time.sleep(0.3)
            return rsis
        except:
            time.sleep(1)

def get_ticker_revenue_rate(balance):
    coin_ticker = balance['unit_currency'] + "-" + balance['currency']
    now_price = pyupbit.get_current_price(coin_ticker)
    revenue_rate = (now_price - float(balance['avg_buy_price'])) / float(balance['avg_buy_price']) * 100.0
    return revenue_rate, coin_ticker, now_price

def get_revenue_rates(balances):
    if len(balances) >= 2:
        rates = {}
        prices = {}
        for balance in balances:
            if balance['currency'] == 'KRW':
                continue
            result = get_ticker_revenue_rate(balance)
            rates[result[1]] = result[0]
            prices[result[1]] = result[2]
        return rates, prices
    else:
        return
    
def print_state(ticker, state, excludes_flag=False):
    if excludes_flag:
        ticker = ticker + '*'
    print(f'코인: {ticker:<11} RSI: {state["rsi"]:10.5f} 수익률: {state["rate"]:10.5f}%, 가격: {state["price"]:10.1f}, 평가손익: {state["profit"]:10.2f}, 평가금액: {state["value"]:10.2f}')

def sell(ticker):
    balance = upbit.get_balance(ticker)
    state = upbit.sell_market_order(ticker, balance)
    price = pyupbit.get_current_price(ticker)
    return balance*price, state

if __name__ == '__main__':
    target_rate_min = float(sys.argv[1])
    target_rate_max = float(sys.argv[2])
    threshold_rsi = float(sys.argv[3])
    
    excludes = []

    if len(sys.argv) == 5:
        if bool(sys.argv[3].title()):
            with open('excludes.txt', 'r') as f:
                data = f.readlines()
                excludes = [coin.strip() for coin in data]
    
    access = 'NRQ5oEIxfrDx0D94BixOLC5xHdsGxxrTwzLGJZSh'
    secret = 'K9nM1xMCylgM5NKHDxsdf3eq7ZJdzZJtkRXymRyB'
    upbit = pyupbit.Upbit(access, secret)

    while True:
        balances = upbit.get_balances()
        balances2 = {'KRW-'+balance['currency']:float(balance['balance']) for balance in balances if balance['currency'] != 'KRW'}
        평가손익 = {'KRW-'+balance['currency']:float(balance['avg_buy_price'])*float(balance['balance']) for balance in balances if balance['currency'] != 'KRW'}
        
        if len(balances) < 2:
            os.system('cls')
            print('보유한 코인이 없습니다.')
            time.sleep(5)
            continue
        
        rates, prices = get_revenue_rates(balances)
        rsis = get_rsis(rates.keys(), unit=60)
        result = {key:{'rate': rates[key], 'rsi': rsis[key], 'price': prices[key], 'value': prices[key]*balances2[key], 'profit': prices[key]*balances2[key]-평가손익[key]} for key in rates}
        
        os.system('cls' if os.name == 'nt' else 'clear')
        print('자동 매도 프로그램 시작')
        print('------------------------------------------------------------')
        
        for ticker in result:
            print_state(ticker, result[ticker], (ticker in excludes))
            rate = result[ticker]['rate']
            rsi = result[ticker]['rsi']

            if rate >= target_rate_min and (ticker not in excludes):
                if rsi < threshold_rsi:
                    sales, state = sell(ticker) # 판매
                    print(f'매도 코인: {ticker:<10} 수익률: {rate:10.5f}% 금액: {sales}원')
                else:
                    print(f'매도 보류 코인: {ticker:<10}') # 판매 보류
            elif ticker in excludes:
                print('매도 예외 코인')
            else:
                print(f'매도 목표 미도달(최소 목표까지 {target_rate_min-rate:7.3f}%)')
        time.sleep(1)
