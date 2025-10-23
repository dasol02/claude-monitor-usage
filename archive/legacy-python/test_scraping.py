#!/usr/bin/env python3
"""
Claude.ai Web Scraping Test
간단한 HTTP 요청으로 스크래핑 가능 여부 테스트
"""

import urllib.request
import json
import http.cookiejar
import ssl

def test_claude_website():
    """Claude.ai 접근 테스트"""

    print("🔍 Claude.ai 웹사이트 접근 테스트...\n")

    # SSL 컨텍스트 생성
    ssl_context = ssl.create_default_context()

    # 쿠키 핸들러
    cookie_jar = http.cookiejar.CookieJar()
    cookie_handler = urllib.request.HTTPCookieProcessor(cookie_jar)
    opener = urllib.request.build_opener(cookie_handler, urllib.request.HTTPSHandler(context=ssl_context))

    # User-Agent 설정
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }

    try:
        # 1. 메인 페이지 접근
        print("1. 메인 페이지 접근...")
        req = urllib.request.Request('https://claude.ai', headers=headers)
        response = opener.open(req, timeout=10)
        print(f"   ✅ Status: {response.status}")
        print(f"   ✅ Content-Type: {response.headers.get('Content-Type')}")

        # 2. API 엔드포인트 확인
        print("\n2. API 엔드포인트 추측...")
        api_endpoints = [
            'https://claude.ai/api/usage',
            'https://api.claude.ai/v1/usage',
            'https://claude.ai/api/organizations/usage',
        ]

        for endpoint in api_endpoints:
            try:
                req = urllib.request.Request(endpoint, headers=headers)
                resp = opener.open(req, timeout=5)
                print(f"   ✅ {endpoint}: {resp.status}")
            except urllib.error.HTTPError as e:
                print(f"   ❌ {endpoint}: {e.code} {e.reason}")
            except Exception as e:
                print(f"   ❌ {endpoint}: {str(e)}")

        # 3. 쿠키 확인
        print("\n3. 쿠키 정보...")
        if len(cookie_jar) > 0:
            print(f"   ✅ 쿠키 개수: {len(cookie_jar)}")
            for cookie in cookie_jar:
                print(f"   - {cookie.name}: {cookie.value[:20]}...")
        else:
            print("   ⚠️  쿠키 없음")

        print("\n" + "="*50)
        print("📊 결론:")
        print("="*50)
        print("❌ 간단한 HTTP 요청으로는 불가능")
        print("🔒 인증이 필요함 (로그인 세션)")
        print("")
        print("✅ 가능한 방법:")
        print("   1. Playwright/Selenium으로 브라우저 자동화")
        print("   2. 로그인 후 세션 쿠키 저장 → 재사용")
        print("   3. Chrome Extension으로 직접 접근")

    except Exception as e:
        print(f"❌ 에러: {e}")

if __name__ == "__main__":
    test_claude_website()
