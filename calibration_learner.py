#!/usr/bin/env python3
"""
Calibration Learner v2 - Per-session window calibration

개선사항:
1. 매번 모니터 체크시 자동 보정 (사용자 입력 받음)
2. 세션 윈도우별 독립적 학습 (15:00-20:00, 20:00-01:00 등)
3. 리셋 타임 고려 - 세션 바뀌면 해당 윈도우 데이터만 사용
"""

import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Optional, Tuple


# 파일 경로
CALIBRATION_DATA_FILE = Path.home() / '.claude-monitor' / 'calibration_data.json'
BASELINE_THRESHOLD = 0.15  # 초기 baseline


def get_session_window_key(now: datetime) -> str:
    """
    현재 시간이 속한 세션 윈도우 키 반환

    Returns:
        str: 'HH:MM-HH:MM' 형식 (예: '09:00-14:00')
    """
    hour = now.hour

    if 9 <= hour < 14:
        return '09:00-14:00'
    elif 14 <= hour < 19:
        return '14:00-19:00'
    elif 19 <= hour < 24:
        return '19:00-00:00'
    elif 0 <= hour < 4:
        return '00:00-04:00'
    elif 4 <= hour < 9:
        return '04:00-09:00'
    else:
        return '09:00-14:00'


def load_calibration_data() -> Dict:
    """
    보정 데이터 로드

    구조:
    {
        "15:00-20:00": {
            "history": [...],
            "model": {...}
        },
        "20:00-01:00": {...},
        ...
    }
    """
    if not CALIBRATION_DATA_FILE.exists():
        return {}

    try:
        with open(CALIBRATION_DATA_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}


def save_calibration_data(data: Dict):
    """보정 데이터 저장"""
    CALIBRATION_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CALIBRATION_DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def get_monitor_reading() -> Optional[Tuple[float, float, str]]:
    """
    현재 모니터가 읽은 사용량 가져오기

    Returns:
        tuple: (session_pct, weekly_pct, session_window_key) or None
    """
    output_file = Path.home() / '.claude_usage.json'

    if not output_file.exists():
        return None

    try:
        with open(output_file, 'r') as f:
            data = json.load(f)

        if data.get('status') != 'active':
            return None

        # Session & Weekly max percentage
        session_pct = data['session']['percentages']['max_percentage']
        weekly_pct = data['weekly']['percentages']['max_percentage']

        # 세션 윈도우 정보
        session_start_str = data['session']['window']['start']
        session_start = datetime.fromisoformat(session_start_str)
        window_key = get_session_window_key(session_start)

        return session_pct / 100.0, weekly_pct / 100.0, window_key

    except Exception as e:
        print(f"⚠️  Error reading monitor output: {e}")
        return None


def record_calibration_point(window_key: str, monitor_value: float, actual_value: float) -> Dict:
    """
    보정 포인트 기록 (세션별)

    Args:
        window_key: 세션 윈도우 키
        monitor_value: 모니터 읽은 값 (0.0 ~ 1.0)
        actual_value: 실제 값 (0.0 ~ 1.0)

    Returns:
        dict: 기록된 포인트
    """
    tz = ZoneInfo('Asia/Seoul')
    now = datetime.now(tz)

    offset = actual_value - monitor_value

    point = {
        'timestamp': now.isoformat(),
        'monitor_value': round(monitor_value, 4),
        'actual_value': round(actual_value, 4),
        'offset': round(offset, 4),
        'absolute_error': round(abs(offset), 4)
    }

    # 데이터 로드
    data = load_calibration_data()

    # 해당 윈도우 초기화
    if window_key not in data:
        data[window_key] = {
            'history': [],
            'model': None
        }

    # 히스토리에 추가
    data[window_key]['history'].append(point)

    # 최대 200개까지만 보관 (윈도우별)
    if len(data[window_key]['history']) > 200:
        data[window_key]['history'] = data[window_key]['history'][-200:]

    save_calibration_data(data)

    return point


