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
MIN_LEARNED_LIMIT = 100  # TPM 최소값
MAX_LEARNED_LIMIT = 20000  # TPM 최대값


def load_session_config():
    """Config에서 세션 설정 읽기"""
    from pathlib import Path
    config_file = Path.home() / '.claude-monitor' / 'config.json'

    if not config_file.exists():
        return 14  # 기본값

    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        return config.get('reset_schedule', {}).get('session_base_hour', 14)
    except:
        return 14


def get_session_window_key(now: datetime) -> str:
    """
    현재 시간이 속한 세션 윈도우 키 반환 (config 기반)

    Returns:
        str: 'HH:MM-HH:MM' 형식 (예: '14:00-19:00')
    """
    base_hour = load_session_config()
    hour = now.hour

    # Base hour를 기준으로 5개의 5시간 윈도우 생성
    windows = []
    current_start = base_hour
    for _ in range(5):
        current_end = (current_start + 5) % 24
        windows.append((current_start, current_end))
        current_start = current_end

    # 현재 시간이 속한 윈도우 찾기
    for win_start, win_end in windows:
        if win_end < win_start:  # 자정을 넘어가는 경우
            if hour >= win_start or hour < win_end:
                return f"{win_start:02d}:00-{win_end:02d}:00"
        else:  # 같은 날 내
            if win_start <= hour < win_end:
                return f"{win_start:02d}:00-{win_end:02d}:00"

    # 기본값
    return f"{base_hour:02d}:00-{(base_hour + 5) % 24:02d}:00"


def get_weekly_window_key() -> str:
    """
    주간 윈도우 키 반환 (항상 고정)

    Returns:
        str: 'weekly'
    """
    return "weekly"


def get_window_end_time(window_key: str) -> datetime:
    """
    윈도우 종료 시간 계산 (window_key 파싱)

    Args:
        window_key: 'HH:MM-HH:MM' 형식 (예: '14:00-19:00') 또는 'weekly'

    Returns:
        datetime: 윈도우 종료 시간
    """
    from datetime import timedelta

    tz = ZoneInfo('Asia/Seoul')
    now = datetime.now(tz)

    # 주간 윈도우는 7일 후로 설정
    if window_key == "weekly":
        return now + timedelta(days=7)

    # window_key 파싱 (예: '14:00-19:00' → end_hour = 19)
    try:
        parts = window_key.split('-')
        end_time_str = parts[1]  # '19:00'
        end_hour = int(end_time_str.split(':')[0])
    except:
        end_hour = 19  # 기본값

    # 종료 시간 계산
    if end_hour == 0:
        # 자정인 경우
        if now.hour >= 12:
            # 현재가 오후/밤이면 다음날 00시
            window_end = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            # 현재가 새벽이면 오늘 00시
            window_end = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif end_hour < now.hour:
        # 종료 시간이 현재보다 이전이면 오늘 (세션 진행 중)
        window_end = now.replace(hour=end_hour, minute=0, second=0, microsecond=0)
    else:
        # 종료 시간이 현재보다 이후면 오늘
        window_end = now.replace(hour=end_hour, minute=0, second=0, microsecond=0)

    return window_end


def reverse_calculate_limit(actual_percentage: float, current_tokens: int, window_minutes: int = 300) -> Optional[int]:
    """
    실제 퍼센트와 현재 토큰으로 limit 역산

    Args:
        actual_percentage: 실제 퍼센트 (0-100)
        current_tokens: 현재 토큰 사용량
        window_minutes: 윈도우 시간(분) (기본: 300분 = 5시간)

    Returns:
        int: TPM (tokens per minute) 또는 None

    예시:
        actual = 39%, tokens = 103,279, window = 300분
        → limit = 103,279 / 0.39 / 300 = 882 TPM
    """
    if actual_percentage <= 0 or current_tokens <= 0:
        return None

    limit_per_minute = current_tokens / (actual_percentage / 100) / window_minutes
    limit_rounded = round(limit_per_minute)

    # 범위 검증
    if limit_rounded < MIN_LEARNED_LIMIT:
        print(f"⚠️  Warning: Calculated limit ({limit_rounded} TPM) too low, using minimum ({MIN_LEARNED_LIMIT} TPM)")
        return MIN_LEARNED_LIMIT
    elif limit_rounded > MAX_LEARNED_LIMIT:
        print(f"⚠️  Warning: Calculated limit ({limit_rounded} TPM) too high, using maximum ({MAX_LEARNED_LIMIT} TPM)")
        return MAX_LEARNED_LIMIT

    return limit_rounded


