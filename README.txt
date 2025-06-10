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

## 🗂️ Project Structure

### Environment Configuration

Create a `.env` file based on `.env.example` and populate your API keys. At a minimum,
set `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` to enable live or paper stock trading
through Alpaca.

To use the optional AI strategist module, set `OPENAI_API_KEY` and enable it with
`ENABLE_AI_STRATEGY=true`.  The application now loads `.env` automatically so the
key is picked up even when modules are imported before the configuration stage.

Additional market data feeds are available including real-time bars from Alpaca
and price polling from CoinGecko.

To let the bot automatically suggest a few trending symbols each day, set
`ENABLE_AI_ASSET_DISCOVERY=true` in your `.env`.  Provide a comma separated list
of your preferred `TRADE_SYMBOLS` which will remain intact while any AI picked
symbols are added on top.

The new `OpportunityScanner` leverages CoinGecko trending data and sentiment
signals to surface promising assets. Temporary symbols will be added for one
hour when discovered.
