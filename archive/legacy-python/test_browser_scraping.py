#!/usr/bin/env python3
"""
Browser-based Scraping Test using AppleScript (Safari)
"""

import subprocess
import time
import re

def run_applescript(script):
    """AppleScript 실행"""
    result = subprocess.run(
        ['osascript', '-e', script],
        capture_output=True,
        text=True,
        timeout=30
    )
    return result.stdout.strip(), result.stderr.strip()

def test_safari_scraping():
    """Safari로 Claude.ai 접근 테스트"""

    print("🌐 Safari로 Claude.ai 접근 테스트...\n")

    try:
        # 1. Safari 열기
        print("1. Safari 실행...")
        script = '''
        tell application "Safari"
            activate
            make new document
            set URL of front document to "https://claude.ai"
            delay 3
        end tell
        '''
        stdout, stderr = run_applescript(script)
        if stderr:
            print(f"   ⚠️  {stderr}")
        else:
            print("   ✅ Safari 열림")

        time.sleep(3)

        # 2. 페이지 타이틀 가져오기
        print("\n2. 페이지 정보 확인...")
        script = '''
        tell application "Safari"
            return name of front document
        end tell
        '''
        stdout, stderr = run_applescript(script)
        print(f"   페이지 제목: {stdout}")

        # 3. 현재 URL 확인
        script = '''
        tell application "Safari"
            return URL of front document
        end tell
        '''
        stdout, stderr = run_applescript(script)
        print(f"   현재 URL: {stdout}")

        # 4. JavaScript 실행 테스트
        print("\n3. JavaScript 실행 테스트...")
        script = '''
        tell application "Safari"
            do JavaScript "document.title" in front document
        end tell
        '''
        stdout, stderr = run_applescript(script)
        print(f"   JS 결과: {stdout}")

        print("\n" + "="*50)
        print("📊 결과:")
        print("="*50)

        if "claude" in stdout.lower():
            print("✅ Claude.ai 접근 성공!")
            print("")
            print("💡 다음 단계:")
            print("   1. 로그인 확인 필요")
            print("   2. /usage 명령 자동 입력")
            print("   3. 결과 파싱")
            print("")
            print("⚠️  제한사항:")
            print("   - 수동으로 1회 로그인 필요")
            print("   - Safari를 열어둬야 함")
            print("   - UI 변경 시 스크립트 수정 필요")
        else:
            print("❌ 접근 실패 또는 리다이렉트")

        # Safari 닫기
        print("\n4. Safari 닫기...")
        script = '''
        tell application "Safari"
            close front document
        end tell
        '''
        run_applescript(script)
        print("   ✅ 정리 완료")

    except subprocess.TimeoutExpired:
        print("❌ 타임아웃: Safari 응답 없음")
    except Exception as e:
        print(f"❌ 에러: {e}")

if __name__ == "__main__":
    print("⚠️  주의: Safari가 실행되고 새 탭이 열립니다.")
    print("계속하려면 Enter를 누르세요...")
    input()
    test_safari_scraping()
