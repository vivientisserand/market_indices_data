import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf
import datetime
import requests
from bs4 import BeautifulSoup


def get_cac40_instruments():
    """Returns CAC40 instruments."""
    res = requests.get("https://en.wikipedia.org/wiki/CAC_40")
    soup = BeautifulSoup(res.content, 'lxml')
    table = soup.find_all('table')[3]
    df = pd.read_html(str(table))[0]
    ticks = df["Ticker"]
    company = df["Company"]
    # ticks = df["Ticker"].apply(lambda S: S[:-3]) # Get rid of '.PA'
    return list(ticks), list(company)


def get_sp500_instruments():
    """Returns SP500 instruments."""
    res = requests.get("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
    soup = BeautifulSoup(res.content, 'lxml')
    table = soup.find_all('table')[0]
    df = pd.read_html(str(table))[0]
    ticks = df["Symbol"]
    company = df["Security"]
    return list(ticks), list(company)


def get_ftse100_instruments():
    """Returns FTSE 100 instruments."""
    res = requests.get("https://en.wikipedia.org/wiki/FTSE_100_Index")
    soup = BeautifulSoup(res.content, 'lxml')
    table = soup.find_all('table')[3]
    df = pd.read_html(str(table))[0]
    ticks = df["EPIC"]
    company = df["Company"]
    ticks = df["EPIC"].apply(lambda S: S+".L") # Syntax for UK stocks in Yahoo Finance
    return list(ticks), list(company)


# Dict to map market indices to the function that returns their instruments.
indices = {"CAC40":get_cac40_instruments, "SP500":get_sp500_instruments, "FTSE100":get_ftse100_instruments}

def get_df(index):
    res = indices.get(index)()
    symbols, company = res[0], res[1]
    ohlcv = {} # Dict to store everything
    for symbol in symbols:
        symbol_df = yf.Ticker(symbol).history(period="10y")
        ohlcv[symbol] = symbol_df[["Open", "High", "Low", "Close", "Volume"]].rename(
            columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume"
            }
        )
        #print(ohlcvs[symbol])
    df = pd.DataFrame(index = ohlcv[symbols[0]].index)
    df.index.name = "date"
    instruments = list(ohlcv.keys())

    for instr in instruments:
        instr_df = ohlcv[instr]
        columns = list(map(lambda x: "{} {}".format(instr, x), instr_df.columns)) # Columns personalized with stock name.
        df[columns] = instr_df
        # print(instr)
        # print(instr_df)
    return df, instruments, company


def format_date(date):
    yymmdd = list(map(lambda x: int(x), str(date).split(" ")[0].split("-")))
    return datetime.date(yymmdd[0], yymmdd[1], yymmdd[2])

# We miss some data from the Yahoo Finance API, we fill it and add return and vol.
def extended_df(traded, df):
    open_cols = list(map(lambda x: str(x) + " open", traded))
    high_cols = list(map(lambda x: str(x) + " high", traded))
    low_cols = list(map(lambda x: str(x) + " low", traded))
    close_cols = list(map(lambda x: str(x) + " close", traded))
    volume_cols = list(map(lambda x: str(x) + " volume", traded))
    historical_data = df.copy()
    historical_data = historical_data[open_cols + high_cols + low_cols + close_cols + volume_cols]
    historical_data.fillna(method="ffill", inplace=True) # Filling missing data by forward : a, b, c, ., -> a, b, c, c...
    historical_data.fillna(method="bfill", inplace=True) # Filling missing data by backward : ., a, b, c -> a, a, b, c
    for instr in traded:
        historical_data["{} % ret".format(instr)] = historical_data["{} close".format(instr)] / historical_data["{} close".format(instr)].shift(1) - 1 # Close to close return
        historical_data["{} % ret vol".format(instr)] = historical_data["{} % ret".format(instr)].rolling(25).std() # Historical rolling standard deviation for realized volatility
        historical_data["{} active".format(instr)] = historical_data["{} close".format(instr)] != historical_data["{} close".format(instr)].shift(1) # Is the stock actively trading or not ?
    historical_data.index = pd.Series(historical_data.index).apply(lambda x: format_date(x))
    return historical_data

