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

필수 포함 내용:
1. 각 뉴스의 핵심 기술과 작동 원리를 구체적으로 설명
2. 실제 한국 스타트업이나 개발자가 어떻게 활용할 수 있는지 구체적인 예시
3. 관련된 오픈소스 도구, API, 라이브러리 이름과 사용법
4. 예상되는 비용, 구현 난이도, 필요한 기술 스택
5. 각 트렌드가 한국 시장에 미칠 구체적인 영향
6. 당장 시도해볼 수 있는 실험이나 프로토타입 아이디어

구조:
## 들어가며 (600-800자)
- 오늘 다룰 핵심 트렌드 3가지를 흥미롭게 소개
- 왜 지금 이 트렌드들이 중요한지 설명
- 독자가 얻을 수 있는 구체적인 이익 제시

## 핵심 인사이트 1: [첫 번째 주요 트렌드] (1,200-1,500자)
### 기술의 핵심
- 기술적 원리와 혁신 포인트를 쉽게 설명
- 기존 방식과의 차이점
- 핵심 장단점 분석

### 실무 활용 시나리오
- 한국 스타트업 맥락에서의 구체적인 활용 사례 2-3개
- 필요한 기술 스택과 도구들 (정확한 이름과 버전)
- 예상 개발 기간과 필요 인력

### 바로 시작하기
- 실제 코드 스니펫이나 설정 예시
- 유용한 리소스 링크 (공식 문서, 튜토리얼, 커뮤니티)

## 핵심 인사이트 2: [두 번째 주요 트렌드] (1,200-1,500자)
[위와 동일한 구조]

## 핵심 인사이트 3: [세 번째 주요 트렌드] (1,200-1,500자)
[위와 동일한 구조]

## 실무 적용 로드맵 (800-1,000자)
### 단기 (1-2주)
- 즉시 실험해볼 수 있는 것들
- 필요한 최소한의 리소스

### 중기 (1-3개월)
- 파일럿 프로젝트 아이디어
- 예상 ROI와 성과 지표

### 장기 (6개월-1년)
- 전략적 도입 방안
- 조직 차원의 준비사항

## 액션 아이템 체크리스트
- [ ] 오늘 당장 해볼 수 있는 일 5가지
- [ ] 이번 주에 학습할 리소스 3가지
- [ ] 다음 달까지 완성할 프로토타입 아이디어 2가지

## 마무리 (400-500자)
- 핵심 메시지 요약
- 독자에게 동기부여가 되는 메시지
- 다음 트렌드 예고나 질문 유도

작성 시 주의사항:
- **굵은 글씨**로 중요한 키워드, 도구명, API명 강조
- 구체적인 숫자, 통계, 사례를 최대한 활용
- 코드나 명령어는 `백틱`으로 표시
- 한국 개발자 커뮤니티에서 실제로 논의되는 주제와 연결
- 네이버, 카카오, 토스, 쿠팡 등 한국 테크 기업 사례 언급
- 실무자가 바로 따라할 수 있는 구체적인 가이드 제공

이제 위 가이드라인에 따라 심도 있고 실용적인 블로그 포스트를 작성해주세요."""

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