import streamlit as st
from datetime import date, timedelta
import requests
from bs4 import BeautifulSoup
import re


def render_news_center():
    """新闻事件中心 - 收集宏观经济事件 (ForexFactory 爬虫)"""
    st.markdown("### 📰 新闻事件中心")
    st.caption('宏观经济事件日历 (来源: ForexFactory)')
    
    col_dates = st.columns(2)
    with col_dates[0]:
        start_date = st.date_input('开始日期', value=date(2026, 3, 1), key='news_start')
    with col_dates[1]:
        end_date = st.date_input('结束日期', value=date(2026, 4, 30), key='news_end')
    
    events = []
    
    try:
        weeks_to_fetch = 12
        current_week_start = date.today() - timedelta(days=date.today().weekday())
        
        for week_offset in range(weeks_to_fetch):
            week_start = current_week_start + timedelta(weeks=week_offset)
            if week_start > end_date:
                break
            
            url = f"https://www.forexfactory.com/calendar?week={week_start.strftime('%Y.%m.%d')}"
            headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                continue
            
            soup = BeautifulSoup(response.text, 'html.parser')
            rows = soup.find_all('tr', class_='calendar__row')
            
            current_date = None
            for row in rows:
                classes = row.get('class', [])
                
                if 'calendar__row--day-breaker' in classes:
                    colspan_cell = row.find('td', attrs={'colspan': '10'})
                    if colspan_cell:
                        date_text = colspan_cell.get_text(strip=True)
                        try:
                            match = re.search(r'([A-Z][a-z]{2})([A-Z][a-z]{2})\s*(\d{1,2})', date_text)
                            if match:
                                month_str = match.group(2)
                                day = int(match.group(3))  # Fixed
                                month_num = {'Jan':1,'Feb':2,'Mar':3,'Apr':4,'May':5,'Jun':6,
                                           'Jul':7,'Aug':8,'Sep':9,'Oct':10,'Nov':11,'Dec':12}[month_str]
                                current_date = date(week_start.year, month_num, day)
                        except:
                            pass
                    continue
                
                if not current_date:
                    continue
                
                if not (start_date <= current_date <= end_date):
                    continue
                
                cells = row.find_all('td', class_='calendar__cell')
                if len(cells) < 10:
                    continue
                
                if len(cells) == 11:
                    time_str = cells[1].get_text(strip=True)
                    currency = cells[2].get_text(strip=True)
                    impact_cell = cells[3]
                    event_name = cells[4].get_text(strip=True)
                    actual = cells[7].get_text(strip=True)
                    forecast = cells[8].get_text(strip=True)
                    previous = cells[9].get_text(strip=True)
                else:
                    time_str = cells[0].get_text(strip=True)
                    currency = cells[1].get_text(strip=True)
                    impact_cell = cells[2]
                    event_name = cells[3].get_text(strip=True)
                    actual = cells[6].get_text(strip=True)
                    forecast = cells[7].get_text(strip=True)
                    previous = cells[8].get_text(strip=True)
                
                if not event_name:
                    continue
                
                if currency != 'USD':
                    continue
                
                impact_span = impact_cell.find('span')
                impact_class = impact_span.get('class', []) if impact_span else []
                is_high_impact = any('red' in c for c in impact_class)
                if not is_high_impact:
                    continue
                
                event_type = '📊 经济数据'
                if any(kw in event_name.lower() for kw in ['rate', 'fed', 'fomc', 'powell', 'speech', 'testimony']):
                    event_type = '🏦 央行动态'
                
                events.append({
                    'date': current_date, 'time': time_str, 'type': event_type,
                    'name': event_name, 'detail': f"实际:{actual or '-'} 预测:{forecast or '-'} 前值:{previous or '-'}",
                    'impact': 'high', 'source': 'ForexFactory'
                })
                
    except Exception as e:
        pass
    
    seen = set()
    unique_events = []
    for e in events:
        key = (e['date'], e['name'])
        if key not in seen:
            seen.add(key)
            unique_events.append(e)
    events = unique_events
    
    known_events = [
        {'date': date(2025, 1, 29), 'type': '🏦 央行动态', 'name': '美联储FOMC利率决议', 'detail': '维持4.25-4.50%', 'impact': 'high'},
        {'date': date(2025, 3, 19), 'type': '🏦 央行动态', 'name': '美联储FOMC利率决议', 'detail': '维持4.25-4.50%', 'impact': 'high'},
        {'date': date(2025, 5, 7), 'type': '🏦 央行动态', 'name': '美联储FOMC利率决议', 'detail': '维持4.25-4.50%', 'impact': 'high'},
        {'date': date(2025, 6, 18), 'type': '🏦 央行动态', 'name': '美联储FOMC利率决议', 'detail': '降息25bp至4.00-4.25%', 'impact': 'high'},
        {'date': date(2025, 7, 30), 'type': '🏦 央行动态', 'name': '美联储FOMC利率决议', 'detail': '维持4.00-4.25%', 'impact': 'high'},
        {'date': date(2025, 9, 17), 'type': '🏦 央行动态', 'name': '美联储FOMC利率决议', 'detail': '降息25bp至3.75-4.00%', 'impact': 'high'},
        {'date': date(2025, 10, 29), 'type': '🏦 央行动态', 'name': '美联储FOMC利率决议', 'detail': '维持3.75-4.00%', 'impact': 'high'},
        {'date': date(2025, 12, 10), 'type': '🏦 央行动态', 'name': '美联储FOMC利率决议', 'detail': '降息25bp至3.50-3.75%', 'impact': 'high'},
        {'date': date(2026, 1, 28), 'type': '🏦 央行动态', 'name': '美联储FOMC利率决议', 'detail': '前值:3.50-3.75% 预测:维持', 'impact': 'high'},
        {'date': date(2026, 3, 18), 'type': '🏦 央行动态', 'name': '美联储FOMC利率决议', 'detail': '前值:3.50-3.75% 预测:维持', 'impact': 'high'},
        {'date': date(2026, 3, 19), 'type': '🏦 央行动态', 'name': '鲍威尔新闻发布会', 'detail': 'FOMC会后', 'impact': 'high'},
        {'date': date(2026, 4, 29), 'type': '🏦 央行动态', 'name': '美联储FOMC利率决议', 'detail': '前值:待公布 预测:待公布', 'impact': 'high'},
        {'date': date(2026, 4, 30), 'type': '🏦 央行动态', 'name': '鲍威尔新闻发布会', 'detail': 'FOMC会后', 'impact': 'high'},
        {'date': date(2026, 6, 10), 'type': '🏦 央行动态', 'name': '美联储FOMC利率决议', 'detail': '前值:待公布 预测:待公布', 'impact': 'high'},
        {'date': date(2026, 7, 29), 'type': '🏦 央行动态', 'name': '美联储FOMC利率决议', 'detail': '前值:待公布 预测:待公布', 'impact': 'high'},
        {'date': date(2026, 9, 16), 'type': '🏦 央行动态', 'name': '美联储FOMC利率决议', 'detail': '前值:待公布 预测:待公布', 'impact': 'high'},
        {'date': date(2026, 11, 4), 'type': '🏦 央行动态', 'name': '美联储FOMC利率决议', 'detail': '前值:待公布 预测:待公布', 'impact': 'high'},
        {'date': date(2026, 12, 16), 'type': '🏦 央行动态', 'name': '美联储FOMC利率决议', 'detail': '前值:待公布 预测:待公布', 'impact': 'high'},
    ]
    
    existing_keys = {(e['date'], e['name']) for e in events}
    for e in known_events:
        key = (e['date'], e['name'])
        if key not in existing_keys and start_date <= e['date'] <= end_date:
            events.append({**e, 'source': '内置日历'})
    
    st.markdown("---")
    with st.expander("➕ 手动添加事件"):
        col1, col2 = st.columns(2)
        with col1:
            new_date = st.date_input('日期', value=date.today(), key='new_event_date')
            new_type = st.selectbox('类型', ['📊 经济数据', '🏦 央行动态', '🎤 重要讲话', '📰 其他'], key='new_event_type')
        with col2:
            new_name = st.text_input('事件名称', key='new_event_name')
            new_detail = st.text_input('详情', key='new_event_detail')
        
        if st.button('添加', key='add_event_btn'):
            if new_name:
                events.append({
                    'date': new_date, 'time': '', 'type': new_type,
                    'name': new_name, 'detail': new_detail,
                    'impact': 'high', 'source': '手动添加'
                })
                st.success("已添加")
    
    events = [e for e in events if start_date <= e['date'] <= end_date]
    events = sorted(events, key=lambda x: x['date'])
    
    if not events:
        st.info("所选日期范围内暂无宏观事件数据")
        return
    
    st.markdown(f"**共 {len(events)} 个高影响事件**")
    
    for event in events:
        impact_color = {'high': '#ff4d4d', 'medium': '#ffa500', 'low': '#4caf50'}.get(event.get('impact', 'low'), '#888')
        time_str = event.get('time', '')
        source = event.get('source', '')
        
        with st.expander(f"{event['type']} | {event['date']} {time_str} | {event['name']}"):
            c1, c2, c3 = st.columns([1, 3, 1])
            c1.markdown(f"<span style='color:{impact_color};font-weight:bold;'>● 高影响</span>", unsafe_allow_html=True)
            c2.markdown(event['detail'])
            c3.caption(source)


render_news_center()
