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
                "content": """Find today's top 5 AI and tech news. For each:
                1. Title
                2. Brief summary (2-3 sentences)
                3. Why it matters
                4. Source URL
                
                Focus on: AI breakthroughs, major tech company announcements, 
                new product launches, industry trends, regulatory updates."""
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
                    "content": "당신은 한국의 IT 전문 기자입니다. 기술 트렌드를 깊이 있게 분석하고 한국 시장 관점에서 실용적인 인사이트를 제공합니다."
                },
                {
                    "role": "user",
                    "content": f"""다음 뉴스를 바탕으로 한국 독자를 위한 2500자 블로그 포스트를 작성하세요:

{self.news_data}

[작성 요구사항]
1. 제목: 오늘의 핵심을 담은 매력적인 제목

2. 구조:
   - 서론(300자): 오늘의 주요 트렌드 개요와 중요성
   - 트렌드 1(700자): 
     * 현황 분석
     * 기술적 의미
     * 한국 시장/기업에 미치는 영향
     * 실무자를 위한 제언
   - 트렌드 2(700자): 위와 동일한 구조
   - 트렌드 3(700자): 위와 동일한 구조
   - 결론(300자): 핵심 시사점과 액션 아이템

3. 작성 스타일:
   - 전문적이지만 이해하기 쉽게
   - 구체적인 예시와 수치 활용
   - 한국 기업이나 시장 상황 언급

4. 형식: 마크다운 사용 (###, **, 등)"""
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
                "content": f"""다음 블로그 포스트를 개선해주세요:

{self.draft_post}

[개선 요청사항]
1. 문장 다듬기:
   - 더 자연스럽고 매끄러운 문장으로
   - 불필요한 반복 제거
   - 전문 용어는 쉽게 설명

2. 내용 보강:
   - 한국 기업 사례 추가 (삼성, LG, 네이버, 카카오 등)
   - 실무에 바로 적용 가능한 팁 추가
   - 구체적인 수치나 통계 보완

3. 구조 개선:
   - 단락 간 자연스러운 연결
   - 핵심 내용 강조 (굵은 글씨 활용)
   - 읽기 쉬운 문단 구성

4. 톤 조정:
   - 전문적이지만 친근한 어투
   - 독자와 소통하는 느낌

최종 결과물은 마크다운 형식으로 작성해주세요."""
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
        
        subject = f"[AI 트렌드] {datetime.now().strftime('%Y년 %m월 %d일')} - 오늘의 핵심 인사이트"
        
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