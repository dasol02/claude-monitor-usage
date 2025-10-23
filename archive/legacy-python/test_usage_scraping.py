#!/usr/bin/env python3
"""
Claude.ai Settings/Usage 페이지 스크래핑 테스트
URL: https://claude.ai/settings/usage
기본 브라우저 사용 (Chrome or Safari)
"""

import subprocess
import time
import json
import re

def get_default_browser():
    """기본 브라우저 확인"""
    try:
        result = subprocess.run(
            ['defaults', 'read', 'com.apple.LaunchServices/com.apple.launchservices.secure', 'LSHandlers'],
            capture_output=True,
            text=True
        )
        if 'chrome' in result.stdout.lower():
            return 'Chrome'
        elif 'safari' in result.stdout.lower():
            return 'Safari'
        else:
            # 기본값으로 Safari 사용
            return 'Safari'
    except:
        return 'Safari'

def run_applescript(script):
    """AppleScript 실행"""
    result = subprocess.run(
        ['osascript', '-e', script],
        capture_output=True,
        text=True,
        timeout=30
    )
    return result.stdout.strip(), result.stderr.strip()

def scrape_usage_chrome():
    """Chrome으로 Usage 페이지 스크래핑"""

    print("🌐 Chrome으로 스크래핑 시도...\n")

    try:
        # Chrome으로 페이지 열기
        print("1. Chrome에서 Usage 페이지 열기...")
        script = '''
        tell application "Google Chrome"
            activate
            set newTab to make new tab at end of tabs of front window
            set URL of newTab to "https://claude.ai/settings/usage"
            delay 5
        end tell
        '''
        stdout, stderr = run_applescript(script)
        print("   ✅ 페이지 열림 (5초 대기)")

        time.sleep(5)

        # 페이지 텍스트 추출
        print("\n2. 페이지 내용 추출 중...")
        script = '''
        tell application "Google Chrome"
            execute front window's active tab javascript "document.body.innerText"
        end tell
        '''
        stdout, stderr = run_applescript(script)

        return stdout, stderr

    except Exception as e:
        print(f"❌ Chrome 에러: {e}")
        return None, str(e)

def scrape_usage_safari():
    """Safari로 Usage 페이지 스크래핑"""

    print("🌐 Safari로 스크래핑 시도...\n")

    try:
        # Safari로 페이지 열기
        print("1. Safari에서 Usage 페이지 열기...")
        script = '''
        tell application "Safari"
            activate
            make new document
            set URL of front document to "https://claude.ai/settings/usage"
            delay 5
        end tell
        '''
        stdout, stderr = run_applescript(script)
        print("   ✅ 페이지 열림 (5초 대기)")

        time.sleep(5)

        # 페이지 텍스트 추출
        print("\n2. 페이지 내용 추출 중...")
        script = '''
        tell application "Safari"
            do JavaScript "document.body.innerText" in front document
        end tell
        '''
        stdout, stderr = run_applescript(script)

        return stdout, stderr

    except Exception as e:
        print(f"❌ Safari 에러: {e}")
        return None, str(e)

def parse_usage_text(text):
    """
    Usage 페이지 텍스트에서 사용량 추출

    예상 텍스트 구조:
    사용 한도
    Current session
    3시간 50분 후 재설정
    17% 사용됨
    주간 한도
    All models
    (화) 오전 10:59에 재설정
    17% 사용됨
    """

    print("3. 사용량 정보 파싱...")

    lines = text.split('\n')
    usage_data = {}

    # 디버그: 전체 텍스트 샘플 출력
    print(f"   추출된 텍스트 길이: {len(text)} 글자")

    for i, line in enumerate(lines):
        line_stripped = line.strip()

        # "Current session" 다음에 나오는 퍼센트 찾기
        if 'Current session' in line_stripped:
            # 다음 5줄 안에서 "XX% 사용됨" 패턴 찾기
            for j in range(i+1, min(i+6, len(lines))):
                match = re.search(r'(\d+)%\s*사용', lines[j])
                if match:
                    usage_data['session'] = int(match.group(1))
                    print(f"   ✅ Session: {match.group(1)}%")
                    break

        # "All models" 다음에 나오는 퍼센트 찾기 (Weekly)
        if 'All models' in line_stripped:
            # 다음 5줄 안에서 "XX% 사용됨" 패턴 찾기
            for j in range(i+1, min(i+6, len(lines))):
                match = re.search(r'(\d+)%\s*사용', lines[j])
                if match:
                    usage_data['weekly'] = int(match.group(1))
                    print(f"   ✅ Weekly: {match.group(1)}%")
                    break

    return usage_data

def close_browser_tab(browser):
    """브라우저 탭 닫기"""
    try:
        if browser == 'Chrome':
            script = '''
            tell application "Google Chrome"
                close active tab of front window
            end tell
            '''
        else:  # Safari
            script = '''
            tell application "Safari"
                close front document
            end tell
            '''
        run_applescript(script)
        print("   ✅ 브라우저 탭 닫음")
    except:
        pass

def main():
    print("=" * 60)
    print("Claude.ai Usage 자동 스크래핑 테스트")
    print("=" * 60)

    # 기본 브라우저 확인
    browser = get_default_browser()
    print(f"\n📱 기본 브라우저: {browser}")

    # 브라우저별 스크래핑 시도
    if browser == 'Chrome':
        page_text, error = scrape_usage_chrome()
    else:
        page_text, error = scrape_usage_safari()

    if not page_text:
        print(f"\n❌ 페이지 텍스트 추출 실패")
        if error:
            print(f"   에러: {error}")
        return

    # URL 확인 (로그인 페이지인지 체크)
    if 'login' in page_text.lower() and 'session' not in page_text.lower():
        print("\n⚠️  로그인이 필요합니다!")
        print(f"   1. {browser}를 열고 https://claude.ai 접속")
        print("   2. 로그인")
        print("   3. 다시 이 스크립트 실행")
        close_browser_tab(browser)
        return

    # Usage 정보 파싱
    usage_data = parse_usage_text(page_text)

    # 결과 출력
    print("\n" + "=" * 60)
    print("📊 스크래핑 결과:")
    print("=" * 60)

    if usage_data:
        print("✅ 추출 성공!\n")
        print(f"   Session: {usage_data.get('session', '?')}%")
        print(f"   Weekly: {usage_data.get('weekly', '?')}%")
        print("\n💾 JSON 형식:")
        print(json.dumps(usage_data, indent=2))

        # 자동 calibration 명령어
        if 'session' in usage_data and 'weekly' in usage_data:
            print(f"\n✨ 자동 Calibration 명령어:")
            print(f"   claude-calibrate {usage_data['session']} {usage_data['weekly']}")

    else:
        print("❌ Usage 정보를 찾을 수 없습니다.\n")
        print("📝 추출된 텍스트 샘플 (처음 500자):")
        print("-" * 60)
        print(page_text[:500])
        print("-" * 60)

    # 정리
    print("\n4. 정리 중...")
    close_browser_tab(browser)
    print("   ✅ 완료")

if __name__ == "__main__":
    print("\n⚠️  주의사항:")
    print(f"   1. 기본 브라우저가 열리고 Usage 페이지가 표시됩니다")
    print("   2. 먼저 브라우저에서 claude.ai에 로그인해두세요")
    print("   3. 로그인하지 않으면 실패합니다")
    print("")
    print("계속하려면 Enter를 누르세요...")
    input()

    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자가 중단했습니다.")
    except Exception as e:
        print(f"\n❌ 예상치 못한 에러: {e}")
        import traceback
        traceback.print_exc()
