import os
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from openai import OpenAI
from typing import List, Dict
import resend
import schedule
import time
from dotenv import load_dotenv
import json

# 환경 변수 로드
load_dotenv()

# 설정
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
RESEND_API_KEY = os.getenv('RESEND_API_KEY')
EMAIL_FROM = os.getenv('EMAIL_FROM', 'blog@company.com')
# EMAIL_TO = os.getenv('EMAIL_TO', '').split(',')
EMAIL_TO='gyu3637@gmail.com'

# API 키 설정
client = OpenAI(api_key=OPENAI_API_KEY)
resend.api_key = RESEND_API_KEY

# RSS 피드 소스
RSS_FEEDS = [
    'https://techcrunch.com/feed/',
    'https://www.theverge.com/rss/index.xml',
    'https://feeds.feedburner.com/TechCrunch/startups',
    'https://www.wired.com/feed/rss',
    'https://feeds.arstechnica.com/arstechnica/technology-lab',
]

class ITTrendAnalyzer:
    def __init__(self):
        self.articles = []
        
    def fetch_rss_feeds(self) -> List[Dict]:
        """RSS 피드에서 최신 기사 수집"""
        all_articles = []
        
        for feed_url in RSS_FEEDS:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:5]:  # 각 피드에서 최신 5개로 증가
                    article = {
                        'title': entry.title,
                        'link': entry.link,
                        'summary': entry.get('summary', ''),
                        'published': entry.get('published_parsed', ''),
                        'source': feed.feed.title
                    }
                    all_articles.append(article)
            except Exception as e:
                print(f"Error fetching {feed_url}: {e}")
                
        return all_articles
    
    def fetch_hacker_news(self) -> List[Dict]:
        """Hacker News 상위 스토리 수집"""
        articles = []
        try:
            # Top stories API
            response = requests.get('https://hacker-news.firebaseio.com/v0/topstories.json')
            story_ids = response.json()[:10]  # 상위 10개로 증가
            
            for story_id in story_ids:
                story_response = requests.get(f'https://hacker-news.firebaseio.com/v0/item/{story_id}.json')
                story = story_response.json()
                
                if story and story.get('type') == 'story':
                    article = {
                        'title': story.get('title', ''),
                        'link': story.get('url', ''),
                        'summary': f"HN Score: {story.get('score', 0)} | Comments: {story.get('descendants', 0)}",
                        'published': datetime.fromtimestamp(story.get('time', 0)),
                        'source': 'Hacker News'
                    }
                    articles.append(article)
        except Exception as e:
            print(f"Error fetching Hacker News: {e}")
            
        return articles
    
    def filter_recent_articles(self, articles: List[Dict], days: int = 1) -> List[Dict]:
        """최근 N일 이내 기사만 필터링"""
        cutoff_date = datetime.now() - timedelta(days=days)
        filtered = []
        
        for article in articles:
            try:
                # 발행일 파싱
                if isinstance(article['published'], tuple):
                    pub_date = datetime(*article['published'][:6])
                elif isinstance(article['published'], datetime):
                    pub_date = article['published']
                else:
                    continue
                    
                if pub_date > cutoff_date:
                    filtered.append(article)
            except:
                continue
                
        # 상위 10개로 증가 (더 많은 컨텍스트 제공)
        return filtered[:10]
    
    def analyze_with_gpt(self, articles: List[Dict]) -> str:
        """GPT를 사용해 트렌드 분석 및 블로그 포스트 생성"""
        # 기사 정보 준비 - 상위 5개만 사용하여 입력 토큰 절감
        top_articles = articles[:5]
        articles_text = "\n".join([
            f"{i+1}. {a['title']} ({a['source']})"
            for i, a in enumerate(top_articles)
        ])
        
        prompt = f"""IT 뉴스 분석하여 3000자 한국어 블로그 작성

[뉴스 제목]
{articles_text}

[작성 요구사항]
분량: 총 3000자
구성:
- 서론(300자): 오늘의 핵심 3가지 트렌드 소개
- 트렌드1(900자): 현황/기술배경/한국시장영향/실무적용
- 트렌드2(900자): 동일 구조
- 트렌드3(900자): 동일 구조  
- 결론(300자): 트렌드 연관성과 액션아이템

스타일: 전문적이면서 실용적, 한국 기업 사례 포함
형식: 마크다운(###,####), **굵은글씨**, [링크](URL)

각 트렌드는 구체적 데이터와 실무 인사이트 필수"""
        
        try:
            # 토큰 최적화 설정
            response = client.chat.completions.create(
                model="gpt-3.5-turbo-16k",  # 비용 효율적인 모델로 변경
                messages=[
                    {"role": "system", "content": "IT 전문 기자. 간결하고 인사이트 있는 분석 제공."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2500  # 토큰 수 감소
            )
            
            return response.choices[0].message.content
        except Exception as e:
            print(f"GPT 분석 오류: {e}")
            return None

class EmailSender:
    def __init__(self):
        self.api_key = RESEND_API_KEY
        
    def send_blog_post(self, content: str, recipients: List[str]):
        """Resend API를 사용해 블로그 포스트를 이메일로 발송"""
        subject = f"[IT 트렌드 심층분석] {datetime.now().strftime('%Y년 %m월 %d일')} - 오늘 꼭 알아야 할 Tech 인사이트"
        
        # HTML 버전 생성
        html_content = self._markdown_to_html(content)
        
        try:
            # Resend API를 사용한 이메일 발송
            r = resend.Emails.send({
                "from": EMAIL_FROM,
                "to": recipients,
                "subject": subject,
                "html": html_content,
                "text": content  # 플레인 텍스트 버전
            })
            
            print(f"이메일 발송 완료: {r}")
            
        except Exception as e:
            print(f"이메일 발송 실패: {e}")
    
    def _markdown_to_html(self, markdown_text: str) -> str:
        """마크다운을 HTML로 변환"""
        html = markdown_text
        
        # 제목 변환
        lines = html.split('\n')
        formatted_lines = []
        
        for line in lines:
            if line.startswith('#### '):
                formatted_lines.append(f'<h4 style="color: #2c3e50; margin-top: 25px; font-size: 20px;">{line[5:]}</h4>')
            elif line.startswith('### '):
                formatted_lines.append(f'<h3 style="color: #34495e; margin-top: 35px; font-size: 24px; border-left: 4px solid #3498db; padding-left: 15px;">{line[4:]}</h3>')
            elif line.startswith('## '):
                formatted_lines.append(f'<h2 style="color: #2c3e50; margin-top: 40px; font-size: 28px;">{line[3:]}</h2>')
            elif line.startswith('# '):
                formatted_lines.append(f'<h1 style="color: #1a1a1a; font-size: 36px; margin-bottom: 30px;">{line[2:]}</h1>')
            elif line.strip() == '':
                formatted_lines.append('<br>')
            else:
                formatted_lines.append(f'<p style="line-height: 1.8; margin: 15px 0; text-align: justify;">{line}</p>')
        
        html = '\n'.join(formatted_lines)
        
        # 굵은 글씨
        import re
        html = re.sub(r'\*\*(.*?)\*\*', r'<strong style="color: #e74c3c; font-weight: 600;">\1</strong>', html)
        
        # 링크 변환
        html = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2" target="_blank" style="color: #3498db; text-decoration: none; border-bottom: 1px dotted #3498db;">\1</a>', html)
        
        # 스타일 추가
        styled_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ 
                    font-family: 'Noto Sans KR', -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; 
                    line-height: 1.8; 
                    color: #333; 
                    background-color: #f5f5f5;
                }}
                .container {{
                    max-width: 800px; 
                    margin: 0 auto; 
                    padding: 50px 30px;
                    background-color: white;
                    box-shadow: 0 2px 20px rgba(0,0,0,0.1);
                }}
                h1, h2, h3, h4 {{ 
                    color: #2c3e50; 
                    margin-top: 30px;
                    font-weight: 700;
                }}
                h1 {{ 
                    border-bottom: 3px solid #3498db; 
                    padding-bottom: 20px; 
                    font-size: 36px;
                    text-align: center;
                }}
                h2 {{
                    font-size: 28px;
                    color: #34495e;
                    margin-top: 50px;
                }}
                h3 {{
                    font-size: 24px;
                    color: #2c3e50;
                    border-left: 4px solid #3498db;
                    padding-left: 15px;
                    margin-top: 40px;
                }}
                h4 {{
                    font-size: 20px;
                    color: #34495e;
                    margin-top: 30px;
                }}
                p {{ 
                    margin: 20px 0; 
                    text-align: justify;
                    font-size: 16px;
                    color: #444;
                }}
                strong {{ 
                    color: #e74c3c; 
                    font-weight: 600;
                }}
                a {{
                    color: #3498db !important;
                    text-decoration: none;
                    border-bottom: 1px dotted #3498db;
                    transition: all 0.3s ease;
                }}
                a:hover {{
                    color: #2980b9 !important;
                    border-bottom-style: solid;
                }}
                .reference-section {{
                    margin-top: 60px;
                    padding: 30px;
                    background-color: #f8f9fa;
                    border-left: 4px solid #3498db;
                    border-radius: 5px;
                }}
                .reference-section h3 {{
                    margin-top: 0;
                    border: none;
                    padding: 0;
                }}
                .reference-section ul {{
                    list-style-type: none;
                    padding: 0;
                }}
                .reference-section li {{
                    margin: 15px 0;
                    padding: 12px 0;
                    border-bottom: 1px solid #e9ecef;
                }}
                .footer {{
                    margin-top: 70px;
                    padding-top: 30px;
                    border-top: 2px solid #ecf0f1;
                    font-size: 14px;
                    color: #95a5a6;
                    text-align: center;
                }}
                .footer p {{
                    text-align: center;
                }}
                .highlight-box {{
                    background-color: #f0f7ff;
                    border-left: 4px solid #3498db;
                    padding: 20px;
                    margin: 30px 0;
                    border-radius: 5px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                {html}
                <div class="footer">
                    <p>이 메일은 IT 트렌드 자동 분석 시스템에 의해 생성되었습니다.</p>
                    <p>매일 오전 9시, 최신 IT 트렌드를 여러분의 메일함으로 전달해 드립니다.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return styled_html

def run_daily_analysis():
    """일일 분석 실행"""
    print(f"트렌드 분석 시작: {datetime.now()}")
    
    # 1. 트렌드 분석기 초기화
    analyzer = ITTrendAnalyzer()
    
    # 2. 기사 수집
    print("기사 수집 중...")
    rss_articles = analyzer.fetch_rss_feeds()
    hn_articles = analyzer.fetch_hacker_news()
    all_articles = rss_articles + hn_articles
    
    # 3. 최신 기사 필터링
    recent_articles = analyzer.filter_recent_articles(all_articles)
    print(f"수집된 최신 기사: {len(recent_articles)}개")
    
    if not recent_articles:
        print("최신 기사가 없습니다.")
        return
    
    # 4. GPT 분석
    print("GPT 분석 중...")
    blog_post = analyzer.analyze_with_gpt(recent_articles)
    
    if not blog_post:
        print("블로그 포스트 생성 실패")
        return
    
    # 5. 이메일 발송
    print("이메일 발송 중...")
    email_sender = EmailSender()
    email_sender.send_blog_post(blog_post, EMAIL_TO)
    
    # 6. 로컬 파일로도 저장 (백업)
    filename = f"archive/blog_post_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(blog_post)
    print(f"블로그 포스트 저장: {filename}")
    
    # 7. 글자 수 확인
    char_count = len(blog_post)
    print(f"생성된 블로그 포스트 길이: {char_count}자")
    
    # 8. 비용 계산 출력 (최적화된 값)
    input_tokens = 5 * 20 + 250  # 5개 기사 제목 + 간결한 프롬프트
    output_tokens = 2500  # 줄어든 응답
    # GPT-3.5-turbo-16k 가격 기준
    cost = (input_tokens * 0.001 + output_tokens * 0.002) / 1000
    print(f"예상 GPT 비용: ${cost:.4f} (약 {cost * 1350:.0f}원)")
    print(f"토큰 절감률: 약 75% (이전 대비)")
    
    print("작업 완료!")

def main():
    """메인 실행 함수"""
    print("IT 트렌드 블로그 자동화 시작")
    
    # 스케줄 설정 (매일 오전 9시)
    schedule.every().day.at("09:00").do(run_daily_analysis)
    
    print("스케줄러 실행 중... (매일 오전 9시에 실행됩니다)")
    print("즉시 실행하려면 'run_daily_analysis()' 함수를 직접 호출하세요.")
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # 1분마다 체크

if __name__ == "__main__":
    # 테스트로 바로 실행
    run_daily_analysis()
    
    # 스케줄러로 실행하려면 아래 주석 해제
    # main()