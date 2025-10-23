#!/usr/bin/env python3
"""
Fetch actual Claude usage from API

Claude CLI의 API 호출을 모방하여 실제 사용량을 가져옴
"""

import os
import json
import subprocess
from pathlib import Path


def get_api_key():
    """Claude API 키 가져오기"""
    # 환경변수에서
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if api_key:
        return api_key

    # 또는 claude auth status에서 추출
    try:
        result = subprocess.run(
            ['claude', 'auth', 'status'],
            capture_output=True,
            text=True,
            timeout=5
        )
        # API key가 포함되어 있을 수 있음
        if 'authenticated' in result.stdout.lower():
            return True  # 인증됨
    except:
        pass

    return None


def fetch_usage_from_api():
    """
    API를 통해 실제 사용량 가져오기

    Returns:
        float: Session output percentage (0.0 ~ 1.0), None if failed
    """
    try:
        import requests

        # Claude API endpoint (추정)
        # 실제 엔드포인트는 claude CLI 소스코드를 확인해야 함
        url = "https://api.anthropic.com/v1/usage"

        api_key = get_api_key()
        if not api_key or api_key == True:
            print("⚠️  API key not found")
            return None

        headers = {
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01'
        }

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            # 응답 구조에 따라 파싱
            # 예: data['session']['output_percentage']
            return data
        else:
            print(f"⚠️  API error: {response.status_code}")
            return None

    except ImportError:
        print("⚠️  'requests' module not found. Install: pip3 install requests")
        return None
    except Exception as e:
        print(f"⚠️  Error fetching from API: {e}")
        return None


def scrape_from_claude_command():
    """
    claude usage 명령어 출력을 스크래핑

    expect나 pexpect를 사용하여 TUI 제어
    """
    try:
        import pexpect

        # claude usage 실행
        child = pexpect.spawn('claude usage', timeout=10)

        # 출력 수집
        output = []
        try:
            while True:
                index = child.expect([
                    pexpect.TIMEOUT,
                    pexpect.EOF,
                    r'Output:\s+(\d+\.?\d*)%',
                    r'.*\n'
                ], timeout=2)

                if index == 0 or index == 1:
                    break
                elif index == 2:
                    # Output percentage 발견
                    percentage = child.match.group(1).decode()
                    child.terminate()
                    return float(percentage) / 100.0
                else:
                    output.append(child.match.group(0).decode())

        except pexpect.TIMEOUT:
            pass

        child.terminate()

        # 출력에서 파싱
        full_output = ''.join(output)
        import re
        match = re.search(r'Output:\s+(\d+\.?\d*)%', full_output)
        if match:
            return float(match.group(1)) / 100.0

    except ImportError:
        print("⚠️  'pexpect' module not found. Install: pip3 install pexpect")
        return None
    except Exception as e:
        print(f"⚠️  Error scraping: {e}")
        return None

    return None


def main():
    """메인 함수"""
    print("🔍 Fetching actual Claude usage...")

    # 방법 1: API 호출 (더 안정적)
    result = fetch_usage_from_api()
    if result:
        print(f"✅ API: {result}")
        return

    # 방법 2: claude usage 스크래핑 (fallback)
    result = scrape_from_claude_command()
    if result:
        print(f"✅ Scraped: {result*100:.1f}%")
        return

    print("❌ Failed to fetch usage")
    print("\nAlternatives:")
    print("1. Install pexpect: pip3 install pexpect")
    print("2. Use manual calibration: claude-calibrate")


if __name__ == '__main__':
    main()
