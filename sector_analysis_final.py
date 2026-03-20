import sys
import os
# sys.path.append(os.path.join(os.getcwd(), 'src'))
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import FinanceDataReader as fdr
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import json
import os
import re
import warnings
import argparse

warnings.filterwarnings('ignore')

def get_sector_list():
    """Scrapes the industry list from Naver Finance."""
    url = "https://finance.naver.com/sise/sise_group.naver?type=upjong"
    res = requests.get(url)
    res.raise_for_status()
    res.encoding = 'euc-kr'
    soup = BeautifulSoup(res.text, 'html.parser')
    
    sectors = []
    # Find all industry links - adjusted selector for upjong page
    links = soup.select('table.type_1 td a')
    for link in links:
        if 'sise_group_detail.naver' in link['href']:
            name = link.text.strip()
            no_match = re.search(r'no=(\d+)', link['href'])
            if no_match:
                no = no_match.group(1)
                sectors.append({'name': name, 'no': no})
    return sectors

def get_stocks_in_sector(sector_no):
    """Scrapes all stocks in a specific sector from Naver Finance."""
    url = f"https://finance.naver.com/sise/sise_group_detail.naver?type=upjong&no={sector_no}"
    res = requests.get(url)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, 'html.parser')
    
    stocks = []
    # Find stock names and codes from the detail table
    rows = soup.select('div.box_type_l table tr')
    for row in rows:
        name_cell = row.select_one('td.name a')
        if name_cell:
            name = name_cell.text.strip()
            code = re.search(r'code=(\d+)', name_cell['href']).group(1)
            stocks.append({'name': name, 'code': code})
    return stocks

def calculate_gains(stocks, today, marcap_df):
    """Calculates gains for various periods for a list of stocks."""
    periods = {
        '1W': today - timedelta(weeks=1),
        '1M': today - timedelta(days=30),
        '3M': today - timedelta(days=90),
        '6M': today - timedelta(days=180),
        '1Y': today - timedelta(days=365),
        '2Y': today - timedelta(days=365*2),
        '3Y': today - timedelta(days=365*3),
        '4Y': today - timedelta(days=365*4),
        'YTD': datetime(today.year, 1, 1)
    }
    
    results = []
    for stock in stocks:
        code = stock['code']
        name = stock['name']
        try:
            marcap = 0
            if code in marcap_df.index:
                marcap = marcap_df.loc[code, 'Marcap']
            
            start_date = (min(periods.values()) - timedelta(days=5)).strftime('%Y-%m-%d')
            df = fdr.DataReader(code, start_date)
            
            if df is None or len(df) < 2:
                continue
                
            current_price = df['Close'].iloc[-1]
            stock_res = {'code': code, 'name': name, 'Marcap': marcap, 'current_price': current_price}
            
            for p_name, p_date in periods.items():
                past_data = df.loc[:p_date.strftime('%Y-%m-%d')]
                if not past_data.empty:
                    past_price = past_data['Close'].iloc[-1]
                    if past_price > 0:
                        stock_res[p_name] = ((current_price - past_price) / past_price) * 100
            
            results.append(stock_res)
        except Exception:
            continue
            
    return pd.DataFrame(results)

