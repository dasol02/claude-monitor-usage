#!/usr/bin/env python3
"""
Claude Usage Monitor - Daemon v2
세션(5시간) 및 주간 사용량을 모니터링하고 JSON 출력
"""

import json
import os
import time
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import argparse

# Limit learner import
try:
    from limit_learner import record_session_snapshot, analyze_and_learn_limits, get_effective_limits
    LIMIT_LEARNING_ENABLED = True
except ImportError:
    LIMIT_LEARNING_ENABLED = False
    print("⚠️  Limit learning module not found. Using static limits.")


CONFIG_FILE = Path.home() / '.claude-monitor' / 'config.json'
OUTPUT_FILE = Path.home() / '.claude_usage.json'
NOTIFICATION_STATE_FILE = Path.home() / '.claude-monitor' / 'notification_state.json'


def load_config():
    """설정 파일 로드"""
    if not CONFIG_FILE.exists():
        print(f"❌ Configuration not found at {CONFIG_FILE}")
        print("   Please run: python3 src/config_manager.py")
        return None

    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)

    # Timezone 설정 추가 (없으면 기본값 사용)
    if 'display_settings' not in config:
        config['display_settings'] = {}
    if 'timezone' not in config['display_settings']:
        config['display_settings']['timezone'] = 'Asia/Seoul'
    if 'timezone_abbr' not in config['display_settings']:
        config['display_settings']['timezone_abbr'] = 'KST'

    return config


def find_all_sessions():
    """모든 Claude 프로젝트의 세션 파일 찾기"""
    home = Path.home()
    projects_dir = home / '.claude' / 'projects'

    if not projects_dir.exists():
        return []

    session_files = list(projects_dir.rglob('*.jsonl'))
    return session_files


def get_rolling_session_window(session_files, now, tz):
    """
    Rolling 5시간 세션 윈도우 계산 (사용 안 함)

    현재 세션의 가장 오래된 메시지 시작 시점부터 +5시간

    Args:
        session_files: 세션 파일 리스트
        now: 현재 시간
        tz: Timezone

    Returns:
        tuple: (window_start, window_end, next_reset)
    """
    # 일단 현재 시간부터 5시간 전까지 모든 메시지 스캔
    potential_start = now - timedelta(hours=5)

    oldest_message_time = None

    # 모든 세션 파일에서 5시간 내 가장 오래된 메시지 찾기
    for session_file in session_files:
        try:
            with open(session_file, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())

                        if data.get('type') == 'assistant' and 'message' in data:
                            timestamp_str = data.get('timestamp')
                            if not timestamp_str:
                                continue

                            msg_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                            msg_time = msg_time.astimezone(tz)

                            # 5시간 이내의 메시지만
                            if msg_time >= potential_start and msg_time <= now:
                                if oldest_message_time is None or msg_time < oldest_message_time:
                                    oldest_message_time = msg_time
                    except:
                        continue
        except:
            continue

    # 가장 오래된 메시지가 있으면 그 시점부터 +5시간
    if oldest_message_time:
        window_start = oldest_message_time
        window_end = oldest_message_time + timedelta(hours=5)
        next_reset = window_end
    else:
        # 메시지가 없으면 현재 시간 기준
        window_start = now
        window_end = now + timedelta(hours=5)
        next_reset = window_end

    return window_start, window_end, next_reset


def get_fixed_session_window(now):
    """
    고정된 5시간 세션 윈도우 계산 (기존 방식)

    결제일 기준으로 고정된 시간대:
    - 10:00 ~ 15:00
    - 15:00 ~ 20:00
    - 20:00 ~ 01:00
    - 01:00 ~ 06:00
    - 06:00 ~ 11:00 (다음날)

    Returns:
        tuple: (window_start, window_end, next_reset)
    """
    hour = now.hour

    # 현재 시간이 속한 5시간 윈도우 찾기
    if 10 <= hour < 15:
        start_hour = 10
        end_hour = 15
    elif 15 <= hour < 20:
        start_hour = 15
        end_hour = 20
    elif 20 <= hour < 24:
        start_hour = 20
        end_hour = 1  # 다음날 01:00
    elif 1 <= hour < 6:
        start_hour = 1
        end_hour = 6
    elif 6 <= hour < 10:
        start_hour = 6
        end_hour = 11
    else:  # 0시 ~ 1시
        start_hour = 20  # 전날 20:00
        end_hour = 1

    # 시작 시간 계산
    if hour < start_hour:
        # 전날에서 시작
        window_start = now.replace(hour=start_hour, minute=0, second=0, microsecond=0) - timedelta(days=1)
    else:
        window_start = now.replace(hour=start_hour, minute=0, second=0, microsecond=0)

    # 종료 시간 계산
    if end_hour < start_hour:
        # 다음날로 넘어감
        window_end = (window_start + timedelta(days=1)).replace(hour=end_hour, minute=0, second=0, microsecond=0)
    else:
        window_end = window_start.replace(hour=end_hour, minute=0, second=0, microsecond=0)

    # 다음 리셋 시간
    next_reset = window_end

    return window_start, window_end, next_reset


