import os
import json
import urllib.request
import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# .env 파일에서 환경 변수 불러오기
load_dotenv()

# ==========================================
# 1. 설정 정보 (환경 변수 로드)
# ==========================================
CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")

# 환경 변수 누락 체크
missing_vars = []
if not CLIENT_ID: missing_vars.append("NAVER_CLIENT_ID")
if not CLIENT_SECRET: missing_vars.append("NAVER_CLIENT_SECRET")
if not SENDER_EMAIL: missing_vars.append("SENDER_EMAIL")
if not SENDER_PASSWORD: missing_vars.append("SENDER_PASSWORD")
if not RECEIVER_EMAIL: missing_vars.append("RECEIVER_EMAIL")

if missing_vars:
    print(f"❌ 설정 오류: .env 파일에 다음 값이 설정되지 않았습니다: {', '.join(missing_vars)}")
    exit(1)

# 조회할 키워드 설정
KEYWORDS = ["컴집", "보아스"]


def get_naver_datalab_data():
    url = "https://naverapihub.apigw.ntruss.com/search-trend/v1/search"
    
    # 오늘 기준 최근 30일 데이터 조회 설정 (오늘 제외 어제까지)
    today = datetime.date.today()
    start_date = (today - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
    end_date = (today - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    # API 요청 바디 구성
    keyword_groups = [{"groupName": kw, "keywords": [kw]} for kw in KEYWORDS]
    
    body = {
        "startDate": start_date,
        "endDate": end_date,
        "timeUnit": "date",
        "keywordGroups": keyword_groups
    }
    
    request = urllib.request.Request(url, method="POST")
    request.add_header("X-NCP-APIGW-API-KEY-ID", CLIENT_ID)
    request.add_header("X-NCP-APIGW-API-KEY", CLIENT_SECRET)
    request.add_header("Content-Type", "application/json")
    
    try:
        response = urllib.request.urlopen(request, data=json.dumps(body).encode("utf-8"))
        rescode = response.getcode()
        if rescode == 200:
            response_body = response.read()
            return json.loads(response_body.decode('utf-8'))
        else:
            print(f"❌ Error Code: {rescode}")
            return None
    except urllib.error.HTTPError as e:
        print(f"❌ API HTTP 에러 발생 ({e.code}): {e.reason}")
        if e.code == 401:
            print("👉 API Key ID 또는 API Key 값이 정확한지 확인해 주세요.")
        return None
    except Exception as e:
        print(f"❌ API 호출 중 예외 발생: {e}")
        return None


def format_report(data):
    if not data or "results" not in data:
        return "데이터를 불러오지 못했습니다."
    
    report_lines = []
    report_lines.append(f"📊 [네이버 검색량 일일 리포트] ({datetime.date.today().strftime('%Y-%m-%d')})\n")
    
    for item in data["results"]:
        title = item["title"]
        report_lines.append(f"키워드: **{title}**")
        recent_data = item["data"][-5:]
        for d in recent_data:
            # 수정된 부분: API 응답의 날짜 필드인 'period' 사용
            report_lines.append(f"  - {d['period']}: 상대 검색량 {d['ratio']}")
        report_lines.append("")
        
    return "\n".join(report_lines)


def send_email(subject, content):
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    
    msg.attach(MIMEText(content, 'plain', 'utf-8'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        server.quit()
        print("✅ 이메일 전송 성공!")
    except Exception as e:
        print(f"❌ 이메일 전송 실패: {e}")


if __name__ == "__main__":
    print("🚀 네이버 검색량 데이터 수집 중...")
    api_data = get_naver_datalab_data()
    
    if api_data:
        report_content = format_report(api_data)
        print(report_content)
        send_email("[자동화] 네이버 검색량 일일 리포트", report_content)
    else:
        print("⚠️ 데이터 수집 실패로 이메일을 발송하지 않습니다.")