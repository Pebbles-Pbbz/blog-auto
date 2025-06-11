import os
import json
import requests
from datetime import datetime
from typing import List, Dict
import resend
import anthropic
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# API 키 및 이메일 설정
PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
RESEND_API_KEY = os.getenv('RESEND_API_KEY')
EMAIL_FROM = os.getenv('EMAIL_FROM', 'ai-trends@yourdomain.com')
EMAIL_TO = os.getenv('EMAIL_TO', 'gyu3637@gmail.com')

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
            """Avoid corporate PR and vague announcements."""
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
    # 2) Claude: 블로그 포스트 생성 (개선된 프롬프트)
    # -----------------------------
    def generate_with_claude(self) -> str:
        """Claude-3.5 Haiku로 최종 Markdown 포스트 작성"""
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        prompt = f"""당신은 스타트업 창업자와 개발자들을 위한 AI 트렌드 분석 전문가입니다.
아래 뉴스들을 바탕으로 한국어로 심도 있는 블로그 포스트를 작성해주세요.

입력 데이터:
{json.dumps(self.news_items, ensure_ascii=False, indent=2)}

작성 가이드라인:
- 전체 분량: 5,000-7,000자 (공백 포함)
- 톤: 전문적이면서도 친근한 대화체
- 독자: 한국의 스타트업 창업자, CTO, 개발자, 프로덕트 매니저

뉴닉 스타일 푸시 메시지와 실무 인사이트 요약으로 정리해줘.

형식은 아래와 같아:
[임팩트 있는 제목]
(필요하면 부제도 괜찮아)
[기사 내용의 핵심을 요약한 본문.
 친근한 톤이지만 맥락과 쟁점을 분명하게 정리하고,
 짧은 단문으로 핵심을 잘라주는 스타일.
 사실관계 + 맥락 요약이 조화롭게 섞여야 해.]

실무자라면 이렇게 봐야 해요

[실무 상황 1 - 어떻게 해석할 수 있는지, 어떤 준비가 필요한지(최대한 자세하게)]
[실무 상황 2 - 이걸 어떤 관점에서 활용하면 도움이 되는지(최대한 자세하게)]
[특정 타겟(예: 스타트업/기획자/투자자 등)이 얻을 수 있는 교훈이나 전략]

한 줄 요약
 [핵심 메시지를 재치 있게 정리. 맨 밑 요약은 선택이지만 있으면 더 좋아요.]
"""

        resp = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=8192,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )

        self.final_post = resp.content[0].text
        self.debug_info['claude_usage'] = {
            'input_tokens': resp.usage.input_tokens,
            'output_tokens': resp.usage.output_tokens,
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
                'claude_usage': self.debug_info.get('claude_usage', {})
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
        self.generate_with_claude()
        # self.save_to_file()
        self.send_email()
        print("🎉 모든 작업 완료!")


if __name__ == "__main__":
    AITrendAnalyzer().run()