def get_weekly_window(now):
    """
    주간 윈도우 계산 (7일 = 168시간)

    현재 시간으로부터 7일 전

    Returns:
        tuple: (window_start, window_end, next_reset)
    """
    window_end = now
    window_start = now - timedelta(days=7)

    # 다음 리셋은 매주 화요일 (가정)
    # 실제로는 결제일 기준이지만, 일단 7일 롤링으로 처리
    next_reset = now + timedelta(days=1)  # 임시

    return window_start, window_end, next_reset


def parse_sessions_in_window(session_files, window_start, window_end, tz):
    """
    특정 시간 윈도우 내의 모든 세션에서 토큰 사용량 집계

    Args:
        session_files: 세션 파일 리스트
        window_start: 윈도우 시작 시간 (datetime)
        window_end: 윈도우 종료 시간 (datetime)
        tz: Timezone

    Returns:
        dict: 사용량 정보
    """
    usage_data = {
        'input_tokens': 0,
        'output_tokens': 0,
        'cache_read_tokens': 0,
        'cache_creation_tokens': 0,
        'total_counted_tokens': 0,
        'messages_count': 0,
        'oldest_message_time': None,
        'latest_message_time': None
    }

    for session_file in session_files:
        with open(session_file, 'r') as f:
            for line in f:
                try:
                    data = json.loads(line.strip())

                    # assistant 메시지에서 usage 정보 추출
                    if data.get('type') == 'assistant' and 'message' in data:
                        message = data['message']

                        # 타임스탬프 확인
                        timestamp_str = data.get('timestamp')
                        if not timestamp_str:
                            continue

                        msg_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        msg_time = msg_time.astimezone(tz)

                        # 윈도우 내의 메시지만 집계
                        if msg_time < window_start or msg_time > window_end:
                            continue

                        # 시간 추적
                        if usage_data['oldest_message_time'] is None:
                            usage_data['oldest_message_time'] = msg_time
                        usage_data['latest_message_time'] = msg_time

                        if 'usage' in message:
                            usage = message['usage']

                            usage_data['input_tokens'] += usage.get('input_tokens', 0)
                            usage_data['output_tokens'] += usage.get('output_tokens', 0)
                            usage_data['cache_read_tokens'] += usage.get('cache_read_input_tokens', 0)
                            usage_data['cache_creation_tokens'] += usage.get('cache_creation_input_tokens', 0)
                            usage_data['messages_count'] += 1

                except (json.JSONDecodeError, Exception):
                    continue

    # Cache read tokens는 rate limit에 카운트되지 않음
    usage_data['total_counted_tokens'] = (
        usage_data['input_tokens'] +
        usage_data['output_tokens'] +
        usage_data['cache_creation_tokens']
    )

    return usage_data


def calculate_usage_percentage(usage, limits):
    """
    사용량 퍼센트 계산

    Args:
        usage: 사용량 데이터
        limits: rate limit 설정 (session 또는 weekly)
    """
    window_minutes = limits['window_hours'] * 60

    # 윈도우 동안 사용 가능한 총 토큰
    total_input_limit = limits['input_tokens_per_minute'] * window_minutes
    total_output_limit = limits['output_tokens_per_minute'] * window_minutes

    # 퍼센트 계산
    input_pct = (usage['input_tokens'] / total_input_limit) * 100 if total_input_limit > 0 else 0
    output_pct = (usage['output_tokens'] / total_output_limit) * 100 if total_output_limit > 0 else 0

    # 가장 높은 퍼센트 사용
    max_pct = max(input_pct, output_pct)

    return {
        'input_percentage': round(input_pct, 1),
        'output_percentage': round(output_pct, 1),
        'max_percentage': round(max_pct, 1)
    }


