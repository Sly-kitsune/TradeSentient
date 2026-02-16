import pandas as pd
import asyncio
from backend.database import get_db, init_db, AsyncSessionLocal
from backend.models import MarketPrice
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import random

async def fetch_data(symbol):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(MarketPrice)
            .where(MarketPrice.symbol == symbol)
            .order_by(MarketPrice.timestamp.asc())
        )
        data = result.scalars().all()
        return [{"timestamp": d.timestamp, "price": d.price} for d in data]

async def populate_mock_data(symbol):
    print(f"Populating mock data for {symbol}...")
    async with AsyncSessionLocal() as session:
        # Check if data exists
        result = await session.execute(select(MarketPrice).where(MarketPrice.symbol == symbol).limit(1))
        if result.scalar():
            print("Data already exists.")
            return

        prices = []
        price = 10000.0
        start_time = datetime.utcnow() - timedelta(days=365)
        
        # Simulate price movement
        for i in range(365 * 24): # Hourly data for a year
            timestamp = start_time + timedelta(hours=i)
            change_percent = (random.random() - 0.5) * 0.02 # +/- 1%
            price *= (1 + change_percent)
            prices.append(MarketPrice(symbol=symbol, price=price, timestamp=timestamp))
        
        session.add_all(prices)
        await session.commit()
    print("Mock data populated.")

async def run_backtest(symbol):
    print(f"Running backtest for {symbol}...")
    
    # 1. Fetch Data
    raw_data = await fetch_data(symbol)
    
    if not raw_data:
        print("No data found.")
        return

    df = pd.DataFrame(raw_data)
    df.set_index('timestamp', inplace=True)
    
    # 2. Strategy: SMA Crossover (Simple Moving Average)
    # Calculate indicators
    df['SMA_50'] = df['price'].rolling(window=50).mean()
    df['SMA_200'] = df['price'].rolling(window=200).mean()
    
    # Generate Signals
    # 1 = Bullish (Long), -1 = Bearish (Short/Exit), 0 = Neutral
    df['Signal'] = 0
    # Bullish when short MA > long MA
    df.loc[df['SMA_50'] > df['SMA_200'], 'Signal'] = 1 
    # Bearish when short MA < long MA
    df.loc[df['SMA_50'] < df['SMA_200'], 'Signal'] = -1 
    
    # 3. Simulate Trades
    cash = 10000.0
    holdings = 0.0
    position = 0 # 0: Cash, 1: Long
    trades = []
    
    # Iterate through dataframe
    for i in range(1, len(df)):
        current_signal = df.iloc[i]['Signal']
        prev_signal = df.iloc[i-1]['Signal'] # Check for crossover
        price = df.iloc[i]['price']
        timestamp = df.index[i]
        
        # Buy Signal (Golden Cross)
        if current_signal == 1 and prev_signal != 1 and position == 0:
            holdings = cash / price
            cash = 0
            position = 1
            trades.append({'type': 'BUY', 'price': price, 'time': timestamp, 'val': holdings * price})
            # print(f"BUY at {price:.2f} on {timestamp}")
        
        # Sell Signal (Death Cross)
        elif current_signal == -1 and prev_signal != -1 and position == 1:
            cash = holdings * price
            holdings = 0
            position = 0
            trades.append({'type': 'SELL', 'price': price, 'time': timestamp, 'val': cash})
            # print(f"SELL at {price:.2f} on {timestamp}")

    # Final Value
    final_value = cash
    if position == 1:
        final_value = holdings * df.iloc[-1]['price']
        
    print(f"Initial Portfolio: $10000.00")
    print(f"Final Portfolio:   ${final_value:.2f}")
    roi = ((final_value - 10000)/10000)*100
    print(f"Return (ROI):      {roi:.2f}%")
    print(f"Total Trades:      {len(trades)}")
    
    # Benchmark (Buy and Hold)
    start_price = df.iloc[0]['price']
    end_price = df.iloc[-1]['price']
    benchmark_roi = ((end_price - start_price) / start_price) * 100
    print(f"Benchmark ROI:     {benchmark_roi:.2f}%")

async def main():
    await init_db()
    symbol = "BTC"
    await populate_mock_data(symbol)
    await run_backtest(symbol)

if __name__ == "__main__":
    asyncio.run(main())