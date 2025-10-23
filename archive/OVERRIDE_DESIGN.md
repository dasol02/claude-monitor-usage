# 최우선 캘리브레이션 설계

## 📋 요구사항 분석

```bash
claude-calibrate 10 39
```

### 입력값:
- `10` = 모니터 값 (monitor_value: 10%)
- `39` = 실제 값 (actual_value: 39%) ← **Claude usage UI에서 확인한 정확한 값**

### 요구사항:
1. ✅ **즉시 반영**: 39%를 SwiftBar에 최우선으로 표시 (샘플 3개 기다리지 않고)
2. ✅ **토큰 역산**: 현재 토큰 사용량으로 limit 역산
3. ✅ **세션별 학습**: 현재 타임세션 (예: 14:00~19:00)에 데이터 저장
4. ✅ **이전 데이터 활용**: 이전 값들은 참고용으로 계속 학습에 사용

---

## 🎯 현재 문제점

### 문제 1: 샘플 3개 필요
```python
# calibration_learner.py:337
if model['sample_count'] < 3:
    return {..., 'offset_applied': 0.0}  # ❌ 적용 안 됨
```
→ 첫 캘리브레이션 입력해도 SwiftBar에 반영 안 됨

### 문제 2: 최신 값이 우선순위 없음
```python
# 모든 샘플이 동일한 가중치로 평균 계산
offset_mean = average(all_offsets)
```
→ 오래된 부정확한 값들이 최신 정확한 값의 효과를 희석시킴

### 문제 3: 즉시 반영 불가
- 캘리브레이션 입력 → 모델 업데이트 → 다음 모니터 실행 때 반영
- 실시간으로 SwiftBar에 보이지 않음

---

## 💡 해결 방안

### 방안 1: Override 메커니즘

```json
// calibration_data.json
{
  "14:00-19:00": {
    "history": [
      {
        "timestamp": "2025-10-16T11:42:00+09:00",
        "monitor_value": 0.10,
        "actual_value": 0.39,
        "offset": 0.29,
        "token_data": {...}
      }
    ],
    "latest_override": {  // ← 새로 추가
      "timestamp": "2025-10-16T11:42:00+09:00",
      "calibrated_percentage": 39.0,
      "expires_at": "2025-10-16T19:00:00+09:00",  // 현재 세션 끝날 때까지
      "learned_limit": 940  // 역산된 limit
    },
    "model": {...}
  }
}
```

**작동 방식:**
1. `claude-calibrate 10 39` 입력
2. `latest_override` 생성 (현재 세션 끝날 때까지 유효)
3. 모니터 데몬이 `latest_override` 최우선 사용
4. SwiftBar에 즉시 39% 표시

---

### 방안 2: 토큰 역산 로직

```python
def reverse_calculate_limit(actual_percentage, current_tokens, window_minutes=300):
    """
    실제 퍼센트와 현재 토큰으로 limit 역산

    예시:
    - actual_percentage = 39%
    - output_tokens = 103,279
    - window_minutes = 300 (5시간)

    계산:
    limit = tokens / (percentage / 100) / window_minutes
          = 103,279 / 0.39 / 300
          = 882 TPM
    """
    if actual_percentage <= 0:
        return None

    limit_per_minute = current_tokens / (actual_percentage / 100) / window_minutes
    return round(limit_per_minute)

# 사용 예시:
# output_tokens = 103,279
# actual = 39%
# → learned_output_limit = 882 TPM
```

---

### 방안 3: 최신 값 우선 가중치

현재는 exponential decay를 사용하지만, **가장 최신 값에 훨씬 더 높은 가중치** 부여:

```python
# 현재: decay_factor = 0.9
weights = [0.9^2, 0.9^1, 0.9^0] = [0.81, 0.9, 1.0]  # 비율: 81%, 90%, 100%

# 개선: 최신 값에 5배 가중치
if len(history) == 1:
    # 첫 입력이면 100% 신뢰
    offset_mean = history[0]['offset']
elif len(history) == 2:
    # 최신:이전 = 5:1
    weights = [1, 5]
    offset_mean = weighted_average([old, new], [1, 5])
else:
    # 최신 3개만 사용, 최신에 5배 가중치
    recent_3 = history[-3:]
    weights = [1, 2, 5]  # 오래된 것: 1, 중간: 2, 최신: 5
    offset_mean = weighted_average(recent_3, weights)
```

---

## 🔧 구현 계획

### 1단계: calibration_learner.py 수정

#### A. Override 기능 추가