def create_treemap(df_sectors, df_stocks, last_updated_str):
    """Creates an interactive TreeMap of Sectors and a JS-powered text list for Stocks."""
    print("Generating Enhanced TreeMap/List hybrid visualization...")
    
    periods = ['1W', '1M', '3M', '6M', '1Y', '2Y', '3Y', '4Y', 'YTD']
    fig = go.Figure()
    
    # 1. Create Traces for each period
    for p in periods:
        fig.add_trace(go.Treemap(
            labels=df_sectors['sector_name'],
            parents=[""] * len(df_sectors),
            values=df_sectors['total_marcap'],
            textinfo="label+value+text",
            text=df_sectors[p].apply(lambda x: f"{x:+.2f}%"),
            marker=dict(
                colors=df_sectors[p],
                colorscale='RdYlGn',
                cmid=0,
                cmin=-15,
                cmax=15,
                colorbar=dict(title=f"{p} Gain (%)", thickness=20)
            ),
            visible=(p == '1M'), # Default visible
            name=p,
            hovertemplate="<b>%{label}</b><br>Market Cap: %{value:,.0f} KRW<br>Gain: %{text}<extra></extra>"
        ))

    # 2. Add Buttons to switch periods
    buttons = []
    for i, p in enumerate(periods):
        visible = [False] * len(periods)
        visible[i] = True
        buttons.append(dict(
            label=p,
            method="update",
            args=[{"visible": visible}, {"title": f"Sector Performance Heatmap ({p})"}]
        ))

    fig.update_layout(
        updatemenus=[dict(
            type="buttons",
            direction="right",
            active=1,
            x=0.5,
            xanchor="center",
            y=1.1,
            buttons=buttons
        )],
        title="Sector Performance Heatmap (1M)",
        margin=dict(t=80, l=10, r=10, b=10)
    )

    # 3. Export to HTML with custom JS for the list
    plot_id = "main-treemap"
    plot_html = fig.to_html(full_html=False, include_plotlyjs='cdn', div_id=plot_id)
    
    period_cols = ['1W', '1M', '3M', '6M', '1Y', '2Y', '3Y', '4Y', 'YTD']
    stocks_json_data = df_stocks[['name', 'sector_name', 'Marcap'] + period_cols].to_dict(orient='records')
    stocks_json_str = json.dumps(stocks_json_data, ensure_ascii=False)

    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Sector Analysis Dashboard</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
        <style>
            body {{ font-family: 'Inter', sans-serif; background: #0d1117; color: #c9d1d9; margin:0; padding: 20px; }}
            #dashboard-container {{ max-width: 1400px; margin: auto; }}
            #header-section {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid #333; padding-bottom: 15px; }}
            h2 {{ color: #4caf50; font-size: 2em; margin: 0; letter-spacing: -0.5px; }}
            #meta-info {{ display: flex; flex-direction: column; align-items: flex-end; gap: 8px; }}
            #last-updated {{ font-size: 0.9em; color: #8b949e; }}
            #refresh-btn {{ background: #238636; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 0.9em; transition: background 0.2s; }}
            #refresh-btn:hover {{ background: #2ea043; }}
            .stock-list-container {{ margin-top: 30px; background: #161b22; border-radius: 12px; padding: 25px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
            .stock-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 15px; margin-top: 20px; }}
            .stock-card {{ background: #21262d; border: 1px solid #30363d; border-radius: 8px; padding: 15px; transition: transform 0.2s; }}
            .stock-card:hover {{ transform: translateY(-3px); border-color: #58a6ff; }}
            .stock-name {{ font-weight: 800; font-size: 1.1em; color: #f0f6fc; margin-bottom: 10px; }}
            .metric-group {{ display: flex; flex-direction: column; gap: 5px; }}
            .metric-row {{ display: flex; justify-content: space-between; font-size: 0.9em; }}
            .metric-active {{ color: #58a6ff; font-weight: 600; background: rgba(88,166,255,0.1); padding: 2px 5px; border-radius: 4px; }}
            .gain-pos {{ color: #3fb950; }}
            .gain-neg {{ color: #f85149; }}
            .gain-zero {{ color: #8b949e; }}
            #selection-prompt {{ text-align: center; color: #8b949e; padding: 40px; font-style: italic; }}
        </style>
    </head>
    <body>
        <div id="dashboard-container">
            <div id="header-section">
                <h2>Market Sector Dashboard</h2>
                <div id="meta-info">
                    <span id="last-updated">🕒 Last Updated: {last_updated_str}</span>
                    <button id="refresh-btn" onclick="handleRefresh()">🔄 Refresh Data</button>
                </div>
            </div>
            <script>
                window.currentSector = null;
                window.timeframes = ['1W', '1M', '3M', '6M', '1Y', '2Y', '3Y', '4Y', 'YTD'];
                function handleRefresh() {{
                    alert("To fetch the latest real-time data, please run the script in your terminal with the refresh flag:\\n\\npython sector_analysis_final.py --refresh");
                }}
            </script>
            <div id="chart-area">{plot_html}</div>
            <div class="stock-list-container">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px; margin-bottom: 20px;">
                    <div id="selected-sector-title" style="font-size: 1.5em; font-weight:800; color:#58a6ff;">Select a Sector from the Heatmap</div>
                    <input type="text" id="search-input" placeholder="🔍 Search stock name..." onkeyup="handleSearch()" style="background: #0d1117; border: 1px solid #30363d; color: white; padding: 10px 20px; border-radius: 25px; width: 300px; outline: none; transition: border-color 0.2s;">
                </div>
                <div id="stock-list" class="stock-grid"><div id="selection-prompt">Click a sector box to view constituent stocks and their performance.</div></div>
            </div>
        </div>
        <script>
            const allStocks = {stocks_json_str};
            const PLOT_ID = '{plot_id}';
            
            function handleSearch() {{
                if(window.currentSector) {{
                    renderStockList(window.currentSector);
                }} else {{
                    renderStockList(null);
                }}
            }}

            function renderStockList(sector) {{
                const gd = document.getElementById(PLOT_ID);
                if(!gd && sector) return;
                
                let activeTF = '1M';
                if(gd) {{
                    for(let i=0; i<gd.data.length; i++) {{
                        if(gd.data[i].visible === true) {{
                            activeTF = gd.data[i].name;
                            break;
                        }}
                    }}
                }}
                
                const searchTerm = document.getElementById('search-input').value.toLowerCase();
                const filtered = allStocks.filter(s => {{
                    const matchesSector = sector ? s.sector_name === sector : true;
                    const matchesSearch = s.name.toLowerCase().includes(searchTerm);
                    return matchesSector && matchesSearch;
                }});
                
                // Sort by Marcap descending
                filtered.sort((a,b) => (b.Marcap || 0) - (a.Marcap || 0));
                
                const titleDiv = document.getElementById('selected-sector-title');
                const listDiv = document.getElementById('stock-list');
                
                if(sector) {{
                    titleDiv.innerText = "⭐ " + sector + " (" + activeTF + " Performance)";
                }} else if(searchTerm) {{
                    titleDiv.innerText = "🔍 Search Results: '" + searchTerm + "'";
                }} else {{
                    titleDiv.innerText = "Select a Sector from the Heatmap";
                }}
                
                listDiv.innerHTML = "";
                if(filtered.length === 0) {{
                    listDiv.innerHTML = "<div id='selection-prompt' style='grid-column: 1/-1;'>No stocks found matching the criteria.</div>";
                    return;
                }}
                
                const getGainClass = (v) => v > 0 ? 'gain-pos' : (v < 0 ? 'gain-neg' : 'gain-zero');
                const getGainStr = (v) => v !== undefined ? (v > 0 ? "+" : "") + v.toFixed(2) + "%" : "N/A";
                const formatMarcap = (v) => v ? (v / 1e12).toFixed(1) + "T ₩" : "N/A";

                filtered.forEach(s => {{
                    let html = "<div class='stock-card'>";
                    html += "<div style='display:flex; justify-content:space-between; align-items:start; margin-bottom: 10px;'>";
                    html += "<div class='stock-name'>" + s.name + "</div>";
                    html += "<div style='font-size:0.75em; color:#8b949e; background:#30363d; padding:2px 6px; border-radius:4px; white-space:nowrap;'>" + formatMarcap(s.Marcap) + "</div>";
                    html += "</div>";
                    html += "<div class='metric-group'>";
                    ['1W', '1M', '1Y', '3Y'].forEach(tf => {{
                        const isActive = (tf === activeTF);
                        const val = s[tf];
                        html += "<div class='metric-row" + (isActive ? " metric-active" : "") + "'>";
                        html += "<span>" + tf + " Gain:</span>";
                        html += "<span class='" + getGainClass(val) + "'>" + getGainStr(val) + "</span>";
                        html += "</div>";
                    }});
                    html += "</div></div>";
                    listDiv.innerHTML += html;
                }});
            }}

            window.onload = function() {{
                const gd = document.getElementById(PLOT_ID);
                gd.on('plotly_click', function(data) {{
                    const sector = data.points[0].label;
                    window.currentSector = sector;
                    renderStockList(sector);
                }});
                gd.on('plotly_restyle', function() {{
                    if(window.currentSector) renderStockList(window.currentSector);
                }});
            }}
        </script>
    </body>
    </html>
    """
    with open("sector_performance_heatmap.html", "w", encoding='utf-8') as f:
        f.write(full_html)
    print("Hybrid Heatmap/List saved to sector_performance_heatmap.html")

def main():
    parser = argparse.ArgumentParser(description="Sector Analysis Dashboard Generator")
    parser.add_argument('--refresh', action='store_true', help='Force refresh data from Naver Finance')
    args = parser.parse_args()

    today = datetime.now()
    last_updated_str = today.strftime('%Y-%m-%d %H:%M:%S')
    results_file = 'sector_analysis_results.csv'
    stock_details_file = 'sector_stock_details.csv'
    
    if not args.refresh and os.path.exists(results_file) and os.path.exists(stock_details_file):
        print("Existing results found. Loading for visualization...")
        mtime = os.path.getmtime(results_file)
        last_updated_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
        df_results = pd.read_csv(results_file)
        df_stocks = pd.read_csv(stock_details_file)
        create_treemap(df_results, df_stocks, last_updated_str)
        return

    print("Fetching global market cap data for weighting...")
    try:
        krx_stocks = fdr.StockListing('KRX')
        marcap_df = krx_stocks.set_index('Code')[['Marcap']]
    except Exception:
        marcap_df = pd.DataFrame()

    REPRESENTATIVE_SECTORS = ["반도체와반도체장비", "자동차", "제약", "생물공학", "전기장비", "IT서비스", "은행", "조선", "화학", "철강", "건설", "게임엔터테인먼트", "화장품", "항공사", "에너지장비및서비스", "식품", "기계", "우주항공과국방"]
    full_sectors = get_sector_list()
    print(f"Total sectors found: {len(full_sectors)}")
    sectors = [s for s in full_sectors if s['name'] in REPRESENTATIVE_SECTORS]
    print(f"Matched representative sectors: {len(sectors)}")
    
    if not sectors:
        print("Available sectors on Naver:")
        for s in full_sectors[:10]:
            print(f"- {s['name']}")
        return
    
    all_stocks_data = []
    all_sector_data = []
    
    for sector in sectors:
        print(f"Processing {sector['name']}...", end=' ', flush=True)
        stocks = get_stocks_in_sector(sector['no'])
        if not stocks: continue
        
        df_gains = calculate_gains(stocks, today, marcap_df)
        if df_gains.empty: continue
        
        df_gains['sector_name'] = sector['name']
        all_stocks_data.append(df_gains)
        
        sector_summary = {'sector_name': sector['name'], 'stock_count': len(df_gains), 'total_marcap': df_gains['Marcap'].sum()}
        for p in ['1W', '1M', '3M', '6M', '1Y', '2Y', '3Y', '4Y', 'YTD']:
            valid_gains = df_gains.dropna(subset=[p])
            if not valid_gains.empty:
                w = valid_gains['Marcap'] + 1
                sector_summary[p] = np.average(valid_gains[p], weights=w)
        all_sector_data.append(sector_summary)
        print("Done.")

    df_results = pd.DataFrame(all_sector_data)
    df_stocks = pd.concat(all_stocks_data)
    df_results.to_csv(results_file, index=False)
    df_stocks.to_csv(stock_details_file, index=False)
    create_treemap(df_results, df_stocks, last_updated_str)

if __name__ == "__main__":
    main()