def set_calibration_override(window_key: str, calibrated_pct: float, learned_limit: int, expires_at: str):
    """
    세션에 override 값 설정 (즉시 반영)

    Args:
        window_key: 세션 윈도우 키
        calibrated_pct: 캘리브레이션된 퍼센트 (0-100)
        learned_limit: 학습된 limit (TPM)
        expires_at: 만료 시간 (ISO format)
    """
    data = load_calibration_data()

    if window_key not in data:
        data[window_key] = {'history': [], 'model': None}

    data[window_key]['latest_override'] = {
        'timestamp': datetime.now(ZoneInfo('Asia/Seoul')).isoformat(),
        'calibrated_percentage': calibrated_pct,
        'expires_at': expires_at,
        'learned_limit': learned_limit
    }

    save_calibration_data(data)


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


def get_global_fallback_limit() -> Optional[int]:
    """
    모든 세션의 learned_output_limit을 가중 평균하여 fallback limit 계산

    Returns:
        int: Global fallback output limit (TPM), 데이터 없으면 None
    """
    data = load_calibration_data()

    limits = []
    weights = []

    # 모든 세션 윈도우에서 learned_output_limit 수집 (weekly 제외)
    for window_key, window_data in data.items():
        if window_key == "weekly":
            continue

        model = window_data.get('model')
        if not model:
            continue

        learned_limit = model.get('learned_output_limit')
        sample_count = model.get('sample_count', 0)

        # Learned limit이 있고 샘플이 3개 이상인 경우만 사용
        if learned_limit and learned_limit > 0 and sample_count >= 3:
            limits.append(learned_limit)
            # 샘플 수에 비례한 가중치 (더 많은 샘플 = 더 높은 신뢰도)
            weight = min(sample_count / 10.0, 1.0)  # 최대 1.0
            weights.append(weight)

    if not limits:
        return None

    # 가중 평균 계산
    total_weight = sum(weights)
    weighted_avg = sum(l * w for l, w in zip(limits, weights)) / total_weight

    return round(weighted_avg)