```python
def set_calibration_override(window_key: str, calibrated_pct: float, learned_limit: int, expires_at: str):
    """세션에 override 값 설정"""
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
```

#### B. get_calibrated_value 수정

```python
def get_calibrated_value(monitor_value: float, window_key: str) -> Dict:
    """보정된 값 반환 (override 최우선)"""
    data = load_calibration_data()

    # 1. Override 확인 (최우선)
    if window_key in data and 'latest_override' in data[window_key]:
        override = data[window_key]['latest_override']
        expires_at = datetime.fromisoformat(override['expires_at'])

        if datetime.now(ZoneInfo('Asia/Seoul')) < expires_at:
            # Override 유효함 → 최우선 사용
            return {
                'original_value': round(monitor_value, 4),
                'calibrated_value': round(override['calibrated_percentage'] / 100, 4),
                'offset_applied': round((override['calibrated_percentage'] / 100) - monitor_value, 4),
                'confidence': 1.0,  # Override는 100% 신뢰
                'status': 'override',  # 새 상태
                'method': 'manual_override',
                'expires_at': override['expires_at']
            }

    # 2. 기존 로직 (모델 기반)
    if window_key not in data or data[window_key]['model'] is None:
        return {...}  # 기존 코드

    model = data[window_key]['model']

    # 샘플 1개부터 적용 (기존: 3개)
    if model['sample_count'] < 1:
        return {..., 'status': 'insufficient_data'}

    # 최신 값 우선 가중치 적용
    history = data[window_key]['history']
    if len(history) == 1:
        offset_mean = history[0]['offset']
    elif len(history) == 2:
        weights = [1, 5]
        offsets = [history[-2]['offset'], history[-1]['offset']]
        offset_mean = sum(o * w for o, w in zip(offsets, weights)) / sum(weights)
    else:
        recent_3 = history[-3:]
        weights = [1, 2, 5]
        offsets = [p['offset'] for p in recent_3]
        offset_mean = sum(o * w for o, w in zip(offsets, weights)) / sum(weights)

    calibrated_value = monitor_value + offset_mean

    return {
        'original_value': round(monitor_value, 4),
        'calibrated_value': round(calibrated_value, 4),
        'offset_applied': round(offset_mean, 4),
        'confidence': min(len(history) / 5, 1.0),
        'status': 'learning' if len(history) < 5 else 'calibrated',
        'method': 'weighted_offset'
    }
```

#### C. calibrate_with_args 수정

```python
def calibrate_with_args(session_actual: float, weekly_actual: Optional[float] = None) -> Optional[Dict]:
    """커맨드 인자로 보정 수행 (즉시 반영)"""

    # 1. 모니터 값 읽기
    monitor_data = get_monitor_reading()
    if monitor_data is None:
        return None

    session_monitor, weekly_monitor, window_key, token_data = monitor_data

    # 2. 토큰 역산으로 limit 계산
    window_minutes = 300  # 5시간

    input_total = token_data['input_tokens'] + token_data['cache_creation_tokens']
    output_total = token_data['output_tokens']

    learned_input_limit = reverse_calculate_limit(
        session_actual, input_total, window_minutes
    )
    learned_output_limit = reverse_calculate_limit(
        session_actual, output_total, window_minutes
    )

    # 3. 보정 포인트 기록 (토큰 데이터 포함)
    session_actual_normalized = session_actual / 100.0
    point = record_calibration_point(
        window_key,
        session_monitor,
        session_actual_normalized,
        token_data
    )

    # 4. Override 설정 (즉시 반영)
    window_end = get_window_end_time(window_key)
    set_calibration_override(
        window_key,
        session_actual,
        max(learned_input_limit, learned_output_limit),
        window_end.isoformat()
    )

    # 5. 모델 업데이트 (학습용)
    model = update_calibration_model(window_key)

    print(f"\n✅ 즉시 반영: {session_actual:.1f}% → SwiftBar에 표시됨")
    print(f"   학습된 limit: {learned_output_limit} TPM (output)")
    print(f"   Override 만료: {window_end.strftime('%H:%M')} (세션 끝)")
    print(f"   히스토리 샘플: {model['sample_count']}개 (참고용)")

    return {
        'status': 'success',
        'override': True,
        'calibrated_percentage': session_actual,
        'learned_limit': learned_output_limit,
        'model': model
    }
```

---

### 2단계: monitor_daemon.py 수정

