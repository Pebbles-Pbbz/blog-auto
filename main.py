import os
import json
import requests
from datetime import datetime
from typing import List, Dict
import resend
import openai
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# API 키 및 이메일 설정
PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
RESEND_API_KEY = os.getenv('RESEND_API_KEY')
EMAIL_FROM = os.getenv('EMAIL_FROM', 'ai-trends@yourdomain.com')
EMAIL_TO = os.getenv('EMAIL_TO', 'gyu3637@gmail.com')
# EMAIL_TO = 'gyu3637@gmail.com'

# Resend 초기화
resend.api_key = RESEND_API_KEY


class AITrendAnalyzer:
    """Perplexity → Claude → E-mail 파이프라인"""

    def __init__(self):
        self.news_items: List[Dict] = []  # Perplexity JSON
        self.sources: List[str] = []      # URL 리스트
        self.final_post: str = ''         # Claude 결과 (Markdown)
        self.debug_info: Dict = {}

    # -----------------------------
    # 1) Perplexity: 오늘의 뉴스 검색
    # -----------------------------
    def search_news_with_perplexity(self) -> List[Dict]:
        """Perplexity API로 오늘의 AI/Tech 뉴스 5개를 JSON 배열로 수집"""
        headers = {
            'Authorization': f'Bearer {PERPLEXITY_API_KEY}',
            'Content-Type': 'application/json'
        }

        prompt = (
            """Find today's top 5 AI and tech news that would interest startup founders and developers.\n"""
            """Return ONLY a valid JSON array with objects: {title, summary, implications, url}.\n"""
            """Focus on launches, open-source, funding, breakthroughs, APIs, dev tools.\n"""
            """Avoid corporate PR and vague announcements.\n"""
            """Avoid videos such as youtube, tiktok, etc."""
        )

        payload = {
            "model": "sonar",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 2000
        }

        try:
            resp = requests.post(
                'https://api.perplexity.ai/chat/completions',
                headers=headers,
                json=payload,
                timeout=30
            )
            resp.raise_for_status()
            content = resp.json()['choices'][0]['message']['content'].strip()

            # 코드펜스 제거
            if content.startswith('```'):
                content = content.split('\n', 1)[1].rsplit('```', 1)[0].strip()

            self.news_items = json.loads(content)
            self.sources = [item['url'] for item in self.news_items]
            self.debug_info['news_count'] = len(self.news_items)
            return self.news_items
        except Exception as e:
            print(f"❌ Perplexity 오류: {e}")
            raise

    # -----------------------------
    # 2) OpenAI: 블로그 포스트 생성 (개선된 프롬프트)
    # -----------------------------
    def generate_with_openai(self) -> str:
        """GPT-4.1로 최종 Markdown 포스트 작성"""
        client = openai.OpenAI(api_key=OPENAI_API_KEY)

        prompt = f"""당신은 스타트업 창업자와 개발자들을 위한 AI 트렌드 분석 전문가입니다.
아래 뉴스들을 바탕으로 한국어로 심도 있는 블로그 포스트를 작성해주세요.

입력 데이터:
{json.dumps(self.news_items, ensure_ascii=False, indent=2)}

작성 가이드라인:
- 전체 분량: 2500자 - 4000자 (공백 포함)
- 독자: 한국의 스타트업 창업자, CTO, 개발자, 프로덕트 매니저
- "뉴닉 스타일 + 스레드(Thread) 감성"

1. **반말 톤**으로 말 걸듯 써줘  
2. **제목은 자극적이고 후킹되게**, 말맛 있게 쓸 것  
   (예: “AI가 책 읽고 공부했는데… 법원은 OK했대?”)  

3. 본문 구성은 이 순서로 이모지 포함해서 :
- :boom: 첫 문단: 요즘 유행하는 사례(혹은 밈)나 공감가는 상황에서 시작  
- :round_pushpin: 중간 요약: 사건 or 이슈가 뭐였는지 맥락 정리  
- :eyes: 실무자 시선: “그럼 이걸 우리는 어떻게 받아들여야 할까?” 꼭 포함  
- :white_check_mark: 마지막 한 줄 요약: 캐주얼하지만 정리되는 문장

4. **친절하지만 가볍게**, “설명해주듯” 말투로  
5. 너무 설명하거나 교과서처럼 쓰지 말고, **카톡하듯** 쓸 것
"""

        resp = client.chat.completions.create(
            model="gpt-4.1-nano-2025-04-14",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=8192,
            temperature=0.3
        )

        self.final_post = resp.choices[0].message.content
        self.debug_info['openai_usage'] = {
            'prompt_tokens': resp.usage.prompt_tokens,
            'completion_tokens': resp.usage.completion_tokens,
            'total_tokens': resp.usage.total_tokens,
        }
        return self.final_post

    # -----------------------------
    # 3) 파일 저장
    # -----------------------------
    def save_to_file(self):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        md_name = f"blog_post_{timestamp}.md"
        with open(md_name, 'w', encoding='utf-8') as f:
            f.write(self.final_post)

        meta_name = f"metadata_{timestamp}.json"
        with open(meta_name, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': timestamp,
                'news_count': len(self.news_items),
                'final_length': len(self.final_post),
                'openai_usage': self.debug_info.get('openai_usage', {})
            }, f, ensure_ascii=False, indent=2)

        print(f"📄 {md_name} & {meta_name} 저장 완료")

    # -----------------------------
    # 4) Markdown → HTML (푸터에 출처 포함)
    # -----------------------------
    def _markdown_to_html(self, md: str, sources: List[str]) -> str:
        import re

        # 기본 Markdown 변환 (단순 정규식)
        html = md
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)  # 인라인 코드
        html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        html = re.sub(r'(<li>.*?</li>)', r'<ul>\1</ul>', html, flags=re.DOTALL)
        
        # 체크박스 처리
        html = re.sub(r'- \[ \] (.+)$', r'<li><input type="checkbox" disabled> \1</li>', html, flags=re.MULTILINE)
        html = re.sub(r'- \[x\] (.+)$', r'<li><input type="checkbox" checked disabled> \1</li>', html, flags=re.MULTILINE)

        # 문단 래핑
        paragraphs = [p.strip() for p in html.split('\n\n') if p.strip()]
        html = '\n'.join(
            p if p.startswith('<') else f'<p>{p}</p>'
            for p in paragraphs
        )

        # 출처 섹션
        src_html = '<h3>참고 자료</h3><ol>' + ''.join(
            f'<li><a href="{u}" target="_blank">{u}</a></li>' for u in sources
        ) + '</ol>'

        # 스타일 적용 (개선된 디자인)
        styled = f"""
        <!DOCTYPE html>
        <html lang=ko>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body{{
                    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    line-height: 1.8;
                    color: #2c3e50;
                    max-width: 750px;
                    margin: 0 auto;
                    padding: 40px 20px;
                    background: #f8f9fa;
                }}
                h1{{
                    color: #1a202c;
                    border-bottom: 3px solid #4299e1;
                    padding-bottom: 15px;
                    margin-bottom: 30px;
                    font-size: 32px;
                    font-weight: 700;
                }}
                h2{{
                    color: #2d3748;
                    margin-top: 45px;
                    margin-bottom: 25px;
                    font-size: 26px;
                    font-weight: 600;
                }}
                h3{{
                    color: #4a5568;
                    margin-top: 30px;
                    margin-bottom: 20px;
                    font-size: 20px;
                    font-weight: 600;
                }}
                strong{{
                    color: #e53e3e;
                    font-weight: 600;
                }}
                code{{
                    background: #e2e8f0;
                    padding: 2px 6px;
                    border-radius: 3px;
                    font-family: 'Consolas', 'Monaco', monospace;
                    font-size: 0.9em;
                }}
                p{{
                    margin: 20px 0;
                    text-align: justify;
                }}
                ul{{
                    margin: 20px 0;
                    padding-left: 30px;
                }}
                li{{
                    margin: 10px 0;
                }}
                a{{
                    color: #4299e1;
                    text-decoration: none;
                }}
                a:hover{{
                    text-decoration: underline;
                }}
                input[type="checkbox"]{{
                    margin-right: 8px;
                }}
                .footer{{
                    margin-top: 60px;
                    padding-top: 30px;
                    border-top: 1px solid #e2e8f0;
                    font-size: 14px;
                    color: #718096;
                    text-align: center;
                }}
            </style>
        </head>
        <body>
            <h1>AI 트렌드 인사이트</h1>
            {html}
            {src_html}
            <div class="footer">
                Generated by AI Trend Analyzer • {datetime.now().strftime('%Y년 %m월 %d일 %H:%M')}
            </div>
        </body>
        </html>"""
        return styled

    # -----------------------------
    # 5) 이메일 발송
    # -----------------------------
    def send_email(self):
        if not self.final_post:
            print("⚠️  최종 포스트가 비어 있습니다. 이메일 취소")
            return

        html_body = self._markdown_to_html(self.final_post, self.sources)
        subject = f"[AI 트렌드] {datetime.now().strftime('%m/%d')} 실무 인사이트"

        try:
            result = resend.Emails.send({
                "from": EMAIL_FROM,
                "to": EMAIL_TO,
                "subject": subject,
                "html": html_body,
                "text": self.final_post
            })
            print(f"✅ 이메일 발송 완료: {result}")
        except Exception as e:
            print(f"❌ 이메일 발송 실패: {e}")

    # -----------------------------
    # 파이프라인 실행
    # -----------------------------
    def run(self):
        print("🚀 AI 트렌드 분석 시작!")
        self.search_news_with_perplexity()
        self.generate_with_openai()
        # self.save_to_file()
        self.send_email()
        print("🎉 모든 작업 완료!")


if __name__ == "__main__":
    AITrendAnalyzer().run()