def get_monitor_reading() -> Optional[Tuple[float, float, str, Dict]]:
    """
    현재 모니터가 읽은 사용량 가져오기

    Returns:
        tuple: (session_pct, weekly_pct, session_window_key, token_data) or None
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

        # 토큰 사용량 데이터
        token_data = {
            'input_tokens': data['session']['usage']['input_tokens'],
            'output_tokens': data['session']['usage']['output_tokens'],
            'cache_creation_tokens': data['session']['usage']['cache_creation_tokens'],
            'total_counted_tokens': data['session']['usage']['total_counted_tokens']
        }

        return session_pct / 100.0, weekly_pct / 100.0, window_key, token_data

    except Exception as e:
        print(f"⚠️  Error reading monitor output: {e}")
        return None


def record_calibration_point(window_key: str, monitor_value: float, actual_value: float, token_data: Dict = None) -> Dict:
    """
    보정 포인트 기록 (세션별)

    Args:
        window_key: 세션 윈도우 키
        monitor_value: 모니터 읽은 값 (0.0 ~ 1.0)
        actual_value: 실제 값 (0.0 ~ 1.0)
        token_data: 토큰 사용량 데이터 (optional)

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

    # 토큰 데이터 추가 (limit 역산용)
    if token_data:
        point['token_data'] = token_data

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

    # 적응형 샘플 선택 (초기에는 적게, 나중에는 많이)
    sample_count = len(history)
    if sample_count <= 10:
        # 초기: 최근 5개 (빠른 학습)
        recent_history = history[-5:]
        target_samples = 10
    elif sample_count <= 30:
        # 중기: 최근 20개 (안정화)
        recent_history = history[-20:]
        target_samples = 30
    else:
        # 후기: 최근 50개 (장기 정확도)
        recent_history = history[-50:]
        target_samples = 50

    # Limit 학습 (토큰 데이터가 있는 경우)
    learned_input_limit = None
    learned_output_limit = None

    # 토큰 데이터가 있는 샘플들로 limit 역산
    samples_with_tokens = [p for p in recent_history if 'token_data' in p]

    if len(samples_with_tokens) >= 3:
        # Input limit 학습 (input + cache_creation 기준)
        input_limits = []
        output_limits = []

        for point in samples_with_tokens:
            if point['actual_value'] > 0:  # 0% 제외
                tokens = point['token_data']
                input_total = tokens['input_tokens'] + tokens['cache_creation_tokens']
                output_total = tokens['output_tokens']

                # 역산: limit = tokens / (percentage / 100) / 300분
                input_limit_per_min = input_total / (point['actual_value'] * 300)
                output_limit_per_min = output_total / (point['actual_value'] * 300)

                input_limits.append(input_limit_per_min)
                output_limits.append(output_limit_per_min)

        if input_limits:
            # Exponential weighted average
            decay_factor = 0.85
            weights = [decay_factor ** (len(input_limits) - 1 - i) for i in range(len(input_limits))]
            total_weight = sum(weights)

            learned_input_limit = sum(l * w for l, w in zip(input_limits, weights)) / total_weight
            learned_output_limit = sum(l * w for l, w in zip(output_limits, weights)) / total_weight

    # Offset 계산 (fallback용)
    offsets = [point['offset'] for point in recent_history]

    # Exponential weighted average (최근 것일수록 가중치 높음)
    weights = []
    decay_factor = 0.9
    for i in range(len(offsets)):
        weight = decay_factor ** (len(offsets) - 1 - i)  # 최신일수록 높음
        weights.append(weight)

    total_weight = sum(weights)
    weighted_offsets = [o * w for o, w in zip(offsets, weights)]
    offset_mean = sum(weighted_offsets) / total_weight

    # 표준편차 계산
    offset_variance = sum(((x - offset_mean) ** 2) * w for x, w in zip(offsets, weights)) / total_weight
    offset_std = offset_variance ** 0.5

    # Confidence 계산
    # 샘플이 많고 표준편차가 작을수록 confidence 높음
    sample_confidence = min(sample_count / target_samples, 1.0)
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
        'window_key': window_key,
        'learned_input_limit': round(learned_input_limit, 0) if learned_input_limit else None,
        'learned_output_limit': round(learned_output_limit, 0) if learned_output_limit else None,
        'has_limit_learning': learned_input_limit is not None
    }

    data[window_key]['model'] = model
    save_calibration_data(data)

    return model


