# 🇰🇷 K-StockFlow: Sector Analysis Dashboard

![K-StockFlow Dashboard](https://img.shields.io/badge/Status-Live-success)
![Data Source](https://img.shields.io/badge/Source-Naver%20Finance-blue)
![Update Frequency](https://img.shields.io/badge/Update-Daily-orange)

An interactive, high-performance treemap dashboard for the Korean stock market, focusing on **18 Representative Sectors** including semiconductors, robotics, and aerospace.

## 🚀 Key Features

- **Interactive TreeMap**: Visual overview of sector performance across multiple timeframes.
- **Constituent Cards**: Detailed stock-level data including **1W, 1M, 1Y, and 3Y** gains.
- **Dynamic Sorting**: Instant sorting of constituent stocks based on the selected timeframe.
- **Automated Updates**: Powered by GitHub Actions to refresh data daily after market close.

## 🛠 Tech Stack

- **Python**: `FinanceDataReader`, `Pandas`, `Plotly`
- **Frontend**: HTML5, Vanilla JS, Plotly.js
- **Automation**: GitHub Actions

## 📦 Local Setup

1. **Clone the repo**:
   ```bash
   git clone https://github.com/sdm6410/StockFlow-KR.git
   cd StockFlow-KR
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the analysis**:
   ```bash
   python sector_analysis_final.py --refresh
   ```

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
