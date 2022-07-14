import requests
from pprint import pprint
import json
import pandas as pd
import datetime
import seaborn as sns
from string import Template
import asyncio
import aiohttp
import plotly.express as px
import numpy as np
import streamlit as st
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title='AAVE v2 TVL, Yield & Utilization Dashboard', layout='centered')
refresh = st_autorefresh(limit=1)


subgraph = 'https://api.thegraph.com/subgraphs/name/messari/aave-v2-ethereum'
# function to use requests.post to make an API call to the subgraph url
def run_query(q, s):
    #request from subgraph
    request = requests.post(s, json={'query': query})
    if request.status_code == 200:
        return request.json()
    else:
        raise Exception('Query failed. return code is {}.      {}'.format(request.status_code, query))

# deposits template
base_template = Template(
"""
{
  marketDailySnapshots (first: 1000, orderBy: timestamp, orderDirection:asc, where: {timestamp_gte: $timestamp}) {
    id 
    market {
      id
      inputTokens {
        symbol
      }
      totalBorrowUSD
      totalValueLockedUSD
      totalVolumeUSD
      inputTokenBalances
      depositRate
      
    }
    timestamp
  }
}

"""
)

###all lists to compile into df at end
timestamps = []
symbol = []
total_borrowUSD = []
tvl = []
deposit_rate = []



start_timestamp = 1606778006
query = base_template.substitute(timestamp=start_timestamp)

def get_data():

    result = run_query(query, subgraph)
    tmp_df = result['data']['marketDailySnapshots']

    for item in tmp_df:
        symbol.append(item['market']['inputTokens'])
        total_borrowUSD.append(item['market']['totalBorrowUSD'])
        tvl.append(item['market']['totalValueLockedUSD'])
        deposit_rate.append(item['market']['depositRate'])
        timestamps.append(item['timestamp'])


#get all deposit data
get_data()

start_timestamp = timestamps[-1]
while int(timestamps[-1]) < int((datetime.datetime.now() - datetime.timedelta(days=2)).timestamp()):
    query = base_template.substitute(timestamp=start_timestamp)
    get_data()
    start_timestamp = timestamps[-1]

#put into df

symbol = [i[0]['symbol'] for i in symbol] #get symbols from dictionary
unique_symbols = set(symbol)
timestamps = [int(i) for i in timestamps] #convert to integers
timestamps = [datetime.datetime.fromtimestamp(i).strftime("%Y/%m/%d") for i in timestamps] #convert integer unix stamp to datetime
#tvl = [i.strip('-') for i in tvl] #some tvl values are negative, not sure why. get absolute values (strip negative signs)
total_borrowUSD = [float(i) for i in total_borrowUSD]
tvl = [float(i) for i in tvl]
deposit_rate = [round(float(i), 3) for i in deposit_rate]
#deposit_rate = [str(i*100) + '%' for i in deposit_rate]
columns = ['Date', 'Symbol', 'Total Borrow USD', 'TVL', 'Deposit Rate'] #create columns
final_list = [timestamps, symbol, total_borrowUSD, tvl, deposit_rate] #compile final list for df
df = pd.DataFrame(final_list).transpose() #compile df and transpose to add columns
df.columns = columns #add columns
df = df.loc[df['TVL'] > 0]


sectors = {
    'CRV': 'DeFi',
    'UNI': 'DeFi',
    'LINK': 'Infrastructure',
    'WETH': 'Smart Contract Platforms',
    'USDC': 'Stablecoins',
    'MANA': 'GameFi',
    'DAI': 'Stablecoins',
    'stETH': 'Smart Contract Platforms',
    'sUSD': 'Stablecoins',
    'USDT': 'Stablecoins',
    'AMPL': 'Stablecoins',
    'BUSD': 'Stablecoins',
    'BAL': 'DeFi',
    'MKR': 'DeFi', 
    'xSUSHI': 'DeFi',
    'SNX': 'DeFi',
    'CVX': 'DeFi',
    'BAT': 'Infrastructure',
    'FEI': 'Stablecoins',
    'RAI': 'Stablecoins',
    'WBTC': 'Currencies',
    'AAVE': 'DeFi',
    'ENJ': 'GameFi',
    'PAX': 'Stablecoins',
    'REN': 'DeFi',
    'TUSD': 'Stablecoins',
    'FRAX': 'Stablecoins',
    'GUSD': 'Stablecoins',
    'KNC': 'DeFi',
    'DPI': 'DeFi',
    'YFI': 'DeFi',
    'ENS': 'Infrastructure',
    'ZRX': 'DeFi',
    'renFIL': 'Infrastructure',
    'UNI-V2': 'DeFi',
    'BPT': 'GameFi',
    'G-UNI': 'DeFi'
}

df['Utilization (%)'] = df['Total Borrow USD'] / df['TVL'] #calculate utilization rate
df['Utilization (%)'] = pd.to_numeric(df['Utilization (%)']) * 100 #format utilization rate for treemap
df['Deposit Rate'] = pd.to_numeric(df['Deposit Rate']) * 100 #format deposit rate for treemap

df = df.loc[df['Utilization (%)'] < 100.0] #Remove incorrect utilization data

df['Sector'] = df['Symbol'].map(sectors) #Add sectors column

#Streamlit app title
st.markdown("<h1 style='text-align: center; color: white;'> AAVE v2 - Liquidity</h1>", unsafe_allow_html=True)


#date filter
date = st.date_input(label='Enter Date (Year/Month/Day ie: 2022/07/05)', min_value=datetime.date(2020, 11, 30), max_value=datetime.date.today())
date = str(date)
date = date.replace("-", "/")
df = df.loc[df['Date'] == date]
df = df.drop_duplicates()

fig=px.treemap(df, path=[px.Constant("All Sectors"), 'Sector', 'Symbol'], values='TVL', \
            color='Utilization (%)', color_continuous_scale=['green', 'red'], \
              hover_data=['TVL', 'Total Borrow USD', 'Deposit Rate'])

fig.data[0].texttemplate = "%{label}<br>TVL: $%{value:,.0f}<br>Deposit Rate: %{customdata[2]:.2f}%"
fig.data[0].hovertemplate = "%{label}<br>TVL: $%{value:,.0f}<br>Total Borrow USD: $%{customdata[1]:,.0f}<br>Deposit Rate: %{customdata[2]:.2f}%<br>Utilization: %{customdata[3]:.2f}%"



st.write(fig)
#st.write(df)

st.subheader('Glossary:')
st.write(
  """
  Total Borrow USD: Current balance of all borrowed assets (not historical cumulative), in USD. In the case of CDPs, this will be all minted assets. \n\n
  TVL: The total value locked in deposits on this market measured in USD \n\n
  Utilization (%): Total Borrow USD / TVL \n\n
  Deposit Rate: Deposit interest rate in APY percentage
  """

  )