def get_calibrated_value(monitor_value: float, window_key: str) -> Dict:
    """
    보정된 값 반환 (Override 최우선, 세션별)

    Args:
        monitor_value: 모니터 읽은 값 (0.0 ~ 1.0)
        window_key: 세션 윈도우 키

    Returns:
        dict: 보정 정보
    """
    data = load_calibration_data()

    # 1. Override 확인 (최우선)
    if window_key in data and 'latest_override' in data[window_key]:
        override = data[window_key]['latest_override']
        expires_at = datetime.fromisoformat(override['expires_at'])
        now = datetime.now(ZoneInfo('Asia/Seoul'))

        # Override 유효성 검증
        is_valid = False

        # 세션 윈도우인 경우 - 현재 윈도우와 일치해야 함
        if window_key != "weekly":
            current_window = get_session_window_key(now)
            if current_window == window_key and now < expires_at:
                is_valid = True
            elif current_window != window_key:
                # 다른 윈도우의 override → 삭제
                del data[window_key]['latest_override']
                save_calibration_data(data)
        else:
            # 주간은 시간만 체크
            if now < expires_at:
                is_valid = True

        # Override가 유효하면 적용
        if is_valid:
            learned_limit = override.get('learned_limit')

            # Learned limit 유효성 검증
            if learned_limit and learned_limit > 0:
                if learned_limit < MIN_LEARNED_LIMIT or learned_limit > MAX_LEARNED_LIMIT:
                    # 범위 벗어나면 fallback로 처리
                    learned_limit = None

            if learned_limit and learned_limit > 0:
                # Learned limit이 있으면 실시간 토큰 계산
                try:
                    output_file = Path.home() / '.claude_usage.json'
                    with open(output_file, 'r') as f:
                        usage_data = json.load(f)

                    # 윈도우에 따라 토큰 데이터 선택
                    if window_key == "weekly":
                        # 주간 사용량
                        input_total = usage_data['weekly']['usage']['input_tokens'] + \
                                      usage_data['weekly']['usage']['cache_creation_tokens']
                        output_total = usage_data['weekly']['usage']['output_tokens']
                        window_minutes = 7 * 24 * 60  # 7일
                    else:
                        # 세션 사용량
                        input_total = usage_data['session']['usage']['input_tokens'] + \
                                      usage_data['session']['usage']['cache_creation_tokens']
                        output_total = usage_data['session']['usage']['output_tokens']
                        window_minutes = 300  # 5시간

                    # Learned limit으로 percentage 계산 (output 기준)
                    calibrated_pct = (output_total / (learned_limit * window_minutes)) * 100
                    calibrated_value = calibrated_pct / 100.0
                    method = 'override_limit_based'
                except Exception as e:
                    # 실패시 고정값 사용
                    calibrated_value = override['calibrated_percentage'] / 100
                    method = 'override_fixed'
            else:
                # Learned limit 없으면 고정값 사용
                calibrated_value = override['calibrated_percentage'] / 100
                method = 'override_fixed'

            return {
                'original_value': round(monitor_value, 4),
                'calibrated_value': round(calibrated_value, 4),
                'offset_applied': round(calibrated_value - monitor_value, 4),
                'confidence': 1.0,  # Override는 100% 신뢰
                'status': 'override',
                'method': method,
                'threshold': BASELINE_THRESHOLD,
                'window_key': window_key,
                'expires_at': override['expires_at'],
                'learned_limit': learned_limit
            }
        elif now >= expires_at:
            # Override 만료됨 → 삭제
            del data[window_key]['latest_override']
            save_calibration_data(data)

    # 2. 해당 윈도우의 모델 확인
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

    if model['sample_count'] < 3:
        # 충분한 데이터 없음 - Global fallback limit 시도
        fallback_limit = get_global_fallback_limit()

        if fallback_limit and fallback_limit > 0 and window_key != "weekly":
            # Fallback limit으로 계산 (다른 세션의 학습 데이터 사용)
            try:
                output_file = Path.home() / '.claude_usage.json'
                with open(output_file, 'r') as f:
                    usage_data = json.load(f)

                output_total = usage_data['session']['usage']['output_tokens']
                calibrated_pct = (output_total / (fallback_limit * 300)) * 100
                calibrated_value = calibrated_pct / 100.0

                return {
                    'original_value': round(monitor_value, 4),
                    'calibrated_value': round(calibrated_value, 4),
                    'offset_applied': round(calibrated_value - monitor_value, 4),
                    'confidence': 0.5,  # 중간 신뢰도
                    'status': 'learning_with_fallback',
                    'threshold': BASELINE_THRESHOLD,
                    'window_key': window_key,
                    'method': 'fallback_limit',
                    'fallback_limit': fallback_limit
                }
            except:
                pass  # Fallback 실패시 원본값 사용

        # Fallback도 실패하면 원본값 사용
        return {
            'original_value': round(monitor_value, 4),
            'calibrated_value': round(monitor_value, 4),
            'offset_applied': 0.0,
            'confidence': model['confidence'],
            'status': 'insufficient_data',
            'threshold': BASELINE_THRESHOLD,
            'window_key': window_key
        }

    # 보정값 적용 (3개 샘플부터)
    # Limit 학습이 완료된 경우 learned limit 사용, 아니면 offset 사용
    if model.get('has_limit_learning'):
        # Limit 기반 예측 (더 정확함)
        # 현재 토큰 사용량 읽기
        try:
            output_file = Path.home() / '.claude_usage.json'
            with open(output_file, 'r') as f:
                data = json.load(f)

            input_total = data['session']['usage']['input_tokens'] + data['session']['usage']['cache_creation_tokens']
            output_total = data['session']['usage']['output_tokens']

            # Learned limit으로 percentage 계산
            input_pct = (input_total / (model['learned_input_limit'] * 300)) * 100
            output_pct = (output_total / (model['learned_output_limit'] * 300)) * 100
            calibrated_value = max(input_pct, output_pct) / 100.0

            method = 'limit_based'
        except:
            # 실패시 offset 방식으로 fallback
            calibrated_value = monitor_value + model['offset_mean']
            method = 'offset_fallback'
    else:
        # Limit 학습이 없음 - Global fallback limit 시도
        fallback_limit = get_global_fallback_limit()

        if fallback_limit and fallback_limit > 0 and window_key != "weekly":
            # Fallback limit으로 계산 (다른 세션의 학습 데이터 사용)
            try:
                output_file = Path.home() / '.claude_usage.json'
                with open(output_file, 'r') as f:
                    usage_data = json.load(f)

                output_total = usage_data['session']['usage']['output_tokens']
                calibrated_pct = (output_total / (fallback_limit * 300)) * 100
                calibrated_value = calibrated_pct / 100.0
                method = 'fallback_limit'
            except:
                # Fallback 실패시 offset 방식으로 fallback
                calibrated_value = monitor_value + model['offset_mean']
                method = 'offset_based'
        else:
            # Fallback도 없으면 offset 기반 예측
            calibrated_value = monitor_value + model['offset_mean']
            method = 'offset_based'
            fallback_limit = None

    threshold = BASELINE_THRESHOLD * (1.0 + model['confidence'] * 0.5)

    return {
        'original_value': round(monitor_value, 4),
        'calibrated_value': round(calibrated_value, 4),
        'offset_applied': round(model['offset_mean'], 4),
        'confidence': model['confidence'],
        'status': model['status'],
        'threshold': round(threshold, 4),
        'window_key': window_key,
        'method': method,
        'learned_limits': {
            'input': model.get('learned_input_limit'),
            'output': model.get('learned_output_limit')
        } if model.get('has_limit_learning') else None
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

    session_monitor, weekly_monitor, window_key, token_data = monitor_data

    # 2. 사용자에게 실제 값 물어보기
    actual_values = prompt_for_actual_usage(session_monitor, weekly_monitor, window_key)
    if actual_values is None:
        print("⏭️  Calibration skipped")
        return None

    session_actual, weekly_actual = actual_values

    # 3. 보정 포인트 기록 (토큰 데이터 포함)
    point = record_calibration_point(window_key, session_monitor, session_actual, token_data)

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


def calibrate_with_args(session_actual: float, weekly_actual: Optional[float] = None) -> Optional[Dict]:
    """
    커맨드 인자로 보정 수행 (즉시 반영 + 토큰 역산)

    Args:
        session_actual: 실제 세션 사용량 (0-100)
        weekly_actual: 실제 주간 사용량 (0-100, optional)

    Returns:
        dict: 결과 정보, 실패시 None
    """
    # 1. 모니터 값 읽기
    monitor_data = get_monitor_reading()
    if monitor_data is None:
        print("⚠️  No active monitor data")
        return None

    session_monitor, weekly_monitor, window_key, token_data = monitor_data

    # 2. 값 검증
    if session_actual < 0 or session_actual > 100:
        print(f"⚠️  Invalid session value: {session_actual}%")
        return None

    if weekly_actual is not None and (weekly_actual < 0 or weekly_actual > 100):
        print(f"⚠️  Invalid weekly value: {weekly_actual}%")
        return None

    # 3. 세션 토큰 역산으로 limit 계산
    session_window_minutes = 300  # 5시간

    input_total = token_data['input_tokens'] + token_data['cache_creation_tokens']
    output_total = token_data['output_tokens']

    learned_input_limit = reverse_calculate_limit(session_actual, input_total, session_window_minutes)
    learned_output_limit = reverse_calculate_limit(session_actual, output_total, session_window_minutes)

    # 4. 보정 포인트 기록 (토큰 데이터 포함, 학습용)
    session_actual_normalized = session_actual / 100.0
    point = record_calibration_point(window_key, session_monitor, session_actual_normalized, token_data)

    # 5. 세션 Override 설정 (즉시 반영, output_limit 사용)
    window_end = get_window_end_time(window_key)
    set_calibration_override(
        window_key,
        session_actual,
        learned_output_limit or 0,  # Output limit만 사용
        window_end.isoformat()
    )

    # 6. 모델 업데이트 (학습용)
    model = update_calibration_model(window_key)

    # 7. 결과 출력
    print(f"\n✅ 즉시 반영: {session_actual:.1f}% → SwiftBar에 표시됨")
    print(f"\n📊 Session Calibration for {window_key}:")
    print(f"   Monitor: {session_monitor*100:.1f}%")
    print(f"   Actual:  {session_actual:.1f}%")
    print(f"   Offset:  {point['offset']*100:+.1f}%")

    print(f"\n🎯 학습된 Limit:")
    if learned_input_limit:
        print(f"   Input:  {learned_input_limit:,} TPM")
    if learned_output_limit:
        print(f"   Output: {learned_output_limit:,} TPM")

    print(f"\n⏰ Override:")
    print(f"   만료 시간: {window_end.strftime('%H:%M')} ({window_end.strftime('%Y-%m-%d')})")
    print(f"   상태: 세션 끝날 때까지 {session_actual:.1f}% 고정 표시")

    print(f"\n📚 히스토리:")
    print(f"   샘플 수: {model['sample_count']}개")
    print(f"   신뢰도: {model['confidence']:.2f}")
    print(f"   상태: {model['status']}")

    result = {
        'status': 'success',
        'override': True,
        'session': {
            'calibrated_percentage': session_actual,
            'learned_limits': {
                'input': learned_input_limit,
                'output': learned_output_limit
            },
            'window_key': window_key,
            'expires_at': window_end.isoformat(),
            'point': point,
            'model': model
        }
    }

    # 8. 주간 사용량 처리
    if weekly_actual is not None:
        weekly_window_key = get_weekly_window_key()
        weekly_window_minutes = 7 * 24 * 60  # 7일 = 10080분

        # 주간 토큰으로 limit 역산 (주간 토큰 데이터는 별도로 읽어야 함)
        # 현재는 세션 토큰과 동일하게 사용 (실제로는 weekly usage 데이터 필요)
        try:
            output_file = Path.home() / '.claude_usage.json'
            with open(output_file, 'r') as f:
                usage_data = json.load(f)

            weekly_input_total = usage_data['weekly']['usage']['input_tokens'] + \
                                 usage_data['weekly']['usage']['cache_creation_tokens']
            weekly_output_total = usage_data['weekly']['usage']['output_tokens']

            weekly_learned_input_limit = reverse_calculate_limit(weekly_actual, weekly_input_total, weekly_window_minutes)
            weekly_learned_output_limit = reverse_calculate_limit(weekly_actual, weekly_output_total, weekly_window_minutes)

            # 주간 Override 설정
            weekly_window_end = get_window_end_time(weekly_window_key)
            set_calibration_override(
                weekly_window_key,
                weekly_actual,
                weekly_learned_output_limit or 0,  # Output limit만 사용
                weekly_window_end.isoformat()
            )

            weekly_offset = (weekly_actual / 100.0) - weekly_monitor
            print(f"\n📊 Weekly Calibration:")
            print(f"   Monitor: {weekly_monitor*100:.1f}%")
            print(f"   Actual:  {weekly_actual:.1f}%")
            print(f"   Offset:  {weekly_offset*100:+.1f}%")

            print(f"\n🎯 주간 학습된 Limit:")
            if weekly_learned_input_limit:
                print(f"   Input:  {weekly_learned_input_limit:,} TPM")
            if weekly_learned_output_limit:
                print(f"   Output: {weekly_learned_output_limit:,} TPM")

            print(f"\n⏰ 주간 Override:")
            print(f"   만료 시간: {weekly_window_end.strftime('%Y-%m-%d %H:%M')}")
            print(f"   상태: 7일간 {weekly_actual:.1f}% 고정 표시")

            result['weekly'] = {
                'calibrated_percentage': weekly_actual,
                'learned_limits': {
                    'input': weekly_learned_input_limit,
                    'output': weekly_learned_output_limit
                },
                'window_key': weekly_window_key,
                'expires_at': weekly_window_end.isoformat()
            }

        except Exception as e:
            print(f"\n⚠️  주간 Override 설정 실패: {e}")

    return result


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Calibration Learner v2',
        epilog='Examples:\n'
               '  %(prog)s 2.3 35.5    # Calibrate with session and weekly\n'
               '  %(prog)s 2.3         # Calibrate with session only\n'
               '  %(prog)s --status    # Show calibration status',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('session', type=float, nargs='?',
                        help='Actual session output percentage (e.g., 2.3)')
    parser.add_argument('weekly', type=float, nargs='?',
                        help='Actual weekly output percentage (optional, e.g., 35.5)')
    parser.add_argument('--calibrate', action='store_true',
                        help='Run calibration with interactive prompt (legacy)')
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
        # Legacy interactive mode
        result = auto_calibrate_with_prompt()
        if result:
            print(f"\n✨ Calibration complete!")
    elif args.session is not None:
        # New argument-based mode
        result = calibrate_with_args(args.session, args.weekly)
        if result:
            print(f"\n✨ Calibration complete!")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
