import os
import json
import requests
from datetime import datetime
from typing import List, Dict
import resend
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# API 설정
PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
RESEND_API_KEY = os.getenv('RESEND_API_KEY')
EMAIL_FROM = os.getenv('EMAIL_FROM', 'ai-trends@yourdomain.com')
EMAIL_TO = os.getenv('EMAIL_TO', 'your-email@gmail.com')

# Resend 설정
resend.api_key = RESEND_API_KEY

class AITrendAnalyzer:
    def __init__(self):
        self.news_data = None
        self.draft_post = None
        self.final_post = None
    
    def search_news_with_perplexity(self) -> str:
        """Perplexity API로 최신 AI/Tech 뉴스 검색"""
        print("🔍 Perplexity로 최신 뉴스 검색 중...")
        
        headers = {
            'Authorization': f'Bearer {PERPLEXITY_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "model": "pplx-7b-online",
            "messages": [{
                "role": "user",
                "content": """Find today's top 5 AI and tech news that would interest startup founders and developers. For each:
                1. Title
                2. Brief summary (2-3 sentences)
                3. Practical implications for startups/developers
                4. Source URL
                
                Focus on: AI product launches, open source releases, funding news, 
                technical breakthroughs, API updates, developer tools, market analysis.
                Avoid: corporate PR, vague announcements, overhyped claims."""
            }],
            "temperature": 0.2,
            "max_tokens": 1500
        }
        
        try:
            response = requests.post(
                'https://api.perplexity.ai/chat/completions',
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            
            self.news_data = response.json()['choices'][0]['message']['content']
            print(f"✅ 뉴스 검색 완료: {len(self.news_data)} 글자")
            return self.news_data
            
        except Exception as e:
            print(f"❌ Perplexity API 오류: {e}")
            raise
    
    def create_draft_with_gpt(self) -> str:
        """GPT-3.5로 초안 작성"""
        print("📝 GPT-3.5로 초안 작성 중...")
        
        headers = {
            'Authorization': f'Bearer {OPENAI_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "model": "gpt-3.5-turbo-16k",
            "messages": [
                {
                    "role": "system",
                    "content": "AI 시장 전문가. 스타트업과 개발자에게 실용적이고 담담한 인사이트 제공. 과장이나 미사여구 없이 팩트 중심으로 작성."
                },
                {
                    "role": "user",
                    "content": f"""다음 뉴스를 바탕으로 AI 스타트업 대표와 개발자를 위한 블로그 작성:

{self.news_data}

[타겟 독자]
- AI 시장에 관심있는 스타트업 대표
- 실무 개발자

[작성 요구사항]
분량: 2500-3000자
톤앤매너: 밝고 현실적인 분위기, 담담한 지식 전달 (과한 강조나 과장 표현 지양)

[구조]
## 1. 인트로 (300자)
- 기사 기반의 후킹될 수 있는 질문이나 통계로 시작
- 독자의 현실적 고민과 연결

## 2. 본문 - 핵심 3가지 (각 600-700자)
각 섹션별로:
- 소제목: 50자 내외, 설명적이지 않게 (예: "개발 리스크" X → "정리가 안 되면 생기는 일" O)
- 내용: 실무적 관점의 팁이나 구체적 사례 중심
- 정보, 통찰, 리스크 등 다양한 관점 포함
- 짧고 명확한 단락 구성

## 3. 마무리 (300자)
- 핵심 요약 정리
- 실무에 적용 가능한 인사이트나 한 줄 메시지

[스타일 가이드]
- 마크다운 사용 (##, ###, **굵은글씨**)
- 구체적 수치나 사례 포함
- 한국 스타트업이나 개발자 상황에 맞는 예시
- 지나친 미사여구나 감탄사 배제
- 간결하고 명확한 문장"""
                }
            ],
            "temperature": 0.8,
            "max_tokens": 2500
        }
        
        try:
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            
            self.draft_post = response.json()['choices'][0]['message']['content']
            print(f"✅ 초안 작성 완료: {len(self.draft_post)} 글자")
            return self.draft_post
            
        except Exception as e:
            print(f"❌ OpenAI API 오류: {e}")
            raise
    
    def polish_with_claude(self) -> str:
        """Claude Haiku로 최종 다듬기"""
        print("✨ Claude로 최종 다듬기 중...")
        
        headers = {
            'x-api-key': ANTHROPIC_API_KEY,
            'anthropic-version': '2023-06-01',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 3000,
            "temperature": 0.3,
            "messages": [{
                "role": "user",
                "content": f"""다음 블로그 포스트를 AI 스타트업과 개발자 타겟에 맞게 개선:

{self.draft_post}

[개선 요청사항]
1. 톤 조정:
   - 과도한 감탄사나 형용사 제거
   - 팩트와 데이터 중심으로
   - 담담하고 객관적인 어조 유지
   - 현실적이고 실용적인 관점

2. 내용 개선:
   - 실제 개발이나 비즈니스에 적용할 수 있는 팁
   - 구체적인 툴, 라이브러리, API 언급
   - 실패 사례나 주의점도 균형있게 포함
   - 과대포장된 내용은 현실적으로 수정

3. 구조 정리:
   - 소제목은 호기심을 유발하되 과하지 않게
   - 핵심 정보는 **굵은 글씨**로 강조
   - 불필요한 수식어 제거

4. 실무 예시:
   - 한국 스타트업 환경에 맞는 예시
   - 개발자가 바로 시도해볼 수 있는 내용
   - 투자나 채용 관점의 인사이트

마크다운 형식 유지하되, 깔끔하고 읽기 쉽게 작성."""
            }]
        }
        
        try:
            response = requests.post(
                'https://api.anthropic.com/v1/messages',
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            
            self.final_post = response.json()['content'][0]['text']
            print(f"✅ 최종 다듬기 완료: {len(self.final_post)} 글자")
            return self.final_post
            
        except Exception as e:
            print(f"❌ Claude API 오류: {e}")
            raise
    
    def save_to_file(self):
        """결과물을 파일로 저장"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        
        # 마크다운 파일 저장
        filename = f"blog_post_{timestamp}.md"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(self.final_post)
        print(f"📄 블로그 포스트 저장: {filename}")
        
        # 메타데이터 저장 (JSON)
        metadata = {
            "timestamp": timestamp,
            "news_sources": self.news_data,
            "draft_length": len(self.draft_post),
            "final_length": len(self.final_post),
            "cost_estimate": {
                "perplexity": 0.002,
                "gpt": 0.003,
                "claude": 0.003,
                "total": 0.008
            }
        }
        
        meta_filename = f"metadata_{timestamp}.json"
        with open(meta_filename, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        print(f"📊 메타데이터 저장: {meta_filename}")
    
    def send_email(self):
        """이메일 발송"""
        print("📧 이메일 발송 중...")
        
        subject = f"[AI 스타트업 리포트] {datetime.now().strftime('%Y년 %m월 %d일')} - 오늘 놓치면 안 되는 실무 인사이트"
        
        # 마크다운을 HTML로 변환 (간단한 변환)
        html_content = self._markdown_to_html(self.final_post)
        
        try:
            r = resend.Emails.send({
                "from": EMAIL_FROM,
                "to": EMAIL_TO,
                "subject": subject,
                "html": html_content,
                "text": self.final_post
            })
            print(f"✅ 이메일 발송 완료: {r}")
            
        except Exception as e:
            print(f"❌ 이메일 발송 실패: {e}")
            raise
    
    def _markdown_to_html(self, markdown_text: str) -> str:
        """간단한 마크다운 → HTML 변환"""
        import re
        
        html = markdown_text
        
        # 제목 변환
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        
        # 굵은 글씨
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        
        # 줄바꿈
        html = html.replace('\n\n', '</p><p>')
        html = f'<p>{html}</p>'
        
        # 스타일 추가
        styled_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                h1, h2, h3 {{
                    color: #2c3e50;
                    margin-top: 30px;
                }}
                h1 {{
                    border-bottom: 3px solid #3498db;
                    padding-bottom: 10px;
                }}
                strong {{
                    color: #e74c3c;
                }}
                p {{
                    margin: 15px 0;
                }}
            </style>
        </head>
        <body>
            {html}
            <hr style="margin-top: 50px;">
            <p style="color: #666; font-size: 14px;">
                이 메일은 AI 트렌드 자동 분석 시스템에 의해 생성되었습니다.
            </p>
        </body>
        </html>
        """
        
        return styled_html
    
    def calculate_cost(self):
        """비용 계산 및 출력"""
        costs = {
            "Perplexity": 0.002,
            "GPT-3.5": 0.003,
            "Claude Haiku": 0.003,
            "Total": 0.008
        }
        
        print("\n💰 예상 비용:")
        for service, cost in costs.items():
            print(f"  - {service}: ${cost:.3f} (약 {cost * 1350:.0f}원)")
        
        print(f"\n  월간 예상: ${costs['Total'] * 30:.2f} (약 {costs['Total'] * 30 * 1350:.0f}원)")

def main():
    """메인 실행 함수"""
    print("🚀 AI 트렌드 분석 시작!")
    print(f"⏰ 실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    try:
        analyzer = AITrendAnalyzer()
        
        # 1. 뉴스 검색
        analyzer.search_news_with_perplexity()
        
        # 2. 초안 작성
        analyzer.create_draft_with_gpt()
        
        # 3. 최종 다듬기
        analyzer.polish_with_claude()
        
        # 4. 파일 저장
        analyzer.save_to_file()
        
        # 5. 이메일 발송
        analyzer.send_email()
        
        # 6. 비용 계산
        analyzer.calculate_cost()
        
        print("\n✅ 모든 작업 완료!")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        raise

if __name__ == "__main__":
    main()