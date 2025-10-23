#!/usr/bin/env python3
"""
특정 시간대 윈도우의 캘리브레이션 데이터 정리
최근 N개의 샘플만 유지하고 나머지 삭제
"""

import json
import sys
from pathlib import Path
from datetime import datetime

CALIBRATION_FILE = Path.home() / '.claude-monitor' / 'calibration_data.json'


def load_calibration_data():
    """캘리브레이션 데이터 로드"""
    if not CALIBRATION_FILE.exists():
        print(f"❌ 캘리브레이션 파일이 없습니다: {CALIBRATION_FILE}")
        return None

    with open(CALIBRATION_FILE, 'r') as f:
        return json.load(f)


def save_calibration_data(data):
    """캘리브레이션 데이터 저장"""
    with open(CALIBRATION_FILE, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def cleanup_window_data(window_key, keep_recent=5, reset=False):
    """
    특정 윈도우의 데이터 정리

    Args:
        window_key: 윈도우 키 (예: "09:00-14:00")
        keep_recent: 유지할 최근 샘플 개수
        reset: True면 해당 윈도우 전체 삭제
    """
    data = load_calibration_data()
    if data is None:
        return False

    if window_key not in data:
        print(f"⚠️  윈도우 '{window_key}'가 존재하지 않습니다.")
        print(f"\n사용 가능한 윈도우:")
        for key in data.keys():
            print(f"  - {key}")
        return False

    window_data = data[window_key]
    history = window_data.get('history', [])

    print(f"\n{'='*70}")
    print(f"윈도우: {window_key}")
    print(f"{'='*70}")
    print(f"현재 샘플 수: {len(history)}개")

    if len(history) == 0:
        print("⚠️  데이터가 없습니다.")
        return False

    # 타임스탬프 기준 최근 샘플 정보 출력
    print(f"\n최근 샘플:")
    for i, sample in enumerate(reversed(history[-5:]), 1):
        ts = datetime.fromisoformat(sample['timestamp'])
        print(f"  {i}. {ts.strftime('%Y-%m-%d %H:%M:%S')} - "
              f"Monitor: {sample['monitor_value']:.3f}, "
              f"Actual: {sample['actual_value']:.3f}, "
              f"Offset: {sample['offset']:.3f}")

    if reset:
        # 전체 윈도우 삭제
        print(f"\n⚠️  '{window_key}' 윈도우를 완전히 삭제합니다...")
        del data[window_key]
        save_calibration_data(data)
        print(f"✅ '{window_key}' 윈도우가 삭제되었습니다.")
        return True

    if len(history) <= keep_recent:
        print(f"\n✅ 현재 샘플 수({len(history)}개)가 유지 개수({keep_recent}개) 이하입니다. 삭제할 데이터가 없습니다.")
        return False

    # 최근 N개만 유지
    removed_count = len(history) - keep_recent
    print(f"\n🗑️  오래된 {removed_count}개 샘플을 삭제합니다...")

    # 최근 N개만 남기기
    data[window_key]['history'] = history[-keep_recent:]

    # 모델 정보 업데이트
    data[window_key]['model']['sample_count'] = keep_recent
    data[window_key]['model']['last_updated'] = datetime.now().astimezone().isoformat()

    # 저장
    save_calibration_data(data)

    print(f"✅ {removed_count}개 샘플 삭제 완료!")
    print(f"✅ 최근 {keep_recent}개 샘플이 유지되었습니다.")

    return True


def list_all_windows():
    """모든 윈도우 정보 출력"""
    data = load_calibration_data()
    if data is None:
        return

    print(f"\n{'='*70}")
    print("모든 캘리브레이션 윈도우")
    print(f"{'='*70}")

    for window_key, window_data in data.items():
        history = window_data.get('history', [])
        model = window_data.get('model', {})

        print(f"\n📊 {window_key}")
        print(f"   샘플 수: {len(history)}개")
        print(f"   상태: {model.get('status', 'unknown')}")
        print(f"   신뢰도: {model.get('confidence', 0)*100:.1f}%")

        if history:
            oldest = datetime.fromisoformat(history[0]['timestamp'])
            newest = datetime.fromisoformat(history[-1]['timestamp'])
            print(f"   기간: {oldest.strftime('%Y-%m-%d %H:%M')} ~ {newest.strftime('%Y-%m-%d %H:%M')}")


def main():
    if len(sys.argv) < 2:
        print("사용법:")
        print("  python cleanup_window_data.py <window_key> [options]")
        print("")
        print("옵션:")
        print("  --list                  모든 윈도우 목록 보기")
        print("  --keep N                최근 N개 샘플만 유지 (기본: 5)")
        print("  --reset                 해당 윈도우 전체 삭제")
        print("")
        print("예시:")
        print("  python cleanup_window_data.py --list")
        print("  python cleanup_window_data.py '09:00-14:00'")
        print("  python cleanup_window_data.py '09:00-14:00' --keep 3")
        print("  python cleanup_window_data.py '09:00-14:00' --reset")
        return

    if sys.argv[1] == '--list':
        list_all_windows()
        return

    window_key = sys.argv[1]
    keep_recent = 5
    reset = False

    # 옵션 파싱
    for i in range(2, len(sys.argv)):
        if sys.argv[i] == '--keep' and i + 1 < len(sys.argv):
            keep_recent = int(sys.argv[i + 1])
        elif sys.argv[i] == '--reset':
            reset = True

    cleanup_window_data(window_key, keep_recent, reset)


if __name__ == '__main__':
    main()
