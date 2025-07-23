# Lysara Investments – Automated Multi-Market Trading System

Lysara Investments is a unified, modular trading engine designed to execute algorithmic strategies across multiple asset classes including cryptocurrency, stocks, and forex.

## 💡 Features

- ✅ Modular architecture with plug-and-play API and strategy modules
- 📊 Streamlit dashboard for live monitoring and controls
- 🧠 Technical and sentiment-based strategies
- 🛡️ Centralized risk management system
- 🔄 Fully asynchronous and expandable
- 🚦 Signal fusion engine combining technical and sentiment data
- 🔍 Opportunity scanner for trending coins
- 📈 Market state monitor via CoinGecko
- 🔌 Dynamic strategy loader
- 💬 Uses GPT-4o for AI-driven trade reasoning
- 🔥 Conviction heatmap and AI thought feed on the dashboard
- 🌑 Dark theme with real-time equity curve

## 🗂️ Project Structure

### Environment Configuration

Create a `.env` file based on `.env.example` and populate your API keys. At a minimum,
set `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` to enable live or paper stock trading
through Alpaca.

For cryptocurrency trading we now integrate with **Binance**. Set
`BINANCE_API_KEY` and `BINANCE_SECRET_KEY` in your `.env`.
Legacy Coinbase keys are still supported for compatibility but are no longer
required.

For Alpaca, `ALPACA_BASE_URL` should be the root URL such as
`https://paper-api.alpaca.markets` (without `/v2`). Including `/v2` will produce
404 errors like `.../v2/v2/positions`.

To use the optional AI strategist module, set `OPENAI_API_KEY` and enable it with
`ENABLE_AI_STRATEGY=true`.  The application now loads `.env` automatically so the
key is picked up even when modules are imported before the configuration stage.

Additional market data feeds are available including real-time bars from Alpaca
and price polling from CoinGecko.

To let the bot automatically suggest a few trending symbols each day, set
`ENABLE_AI_ASSET_DISCOVERY=true` in your `.env`.  Provide a comma separated list
of your preferred `TRADE_SYMBOLS` which will remain intact while any AI picked
symbols are added on top.

Set `FOREX_ENABLED=true` and provide `OANDA_API_KEY` and `OANDA_ACCOUNT_ID`
if you want to enable forex trading. When not set, all forex related features
in the dashboard and launcher are hidden.

The new `OpportunityScanner` leverages CoinGecko trending data and sentiment
signals to surface promising assets. Temporary symbols will be added for one
hour when discovered.

## Testing Notes

When running the bot in simulation mode after these Binance upgrades,
verify the following:

1. **Market Data** – prices from Binance WebSocket should stream without
   errors and update your logs.
2. **Account Info** – `fetch_account_info` and `fetch_holdings` must return
   reasonable balances from Binance or mock values in simulation.
3. **Order Execution** – simulated orders should log correctly and update the
   `SimulatedPortfolio`; when live trading is enabled, ensure orders are
   accepted by Binance.
4. **Strategy Inputs** – confirm strategies reference sentiment scores from
   CryptoPanic, NewsAPI and Reddit when generating trade decisions.