def generate_progress_bar(percentage, width=10):
    """배터리 스타일 프로그레스 바 생성"""
    if percentage >= 100:
        filled = width
        empty = 0
    else:
        filled = int((percentage / 100) * width)
        empty = width - filled

    bar = '=' * filled + '-' * empty

    return f"[{int(percentage)}% {bar}]"


def load_notification_state():
    """알림 상태 파일 로드"""
    if not NOTIFICATION_STATE_FILE.exists():
        return {
            'session_window_start': None,
            'notified_thresholds': []
        }

    try:
        with open(NOTIFICATION_STATE_FILE, 'r') as f:
            return json.load(f)
    except:
        return {
            'session_window_start': None,
            'notified_thresholds': []
        }


def save_notification_state(state):
    """알림 상태 파일 저장"""
    NOTIFICATION_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(NOTIFICATION_STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def send_macos_notification(title, message, subtitle=None):
    """
    macOS 알림 전송 (osascript 사용)

    Args:
        title: 알림 제목
        message: 알림 메시지
        subtitle: 알림 부제목 (선택)
    """
    try:
        # AppleScript로 알림 전송
        script = f'display notification "{message}" with title "{title}"'
        if subtitle:
            script = f'display notification "{message}" with title "{title}" subtitle "{subtitle}"'

        os.system(f"osascript -e '{script}'")
    except Exception as e:
        print(f"Failed to send notification: {e}")


def check_and_send_notifications(config, session_percentage, session_window_start):
    """
    임계값을 확인하고 알림 전송

    Args:
        config: 설정 정보
        session_percentage: 현재 세션 사용량 (%)
        session_window_start: 현재 세션 시작 시간 (ISO format)

    Returns:
        list: 전송된 알림의 임계값 리스트
    """
    # 알림 비활성화 상태면 리턴
    if not config.get('notifications', {}).get('enabled', True):
        return []

    # 임계값 가져오기
    thresholds = config.get('notifications', {}).get('thresholds', [80, 90, 95])

    # 알림 상태 로드
    state = load_notification_state()

    # 세션 윈도우가 바뀌면 상태 리셋
    if state.get('session_window_start') != session_window_start:
        state = {
            'session_window_start': session_window_start,
            'notified_thresholds': []
        }
        save_notification_state(state)

    # 임계값 확인 및 알림 전송
    notified = []
    for threshold in sorted(thresholds):
        # 이미 알림을 보낸 임계값은 건너뛰기
        if threshold in state['notified_thresholds']:
            continue

        # 현재 사용량이 임계값을 넘으면 알림 전송
        if session_percentage >= threshold:
            tz_abbr = config['display_settings']['timezone_abbr']
            send_macos_notification(
                title="⚠️ Claude Usage Alert",
                message=f"Session usage has reached {session_percentage}%",
                subtitle=f"Threshold: {threshold}% ({tz_abbr})"
            )

            # 상태 업데이트
            state['notified_thresholds'].append(threshold)
            notified.append(threshold)

    # 상태 저장
    if notified:
        save_notification_state(state)

    return notified


def calculate_time_until_reset(now, reset_time):
    """
    리셋까지 남은 시간 계산

    Args:
        now: 현재 시간 (datetime)
        reset_time: 리셋 시간 (datetime)

    Returns:
        dict: 남은 시간 정보
    """
    time_diff = reset_time - now

    # 음수면 이미 지났음 (0으로 처리)
    if time_diff.total_seconds() < 0:
        return {
            'total_seconds': 0,
            'hours': 0,
            'minutes': 0,
            'human_readable': '0m',
            'human_readable_long': '0 minutes'
        }

    total_seconds = int(time_diff.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60

    # Human readable format
    if hours > 0:
        if minutes > 0:
            human_readable = f"{hours}h {minutes}m"
            human_readable_long = f"{hours} hours {minutes} minutes"
        else:
            human_readable = f"{hours}h"
            human_readable_long = f"{hours} hours"
    else:
        human_readable = f"{minutes}m"
        human_readable_long = f"{minutes} minutes"

    return {
        'total_seconds': total_seconds,
        'hours': hours,
        'minutes': minutes,
        'human_readable': human_readable,
        'human_readable_long': human_readable_long
    }


def monitor_once(config):
    """한 번 모니터링 실행"""
    # Timezone 설정
    tz_name = config['display_settings']['timezone']
    tz_abbr = config['display_settings']['timezone_abbr']
    tz = ZoneInfo(tz_name)

    # 세션 파일 찾기
    session_files = find_all_sessions()

    if not session_files:
        # 세션 파일이 없으면 빈 데이터 반환
        return {
            'status': 'no_session',
            'message': 'No active Claude session found',
            'timestamp': datetime.now(tz).isoformat(),
            'timezone': tz_name,
            'timezone_abbr': tz_abbr
        }

    # 현재 시간
    now = datetime.now(tz)

    # Limit learning 적용 (가능하면)
    if LIMIT_LEARNING_ENABLED:
        effective_limits = get_effective_limits(config)
        session_limits = effective_limits['session']
        weekly_limits = effective_limits['weekly']
        learning_status = effective_limits['learning_status']
    else:
        session_limits = config['rate_limits']['session']
        weekly_limits = config['rate_limits']['weekly']
        learning_status = None

    # 세션 윈도우 계산 (5시간 rolling)
    session_start, session_end, session_reset = get_fixed_session_window(now)
    session_usage = parse_sessions_in_window(session_files, session_start, session_end, tz)
    session_percentages = calculate_usage_percentage(session_usage, session_limits)

    # 세션 리셋까지 남은 시간 계산
    session_time_until_reset = calculate_time_until_reset(now, session_reset)

    # 히스토리 기록 및 자동 학습
    if LIMIT_LEARNING_ENABLED:
        try:
            # 세션 스냅샷 기록
            record_session_snapshot(
                session_usage,
                session_start,
                session_end,
                session_percentages,
                tz
            )

            # 주기적으로 자동 학습 실행 (매 10번째 실행마다)
            # 또는 세션이 70% 이상일 때
            if session_percentages['max_percentage'] >= 70:
                learned = analyze_and_learn_limits()
                if learned['session']['status'] == 'learned':
                    # 학습 완료되면 다음 실행부터 새 limit 적용
                    pass
        except Exception as e:
            print(f"Warning: Failed to record/learn session: {e}")

    # 주간 윈도우 계산 (7일)
    weekly_start, weekly_end, weekly_reset = get_weekly_window(now)
    weekly_usage = parse_sessions_in_window(session_files, weekly_start, weekly_end, tz)
    weekly_percentages = calculate_usage_percentage(weekly_usage, weekly_limits)

    # 주간 리셋까지 남은 시간 계산
    weekly_time_until_reset = calculate_time_until_reset(now, weekly_reset)

    # 알림 체크 및 전송 (세션 사용량 기준)
    notified_thresholds = check_and_send_notifications(
        config,
        session_percentages['max_percentage'],
        session_start.isoformat()
    )

    # 출력 데이터 생성
    output = {
        'status': 'active',
        'plan': config['plan'],
        'timezone': tz_name,
        'timezone_abbr': tz_abbr,
        'limit_learning': {
            'enabled': LIMIT_LEARNING_ENABLED,
            'session_status': learning_status['session']['status'] if learning_status else 'disabled',
            'session_confidence': learning_status['session']['confidence'] if learning_status else 0.0,
            'session_data_points': learning_status['session']['data_points'] if learning_status else 0
        },
        'notifications': {
            'enabled': config.get('notifications', {}).get('enabled', True),
            'thresholds': config.get('notifications', {}).get('thresholds', [80, 90, 95]),
            'notified_this_session': notified_thresholds
        },
        'session': {
            'usage': {
                'input_tokens': session_usage['input_tokens'],
                'output_tokens': session_usage['output_tokens'],
                'cache_creation_tokens': session_usage['cache_creation_tokens'],
                'cache_read_tokens': session_usage['cache_read_tokens'],
                'total_counted_tokens': session_usage['total_counted_tokens'],
                'messages_count': session_usage['messages_count']
            },
            'percentages': session_percentages,
            'limits': {
                'input_tokens_per_minute': session_limits['input_tokens_per_minute'],
                'output_tokens_per_minute': session_limits['output_tokens_per_minute'],
                'window_hours': session_limits['window_hours']
            },
            'window': {
                'start': session_start.isoformat(),
                'end': session_end.isoformat()
            },
            'reset': {
                'time': session_reset.strftime('%H:%M'),
                'time_12h': session_reset.strftime('%I:%M %p'),
                'iso': session_reset.isoformat(),
                'timezone': tz_name,
                'timezone_abbr': tz_abbr,
                'time_until_reset': session_time_until_reset,
                'note': f'{session_limits["window_hours"]}시간 rolling 윈도우'
            },
            'display': {
                'progress_bar': generate_progress_bar(session_percentages['max_percentage']),
                'status_line': f"{session_percentages['max_percentage']}% used, resets in {session_time_until_reset['human_readable']} ({session_reset.strftime('%H:%M')} {tz_abbr})"
            }
        },
        'weekly': {
            'usage': {
                'input_tokens': weekly_usage['input_tokens'],
                'output_tokens': weekly_usage['output_tokens'],
                'cache_creation_tokens': weekly_usage['cache_creation_tokens'],
                'cache_read_tokens': weekly_usage['cache_read_tokens'],
                'total_counted_tokens': weekly_usage['total_counted_tokens'],
                'messages_count': weekly_usage['messages_count']
            },
            'percentages': weekly_percentages,
            'limits': {
                'input_tokens_per_minute': weekly_limits['input_tokens_per_minute'],
                'output_tokens_per_minute': weekly_limits['output_tokens_per_minute'],
                'window_hours': weekly_limits['window_hours']
            },
            'window': {
                'start': weekly_start.isoformat(),
                'end': weekly_end.isoformat()
            },
            'reset': {
                'time': weekly_reset.strftime('%H:%M'),
                'time_12h': weekly_reset.strftime('%I:%M %p'),
                'iso': weekly_reset.isoformat(),
                'timezone': tz_name,
                'timezone_abbr': tz_abbr,
                'time_until_reset': weekly_time_until_reset,
                'note': '7일 rolling 윈도우'
            },
            'display': {
                'progress_bar': generate_progress_bar(weekly_percentages['max_percentage']),
                'status_line': f"{weekly_percentages['max_percentage']}% used (7 days)"
            }
        },
        'timestamp': datetime.now(tz).isoformat()
    }

    return output


def save_output(data):
    """출력 파일 저장"""
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def daemon_mode(config, interval=60):
    """데몬 모드로 지속 실행"""
    # Timezone 설정
    tz_name = config['display_settings']['timezone']
    tz = ZoneInfo(tz_name)

    print(f"🚀 Claude Usage Monitor Daemon v2 started")
    print(f"   Plan: {config['plan']['name']}")
    print(f"   Timezone: {tz_name}")
    print(f"   Output: {OUTPUT_FILE}")
    print(f"   Interval: {interval}s")
    print(f"   Press Ctrl+C to stop\\n")

    try:
        while True:
            # 모니터링 실행
            data = monitor_once(config)

            # 파일 저장
            save_output(data)

            # 상태 출력
            if data['status'] == 'active':
                session_bar = data['session']['display']['progress_bar']
                session_pct = data['session']['percentages']['max_percentage']
                weekly_pct = data['weekly']['percentages']['max_percentage']

                print(f"[{datetime.now(tz).strftime('%H:%M:%S')}] "
                      f"Session: {session_bar} {session_pct}% | "
                      f"Weekly: {weekly_pct}%")
            else:
                print(f"[{datetime.now(tz).strftime('%H:%M:%S')}] "
                      f"No active session")

            # 대기
            time.sleep(interval)

    except KeyboardInterrupt:
        print("\\n\\n✅ Daemon stopped")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='Claude Usage Monitor Daemon v2')
    parser.add_argument('--once', action='store_true',
                        help='Run once and exit (default: daemon mode)')
    parser.add_argument('--interval', type=int, default=60,
                        help='Update interval in seconds (default: 60)')

    args = parser.parse_args()

    # 설정 로드
    config = load_config()
    if not config:
        return 1

    if args.once:
        # 한 번만 실행
        data = monitor_once(config)
        save_output(data)
        print(json.dumps(data, indent=2))
    else:
        # 데몬 모드
        daemon_mode(config, args.interval)

    return 0


if __name__ == '__main__':
    exit(main())