```python
# Line 547-567
if CALIBRATION_ENABLED:
    try:
        calibration = get_calibrated_value(monitor_value, window_key)

        calibration_info = {...}

        # Override 또는 학습 상태면 적용
        if calibration['status'] in ['override', 'calibrated', 'learning']:
            display_percentage = calibration_info['calibrated_percentage']

    except Exception as e:
        print(f"Warning: Calibration failed: {e}")
```

---

### 3단계: 사용 예시

```bash
# 1. Claude usage UI에서 확인
# Session Output: 39%

# 2. 모니터 값 확인
python3 src/monitor_daemon.py --once | jq '.session.percentages.max_percentage'
# 출력: 26.2

# 3. 캘리브레이션 입력 (즉시 반영)
python3 src/calibration_learner.py 39

# 출력:
# ✅ 즉시 반영: 39.0% → SwiftBar에 표시됨
#    학습된 limit: 882 TPM (output)
#    Override 만료: 19:00 (세션 끝)
#    히스토리 샘플: 4개 (참고용)

# 4. SwiftBar 확인 → 🟢 39.0% 표시됨 ✅

# 5. 다음 세션 (19:00 이후) → Override 만료, 학습된 모델 사용
```

---

## 📊 데이터 플로우

```
[사용자 입력]
claude-calibrate 39
      ↓
[캘리브레이션 기록]
- history에 추가 (학습용)
- 토큰 역산 → limit 계산
- latest_override 설정 (즉시 반영용)
      ↓
[모니터 데몬 실행]
1. Override 확인
   └─ 있음 → 39% 사용 ✅
   └─ 없음 → 모델 기반 계산
      ↓
2. display_percentage = 39%
      ↓
3. JSON 저장
      ↓
[SwiftBar 표시]
🟢 39%
```

---

## ⏰ Override 만료 로직

```python
def get_window_end_time(window_key: str) -> datetime:
    """윈도우 종료 시간 계산"""
    tz = ZoneInfo('Asia/Seoul')
    now = datetime.now(tz)

    # 윈도우별 종료 시간
    windows = {
        '09:00-14:00': 14,
        '14:00-19:00': 19,
        '19:00-00:00': 0,   # 다음날 00시
        '00:00-04:00': 4,
        '04:00-09:00': 9
    }

    end_hour = windows[window_key]

    if end_hour == 0:
        # 다음날 00시
        window_end = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif end_hour < now.hour:
        # 이미 지났으면 다음날
        window_end = (now + timedelta(days=1)).replace(hour=end_hour, minute=0, second=0, microsecond=0)
    else:
        # 오늘 내
        window_end = now.replace(hour=end_hour, minute=0, second=0, microsecond=0)

    return window_end
```

---

## ✅ 장점

1. **즉시 반영**: 입력 즉시 SwiftBar에 표시
2. **정확한 Limit 학습**: 토큰 역산으로 실제 limit 파악
3. **세션별 관리**: 각 시간대마다 독립적으로 학습
4. **이전 데이터 활용**: 기존 히스토리는 참고용으로 계속 학습
5. **자동 만료**: 세션 끝나면 Override 만료, 학습된 모델 사용

---

## 🎯 구현 우선순위

1. ✅ **Phase 1**: Override 메커니즘 추가
2. ✅ **Phase 2**: 토큰 역산 로직 구현
3. ✅ **Phase 3**: 최신 값 우선 가중치
4. ⚠️ **Phase 4**: UI 개선 (선택사항)

---

## 🧪 테스트 시나리오

### 시나리오 1: 첫 캘리브레이션
```bash
# 샘플 0개 상태
python3 src/calibration_learner.py 39

# 예상 결과:
# - Override 설정 → 39% 즉시 표시 ✅
# - 샘플 1개 추가
# - Limit 학습: 882 TPM
```

### 시나리오 2: 추가 캘리브레이션
```bash
# 샘플 1개 상태, 10분 후 다시 입력
python3 src/calibration_learner.py 40

# 예상 결과:
# - Override 업데이트 → 40% 즉시 표시 ✅
# - 샘플 2개, 최신 값(40%)에 5배 가중치
# - Limit 재학습
```

### 시나리오 3: 세션 종료 후
```bash
# 19:00 이후 (새 세션 14:00-19:00 → 19:00-00:00)
python3 src/monitor_daemon.py --once

# 예상 결과:
# - 이전 Override 만료
# - 새 세션은 샘플 없음 → 원본 값 사용
# - 새 세션에 캘리브레이션 입력 가능
```

---

**이 설계로 구현할까요?**