def update_calibration_model(window_key: str) -> Dict:
    """
    특정 세션 윈도우의 보정 모델 업데이트

    Args:
        window_key: 세션 윈도우 키

    Returns:
        dict: 업데이트된 모델
    """
    data = load_calibration_data()

    if window_key not in data:
        # 데이터 없음
        return {
            'offset_mean': 0.0,
            'offset_std': 0.0,
            'confidence': 0.0,
            'sample_count': 0,
            'last_updated': None,
            'baseline_threshold': BASELINE_THRESHOLD,
            'status': 'no_data',
            'window_key': window_key
        }

    history = data[window_key]['history']

    if len(history) < 3:
        # 데이터가 충분하지 않음
        model = {
            'offset_mean': 0.0,
            'offset_std': 0.0,
            'confidence': 0.0,
            'sample_count': len(history),
            'last_updated': datetime.now(ZoneInfo('Asia/Seoul')).isoformat(),
            'baseline_threshold': BASELINE_THRESHOLD,
            'status': 'insufficient_data',
            'window_key': window_key
        }
        data[window_key]['model'] = model
        save_calibration_data(data)
        return model

    # 최근 50개 샘플 사용 (윈도우별로 충분한 데이터)
    recent_history = history[-50:]

    # 통계 계산
    offsets = [point['offset'] for point in recent_history]
    offset_mean = sum(offsets) / len(offsets)
    offset_variance = sum((x - offset_mean) ** 2 for x in offsets) / len(offsets)
    offset_std = offset_variance ** 0.5

    # Confidence 계산
    # 샘플이 많고 표준편차가 작을수록 confidence 높음
    sample_confidence = min(len(recent_history) / 50.0, 1.0)  # 50개면 1.0
    stability_confidence = max(0.0, 1.0 - offset_std * 10)  # std가 작을수록 높음
    confidence = (sample_confidence + stability_confidence) / 2.0

    model = {
        'offset_mean': round(offset_mean, 4),
        'offset_std': round(offset_std, 4),
        'confidence': round(confidence, 2),
        'sample_count': len(history),
        'last_updated': datetime.now(ZoneInfo('Asia/Seoul')).isoformat(),
        'baseline_threshold': BASELINE_THRESHOLD,
        'status': 'learning' if confidence < 0.7 else 'learned',
        'recent_samples': len(recent_history),
        'window_key': window_key
    }

    data[window_key]['model'] = model
    save_calibration_data(data)

    return model


def get_calibrated_value(monitor_value: float, window_key: str) -> Dict:
    """
    보정된 값 반환 (세션별)

    Args:
        monitor_value: 모니터 읽은 값 (0.0 ~ 1.0)
        window_key: 세션 윈도우 키

    Returns:
        dict: 보정 정보
    """
    data = load_calibration_data()

    # 해당 윈도우의 모델 확인
    if window_key not in data or data[window_key]['model'] is None:
        # 모델 없음 - baseline 사용
        return {
            'original_value': round(monitor_value, 4),
            'calibrated_value': round(monitor_value, 4),
            'offset_applied': 0.0,
            'confidence': 0.0,
            'status': 'no_data',
            'threshold': BASELINE_THRESHOLD,
            'window_key': window_key
        }

    model = data[window_key]['model']

    if model['sample_count'] < 10:
        # 충분한 데이터 없음 - baseline 사용
        return {
            'original_value': round(monitor_value, 4),
            'calibrated_value': round(monitor_value, 4),
            'offset_applied': 0.0,
            'confidence': model['confidence'],
            'status': 'insufficient_data',
            'threshold': BASELINE_THRESHOLD,
            'window_key': window_key
        }

    # 보정값 적용
    calibrated_value = monitor_value + model['offset_mean']
    threshold = BASELINE_THRESHOLD * (1.0 + model['confidence'] * 0.5)

    return {
        'original_value': round(monitor_value, 4),
        'calibrated_value': round(calibrated_value, 4),
        'offset_applied': round(model['offset_mean'], 4),
        'confidence': model['confidence'],
        'status': model['status'],
        'threshold': round(threshold, 4),
        'window_key': window_key
    }


