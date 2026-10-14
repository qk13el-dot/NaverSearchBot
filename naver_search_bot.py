import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import urllib.request
import json
import datetime
from dotenv import load_dotenv
import tkinter as tk
from tkinter import messagebox
import matplotlib.pyplot as plt
import io
import matplotlib

# 한글 폰트 깨짐 방지 설정 (Windows 기준)
matplotlib.rcParams['font.family'] = 'Malgun Gothic'
matplotlib.rcParams['axes.unicode_minus'] = False

# .env 파일 로드 (로컬 테스트용, GitHub Actions에서는 시크릿 사용)
load_dotenv()

# 환경 변수 가져오기
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL", "qk13el@gmail.com")

# 설정 값 확인
if not all([NAVER_CLIENT_ID, NAVER_CLIENT_SECRET, SENDER_EMAIL, SENDER_PASSWORD, RECEIVER_EMAIL]):
    print("설정 오류: 환경 변수 값이 설정되지 않았습니다.")
    exit(1)

def get_naver_search_trend(keyword, time_unit, days_range):
    """네이버 API를 이용해 검색량 트렌드를 가져오는 함수"""
    url = "https://naverapihub.apigw.ntruss.com/search-trend/v1/search"
    
    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=days_range)
    
    body = {
        "startDate": start_date.strftime("%Y-%m-%d"),
        "endDate": today.strftime("%Y-%m-%d"),
        "timeUnit": time_unit,  # 'month' 또는 'date'
        "keywordGroups": [
            {
                "groupName": keyword,
                "keywords": [keyword]
            }
        ]
    }
    
    request = urllib.request.Request(url)
    request.add_header("X-NCP-APIGW-API-KEY-ID", NAVER_CLIENT_ID)
    request.add_header("X-NCP-APIGW-API-KEY", NAVER_CLIENT_SECRET)
    request.add_header("Content-Type", "application/json")
    
    try:
        response = urllib.request.urlopen(request, data=json.dumps(body).encode("utf-8"))
        rescode = response.getcode()
        if rescode == 200:
            response_body = response.read().decode('utf-8')
            result = json.loads(response_body)
            return result
        else:
            print(f"Error Code: {rescode}")
            return None
    except Exception as e:
        print(f"API 요청 중 에러 발생 ({keyword}): {e}")
        return None

def show_popup():
    """메일 전송 완료 팝업창을 최상단에 확실하게 띄우는 함수"""
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        messagebox.showinfo("네이버 검색봇", "메일을 보냈다!")
        root.destroy()
    except Exception as e:
        print(f"팝업창 출력 실패: {e}")

def create_trend_chart(monthly_data):
    """월간 검색량 추이 그래프를 생성하여 이미지 바이너리로 반환하는 함수"""
    plt.figure(figsize=(10, 5))
    
    for kw, periods in monthly_data.items():
        dates = [item.get('period') for item in periods]
        ratios = [item.get('ratio') for item in periods]
        plt.plot(dates, ratios, marker='o', linewidth=2, label=kw)
        
    plt.title('컴집 & 보아스 월간 검색량 추이 (최근 1년)', fontsize=14, fontweight='bold')
    plt.xlabel('월', fontsize=12)
    plt.ylabel('검색(클릭)량 상대지수', fontsize=12)
    plt.xticks(rotation=45)
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    
    img_stream = io.BytesIO()
    plt.savefig(img_stream, format='png', dpi=150)
    img_stream.seek(0)
    plt.close()
    return img_stream.read()

def send_email(html_content, chart_image_data):
    """이메일 및 그래프 이미지를 전송하는 함수"""
    today_str = datetime.date.today().strftime('%Y-%m-%d')
    msg = MIMEMultipart('related')
    msg['Subject'] = f"[일일 네이버 검색량 리포트] - {today_str} 기준"
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    
    msg_alt = MIMEMultipart('alternative')
    msg.attach(msg_alt)
    msg_alt.attach(MIMEText(html_content, 'html'))
    
    img_part = MIMEImage(chart_image_data, name="trend_chart.png")
    img_part.add_header('Content-ID', '<trend_chart>')
    msg.attach(img_part)
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        server.quit()
        print("이메일 전송 성공!")
        show_popup()
    except Exception as e:
        print(f"이메일 전송 실패: {e}")

