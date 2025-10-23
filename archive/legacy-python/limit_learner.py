#!/usr/bin/env python3
"""
Claude Monitor - Limit Learner
P90 분석을 통한 동적 limit 학습
"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import statistics


HISTORY_FILE = Path.home() / '.claude-monitor' / 'session_history.json'
CONFIG_FILE = Path.home() / '.claude-monitor' / 'config.json'


def load_history():
    """히스토리 파일 로드"""
    if not HISTORY_FILE.exists():
        return {
            'sessions': [],
            'learned_limits': {
                'session': {
                    'output_tpm': None,
                    'confidence': 0.0,
                    'data_points': 0,
                    'status': 'insufficient_data',
                    'last_updated': None
                },
                'weekly': {
                    'output_tpm': None,
                    'confidence': 0.0,
                    'data_points': 0,
                    'status': 'insufficient_data',
                    'last_updated': None
                }
            }
        }

    with open(HISTORY_FILE, 'r') as f:
        return json.load(f)


def save_history(history):
    """히스토리 파일 저장"""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)


def record_session_snapshot(usage_data, window_start, window_end, percentages, tz):
    """
    현재 세션 스냅샷 기록

    Args:
        usage_data: 토큰 사용량 데이터
        window_start: 세션 시작 시간
        window_end: 세션 종료 시간
        percentages: 퍼센트 정보
        tz: Timezone
    """
    history = load_history()

    now = datetime.now(tz)
    window_start_str = window_start.isoformat()

    # 이미 같은 윈도우의 스냅샷이 있는지 확인
    existing_session = None
    for session in history['sessions']:
        if session['window_start'] == window_start_str:
            existing_session = session
            break

    # 스냅샷 데이터
    snapshot = {
        'output_tokens': usage_data['output_tokens'],
        'percentage': percentages['output_percentage'],
        'timestamp': now.isoformat()
    }

    if existing_session:
        # 기존 세션 업데이트
        existing_session['latest_snapshot'] = snapshot

        # Peak usage 업데이트
        if snapshot['output_tokens'] > existing_session['peak_usage']['output_tokens']:
            existing_session['peak_usage'] = snapshot
    else:
        # 새 세션 추가
        new_session = {
            'window_start': window_start_str,
            'window_end': window_end.isoformat(),
            'first_snapshot': snapshot,
            'latest_snapshot': snapshot,
            'peak_usage': snapshot,
            'completed': False
        }
        history['sessions'].append(new_session)

    # 오래된 세션 정리 (30일 이상)
    cutoff = now - timedelta(days=30)
    history['sessions'] = [
        s for s in history['sessions']
        if datetime.fromisoformat(s['window_start']) > cutoff
    ]

    save_history(history)


def analyze_and_learn_limits():
    """
    히스토리 데이터를 분석하여 실제 limit 학습

    Returns:
        dict: 학습된 limit 정보
    """
    history = load_history()

    # 세션 데이터 분석
    session_data_points = []

    for session in history['sessions']:
        peak = session['peak_usage']

        # 50% 이상 사용한 세션 분석 (더 많은 데이터 수집)
        # 높은 퍼센트일수록 신뢰도가 높으므로 가중치 적용
        if peak['percentage'] >= 50:
            # 실제 limit 역산: output_tokens / (percentage / 100)
            # 예: 140,000 tokens / 0.46 = 304,348 total tokens
            # 304,348 tokens / 300 minutes = 1,014 TPM
            estimated_total_tokens = peak['output_tokens'] / (peak['percentage'] / 100)
            estimated_tpm = estimated_total_tokens / 300  # 5시간 = 300분

            # 신뢰도 가중치: 높은 퍼센트일수록 신뢰도 높음
            # 50% → 0.5, 70% → 0.7, 90% → 0.9
            confidence_weight = peak['percentage'] / 100

            session_data_points.append({
                'tpm': estimated_tpm,
                'percentage': peak['percentage'],
                'tokens': peak['output_tokens'],
                'weight': confidence_weight,
                'window_start': session['window_start']
            })

    # P90 분석 (90th percentile)
    learned_session_limit = history['learned_limits']['session'].copy()

    if len(session_data_points) >= 3:
        # 최소 3개의 데이터 포인트 필요
        tpm_values = [dp['tpm'] for dp in session_data_points]

        # 가중 평균 계산 (높은 퍼센트에 더 높은 가중치)
        weights = [dp['weight'] for dp in session_data_points]
        weighted_tpm = sum(t * w for t, w in zip(tpm_values, weights)) / sum(weights)

        # P90도 함께 계산 (보정용)
        p90_tpm = statistics.quantiles(tpm_values, n=10)[8] if len(tpm_values) >= 10 else max(tpm_values)

        # 가중 평균과 P90의 중간값 사용 (더 안정적)
        final_tpm = (weighted_tpm * 0.7 + p90_tpm * 0.3)

        # 신뢰도 계산 (데이터 포인트 수 + 평균 가중치)
        avg_weight = sum(weights) / len(weights)
        confidence = min(len(session_data_points) / 10 * avg_weight, 0.95)  # 최대 95%

        learned_session_limit = {
            'output_tpm': round(final_tpm),
            'confidence': round(confidence, 2),
            'data_points': len(session_data_points),
            'status': 'learned',
            'avg_percentage': round(sum(dp['percentage'] for dp in session_data_points) / len(session_data_points), 1),
            'last_updated': datetime.now(ZoneInfo('Asia/Seoul')).isoformat(),
            'sample_data': session_data_points[-5:]  # 최근 5개 샘플
        }
    elif len(session_data_points) > 0:
        # 데이터는 있지만 부족함
        learned_session_limit['data_points'] = len(session_data_points)
        learned_session_limit['status'] = 'learning'
        learned_session_limit['sample_data'] = session_data_points

    # 히스토리 업데이트
    history['learned_limits']['session'] = learned_session_limit
    save_history(history)

    return history['learned_limits']


def get_effective_limits(config):
    """
    효과적인 limit 값 가져오기 (학습된 값 우선, 없으면 기본값)

    Args:
        config: 설정 파일

    Returns:
        dict: 효과적인 limit 값
    """
    history = load_history()
    learned = history['learned_limits']

    # 세션 limit
    session_limit = config['rate_limits']['session'].copy()
    if learned['session']['status'] == 'learned' and learned['session']['confidence'] >= 0.7:
        # 신뢰도 70% 이상이면 학습된 값 사용
        session_limit['output_tokens_per_minute'] = learned['session']['output_tpm']
        session_limit['note'] = f"Learned from {learned['session']['data_points']} sessions (confidence: {learned['session']['confidence']*100:.0f}%)"
        session_limit['learned'] = True
    else:
        session_limit['learned'] = False

    # 주간 limit (현재는 학습 안 함, 추후 추가 가능)
    weekly_limit = config['rate_limits']['weekly'].copy()
    weekly_limit['learned'] = False

    return {
        'session': session_limit,
        'weekly': weekly_limit,
        'learning_status': learned
    }


def print_learning_status():
    """학습 상태 출력 (디버깅용)"""
    history = load_history()
    learned = history['learned_limits']

    print("\n" + "="*70)
    print("Limit Learning Status")
    print("="*70)

    print(f"\nSession Limit:")
    print(f"  Status: {learned['session']['status']}")
    print(f"  Data Points: {learned['session']['data_points']}")

    if learned['session']['output_tpm']:
        print(f"  Learned TPM: {learned['session']['output_tpm']}")
        print(f"  Confidence: {learned['session']['confidence']*100:.1f}%")
        print(f"  Last Updated: {learned['session'].get('last_updated', 'N/A')}")

    if learned['session'].get('sample_data'):
        print(f"\n  Recent Samples:")
        for i, sample in enumerate(learned['session']['sample_data'][-3:], 1):
            print(f"    {i}. {sample['percentage']:.1f}% ({sample['tokens']:,} tokens) → {sample['tpm']:.0f} TPM")

    print("\n" + "="*70 + "\n")


def main():
    """메인 함수 (테스트용)"""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--status':
        print_learning_status()
    elif len(sys.argv) > 1 and sys.argv[1] == '--analyze':
        print("Analyzing session history...")
        learned = analyze_and_learn_limits()
        print_learning_status()
    elif len(sys.argv) > 1 and sys.argv[1] == '--reset':
        print("Resetting session history...")
        if HISTORY_FILE.exists():
            HISTORY_FILE.unlink()
        print("✅ History reset complete")
    else:
        print("Usage:")
        print("  --status   Show learning status")
        print("  --analyze  Analyze history and learn limits")
        print("  --reset    Reset history")


if __name__ == '__main__':
    main()