def prompt_for_actual_usage(session_monitor: float, weekly_monitor: float, window_key: str) -> Optional[Tuple[float, Optional[float]]]:
    """
    사용자에게 실제 사용량 입력 요청 (세션 + 주간)

    Args:
        session_monitor: 세션 모니터 값 (0.0 ~ 1.0)
        weekly_monitor: 주간 모니터 값 (0.0 ~ 1.0)
        window_key: 세션 윈도우 키

    Returns:
        tuple: (session_actual, weekly_actual or None), 취소시 None
    """
    try:
        print(f"\n{'='*60}")
        print(f"📊 Calibration Check for {window_key}")
        print(f"{'='*60}")
        print(f"Monitor Session: {session_monitor*100:.1f}%")
        print(f"Monitor Weekly:  {weekly_monitor*100:.1f}%")
        print(f"\nPlease check 'claude usage' and enter:")
        print(f"  Session Output: XX%")
        print(f"  Weekly Output:  XX%")
        print(f"\nPress Enter on Session to skip all.\n")

        # 세션 입력
        session_input = input("Actual Session Output %: ").strip()
        if not session_input or session_input.lower() in ['skip', 's', 'cancel', 'q']:
            return None

        session_input = session_input.replace('%', '').strip()
        session_actual = float(session_input)

        if session_actual < 0 or session_actual > 100:
            print(f"⚠️  Invalid: {session_actual}%")
            return None

        # 주간 입력 (선택사항)
        weekly_input = input("Actual Weekly Output % (Enter to skip): ").strip()
        if not weekly_input:
            print("⏭️  Weekly skipped")
            return (session_actual / 100.0, None)

        weekly_input = weekly_input.replace('%', '').strip()
        weekly_actual = float(weekly_input)

        if weekly_actual < 0 or weekly_actual > 100:
            print(f"⚠️  Invalid weekly: {weekly_actual}%")
            return (session_actual / 100.0, None)

        return (session_actual / 100.0, weekly_actual / 100.0)

    except ValueError:
        print(f"⚠️  Invalid input")
        return None
    except (EOFError, KeyboardInterrupt):
        return None
    except Exception as e:
        print(f"⚠️  Error: {e}")
        return None


def auto_calibrate_with_prompt() -> Optional[Dict]:
    """
    자동 보정 (사용자 입력 프롬프트 포함)

    모니터에서 값 읽고 → 사용자에게 실제 값 물어보고 → 기록

    Returns:
        dict: 결과 정보, 실패시 None
    """
    # 1. 모니터 값 읽기
    monitor_data = get_monitor_reading()
    if monitor_data is None:
        print("⚠️  No active monitor data")
        return None

    session_monitor, weekly_monitor, window_key = monitor_data

    # 2. 사용자에게 실제 값 물어보기
    actual_values = prompt_for_actual_usage(session_monitor, weekly_monitor, window_key)
    if actual_values is None:
        print("⏭️  Calibration skipped")
        return None

    session_actual, weekly_actual = actual_values

    # 3. 보정 포인트 기록
    point = record_calibration_point(window_key, session_monitor, session_actual)

    # 4. 모델 업데이트
    model = update_calibration_model(window_key)

    # 5. 결과 출력
    print(f"\n✅ Calibration recorded for {window_key}:")
    print(f"   Session Monitor: {session_monitor*100:.1f}%")
    print(f"   Session Actual:  {session_actual*100:.1f}%")
    print(f"   Offset:  {point['offset']*100:+.1f}%")
    print(f"   Samples: {model['sample_count']}")
    print(f"   Confidence: {model['confidence']:.2f} ({model['status']})")

    if weekly_actual is not None:
        weekly_offset = weekly_actual - weekly_monitor
        print(f"\n   Weekly Monitor: {weekly_monitor*100:.1f}%")
        print(f"   Weekly Actual:  {weekly_actual*100:.1f}%")
        print(f"   Weekly Offset:  {weekly_offset*100:+.1f}%")

    if model['sample_count'] < 10:
        remaining = 10 - model['sample_count']
        print(f"\n   ⏳ Need {remaining} more samples for {window_key}")
    elif model['status'] == 'learning':
        print(f"\n   📚 Learning in progress...")
    else:
        print(f"\n   ✅ Model ready for {window_key}!")

    return {
        'status': 'success',
        'window_key': window_key,
        'point': point,
        'model': model
    }


def show_status():
    """전체 보정 상태 출력"""
    data = load_calibration_data()

    if not data:
        print("No calibration data yet.")
        return

    print(f"\n{'='*60}")
    print("Calibration Status by Session Window")
    print(f"{'='*60}\n")

    for window_key in sorted(data.keys()):
        window_data = data[window_key]
        model = window_data.get('model')
        history_count = len(window_data.get('history', []))

        print(f"📊 {window_key}")
        print(f"   Samples: {history_count}")

        if model:
            print(f"   Offset: {model['offset_mean']*100:+.2f}%")
            print(f"   Confidence: {model['confidence']:.2f}")
            print(f"   Status: {model['status']}")
        else:
            print(f"   Status: No model yet")

        print()


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description='Calibration Learner v2')
    parser.add_argument('--calibrate', action='store_true',
                        help='Run calibration with prompt')
    parser.add_argument('--status', action='store_true',
                        help='Show calibration status')
    parser.add_argument('--history', action='store_true',
                        help='Show calibration history (JSON)')

    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.history:
        data = load_calibration_data()
        print(json.dumps(data, indent=2))
    elif args.calibrate:
        result = auto_calibrate_with_prompt()
        if result:
            print(f"\n✨ Calibration complete!")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