def main():
    keywords = ["컴집", "보아스"]
    
    # 1. 월간 그래프용 데이터 수집 (최근 365일)
    monthly_report_data = {}
    for kw in keywords:
        data = get_naver_search_trend(kw, "month", 365)
        if data and 'results' in data:
            monthly_report_data[kw] = data['results'][0]['data']
            
    # 2. 일일 상세 데이터 수집 (최근 25일 확보)
    daily_report_data = {}
    for kw in keywords:
        data = get_naver_search_trend(kw, "date", 25)
        if data and 'results' in data:
            daily_report_data[kw] = data['results'][0]['data']
            
    if not monthly_report_data or not daily_report_data:
        print("수집된 데이터가 없습니다.")
        return

    # 월간 데이터로 그래프 생성
    chart_img = create_trend_chart(monthly_report_data)

    # HTML 본문 구성
    today_str = datetime.date.today().strftime('%Y-%m-%d')
    html = f"<h2>[일일 네이버 검색량 리포트] - {today_str} 기준</h2>"
    
    for kw, periods in daily_report_data.items():
        # 네이버 API가 제공하는 데이터 중 가장 최신 날짜를 찾되, 
        # 만약 API가 아직 어제/오늘 데이터를 갱신 안 했다면 제공되는 최신 데이터를 기준으로 잡음
        if not periods:
            continue
            
        latest_item = periods[-1]
        latest_date = latest_item.get('period')
        
        # 최신일 기준 뒤에서 7일치 추출
        recent_7 = periods[-7:] if len(periods) >= 7 else periods
        
        # 최신일 인덱스 찾기
        latest_idx = len(periods) - 1
        for idx, item in enumerate(periods):
            if item.get('period') == latest_date:
                latest_idx = idx
                break
                
        latest_ratio = periods[latest_idx].get('ratio', 0)
        prev_ratio = periods[latest_idx - 1].get('ratio', 0) if latest_idx > 0 else 0
        week_ago_item = periods[latest_idx - 7] if latest_idx >= 7 else None
        
        # 추정 검색수 계산
        estimated_count = int(latest_ratio * 15)
        
        # 전일 대비 증감
        if prev_ratio > 0:
            diff_prev = latest_ratio - prev_ratio
            pct_prev = (diff_prev / prev_ratio) * 100
            pct_prev_str = f"▲ +{pct_prev:.1f}%" if diff_prev > 0 else (f"▼ {pct_prev:.1f}%" if diff_prev < 0 else "0.0%")
        else:
            pct_prev_str = "-"

        # 전주 동요일 대비 증감
        pct_week_str = "-"
        if week_ago_item:
            week_ratio = week_ago_item.get('ratio', 0)
            if week_ratio > 0:
                diff_week = latest_ratio - week_ratio
                pct_week = (diff_week / week_ratio) * 100
                pct_week_str = f"▲ +{pct_week:.1f}%" if diff_week > 0 else (f"▼ {pct_week:.1f}%" if diff_week < 0 else "0.0%")

        # 요약 (Summary) 섹션 구성
        html += f"<hr><h3>■ 요약 (Summary) - [{kw}]</h3>"
        html += f"<ul>"
        html += f"<li><b>기준 키워드</b>: {kw}</li>"
        html += f"<li><b>최근 기준일 ({latest_date}) 추정 검색량</b>: 약 {estimated_count:,} 회 (상대지수: {latest_ratio})</li>"
        html += f"<li><b>전일 대비 증감</b>: {pct_prev_str}</li>"
        html += f"<li><b>전주 동요일 대비 증감</b>: {pct_week_str}</li>"
        html += f"</ul>"

        # 최근 7일간 검색 추이 표
        html += f"<h4>■ 최근 7일간 검색 추이 ({kw})</h4>"
        html += "<table border='1' cellspacing='0' cellpadding='6' style='border-collapse: collapse; text-align: center; margin-bottom: 15px; width: 100%; max-width: 550px;'>"
        html += "<tr style='background-color: #f2f2f2;'><th>날짜</th><th>상대지수</th><th>추정 검색수</th><th>전일 대비 증감</th></tr>"
        
        for i in range(len(recent_7)):
            curr = recent_7[i]
            c_date = curr.get('period')
            c_ratio = curr.get('ratio')
            c_est = int(c_ratio * 15)
            
            if i > 0:
                p_ratio = recent_7[i-1].get('ratio', 0)
                if p_ratio > 0:
                    d_pct = ((c_ratio - p_ratio) / p_ratio) * 100
                    d_str = f"+{d_pct:.1f}%" if d_pct > 0 else f"{d_pct:.1f}%"
                else:
                    d_str = "-"
            else:
                d_str = "-"
                
            html += f"<tr><td>{c_date}</td><td>{c_ratio}</td><td><b>{c_est:,}회</b></td><td>{d_str}</td></tr>"
            
        html += "</table>"

        # 인사이트 및 특이사항 자동 도출
        html += f"<h4>■ 인사이트 및 특이사항 ({kw})</h4>"
        html += f"<ul>"
        if latest_ratio >= prev_ratio:
            html += f"<li>최근 기준일({latest_date}) 기준 검색 유입량이 전일 대비 안정적인 상승세를 보이고 있습니다.</li>"
        else:
            html += f"<li>최근 기준일({latest_date}) 기준 검색 유입량이 전일 대비 소폭 조정을 받고 있습니다.</li>"
        html += f"<li>최근 7일 데이터 흐름을 모니터링하여 요일별 트래픽 패턴을 지속 점검 권장합니다.</li>"
        html += f"</ul>"

    # 월간 그래프 이미지 삽입 섹션
    html += "<hr><h3>■ 월간 검색 추이 그래프 (최근 1년)</h3>"
    html += "<img src='cid:trend_chart' style='width:100%; max-width:700px; height:auto;'><br>"
    
    # 이메일 발송
    send_email(html, chart_img)

if __name__ == "__main__":
    main()
