# 논리 연산 우선순위 및 조건 정리

## 📑 목차

1. [디스플레이 값 결정 로직](#-디스플레이-값-결정-로직)
   - [Monitor Daemon (monitor_daemon.py)](#1-monitor-daemon-monitor_daemonpy543-565)
   - [Calibration Learner (calibration_learner.py)](#2-calibration-learner-calibration_learnerpy309-392)
   - [SwiftBar Plugin (ClaudeUsage.1m.sh)](#3-swiftbar-plugin-claudeusage1msh47-61)

2. [캘리브레이션 모델 학습 조건](#-캘리브레이션-모델-학습-조건)
   - [Model Update 프로세스](#model-update-calibration_learnerpy172-306)

3. [Global Fallback Limit 시스템](#-global-fallback-limit-시스템)
   - [작동 원리](#작동-원리)
   - [Fallback 우선순위](#fallback-우선순위)
   - [가중 평균 계산](#가중-평균-계산)

4. [권장 조정 시나리오](#-권장-조정-시나리오)
   - [시나리오 1: 빠른 학습, 낮은 정확도](#시나리오-1-빠른-학습-낮은-정확도)
   - [시나리오 2: 느린 학습, 높은 정확도](#시나리오-2-느린-학습-높은-정확도)
   - [시나리오 3: 균형잡힌 설정 (현재 권장)](#시나리오-3-균형잡힌-설정-현재-권장)

5. [수정이 필요한 경우](#-수정이-필요한-경우)
   - [최소 샘플 수 변경](#1-최소-샘플-수-변경)
   - [Confidence 임계값 추가](#2-confidence-임계값-추가)
   - [SwiftBar status/confidence 확인](#3-swiftbar에서-statusconfidence-확인)

6. [테스트 체크리스트](#-테스트-체크리스트)

7. [현재 설정 요약](#현재-설정-요약)

8. [🆕 최근 개선사항](#-최근-개선사항-2025-10-16-2025-10-17)
   - [Override 실시간 계산 구현](#override-실시간-계산-구현-2025-10-16)
   - [Global Fallback Limit 시스템](#global-fallback-limit-시스템-구현-2025-10-17)
   - [Legacy 모듈 제거](#legacy-limit_learner-제거-2025-10-17)

---

## 📊 디스플레이 값 결정 로직

### 1. Monitor Daemon (monitor_daemon.py:543-565)

**우선순위:**
```
1. CALIBRATION_ENABLED가 True인가?
   └─ YES → calibration 계산 시도
            ├─ calibration['status'] in ['override', 'calibrated', 'learning']인가?
            │  └─ YES → display_percentage = calibrated_percentage ✅
            │  └─ NO  → display_percentage = original_percentage
            └─ 계산 실패 (Exception)
                      → display_percentage = original_percentage
   └─ NO  → display_percentage = original_percentage
```

**현재 코드:**
```python
# Line 545
display_percentage = session_percentages['max_percentage']  # 기본값

if CALIBRATION_ENABLED:
    try:
        calibration = get_calibrated_value(...)

        # 캘리브레이션이 활성화되어 있으면 보정된 값을 사용
        # override, calibrated, learning 모두 적용
        if calibration['status'] in ['override', 'calibrated', 'learning']:
            display_percentage = calibration_info['calibrated_percentage']
    except Exception as e:
        # 실패시 기본값 유지
```

**조정 포인트:**
- [x] **Override 상태 추가** (2025-10-16)
- [ ] 'learning' 상태에서도 캘리브레이션을 적용할 것인가?
- [ ] confidence 임계값을 추가할 것인가? (예: confidence >= 0.5일 때만 적용)
- [ ] sample_count 최소값을 확인할 것인가?

---

### 2. Calibration Learner (calibration_learner.py:388-652)

**우선순위:**
```
1. Override 확인 (최우선)
   └─ latest_override가 있고 만료되지 않았는가?
      ├─ YES + learned_limit > 0
      │  └─ 실시간 토큰으로 percentage 계산 ✅ (override_limit_based)
      ├─ YES + learned_limit 없음
      │  └─ 고정값 사용 (override_fixed)
      └─ NO ↓

2. window_key에 해당하는 모델이 있는가?
   └─ NO → status='no_data', offset=0, 원본 값 반환 ❌
   └─ YES ↓

3. sample_count >= 3 인가?
   └─ NO → Global fallback limit 시도 ⚠️
      ├─ fallback_limit 있음
      │  └─ 실시간 토큰으로 percentage 계산 ✅ (learning_with_fallback)
      └─ fallback_limit 없음
         └─ 원본 값 반환 ❌
   └─ YES ↓

4. model에 limit learning이 있는가? (has_limit_learning)
   ├─ YES → limit 기반 실시간 계산 시도
   │        ├─ 성공 → calibrated_value (limit_based) ✅
   │        └─ 실패 → calibrated_value (offset_fallback) ✅
   └─ NO  → Global fallback limit 시도 ⚠️
      ├─ fallback_limit 있음
      │  └─ 실시간 토큰으로 percentage 계산 ✅ (fallback_limit)
      └─ fallback_limit 없음
         └─ calibrated_value (offset_based) ✅
```

**현재 코드:**
```python
# Line 401-450: Override 확인 (최우선)
if window_key in data and 'latest_override' in data[window_key]:
    override = data[window_key]['latest_override']
    if datetime.now(ZoneInfo('Asia/Seoul')) < expires_at:
        learned_limit = override.get('learned_limit')

        if learned_limit and learned_limit > 0:
            # 실시간 토큰 계산
            output_total = usage_data['session']['usage']['output_tokens']
            calibrated_pct = (output_total / (learned_limit * 300)) * 100
            method = 'override_limit_based'
        else:
            # 고정값 사용
            calibrated_value = override['calibrated_percentage'] / 100
            method = 'override_fixed'

# Line 452-520: 모델 기반 계산
if model.get('has_limit_learning'):
    # Limit 기반 예측 (더 정확함)
    try:
        calibrated_value = ...  # limit 기반
        method = 'limit_based'
    except:
        calibrated_value = monitor_value + model['offset_mean']
        method = 'offset_fallback'
else:
    # Offset 기반 예측 (초기 학습)
    calibrated_value = monitor_value + model['offset_mean']
    method = 'offset_based'
```

**조정 포인트:**
- [x] **Override 실시간 계산 구현** (2025-10-16)
- [ ] sample_count 최소값 (현재: 3) → 조정 가능
- [ ] confidence 임계값 추가? (예: confidence >= 0.6)
- [ ] learning 상태에서도 적용? (현재: YES)
- [ ] limit_based 실패시 fallback 로직

---

### 3. SwiftBar Plugin (ClaudeUsage.1m.sh:47-61)

**우선순위:**
```
1. CALIBRATION_ENABLED == "true"인가?
   └─ NO → SESSION_PCT = original ❌
   └─ YES ↓

2. calibration.info.calibrated_percentage가 null이 아닌가?
   └─ NO → SESSION_PCT = original ❌
   └─ YES → SESSION_PCT = calibrated ✅
```

**현재 코드:**
```bash
# Line 48
CALIBRATION_ENABLED=$(jq -r '.calibration.enabled // false' "$USAGE_FILE")
if [[ "$CALIBRATION_ENABLED" == "true" ]]; then
    CALIBRATED_PCT=$(jq -r '.calibration.info.calibrated_percentage // null' "$USAGE_FILE")
    if [[ "$CALIBRATED_PCT" != "null" ]]; then
        SESSION_PCT="$CALIBRATED_PCT"
    else
        SESSION_PCT=$(jq -r '.session.percentages.max_percentage // 0' "$USAGE_FILE")
    fi
else
    SESSION_PCT=$(jq -r '.session.percentages.max_percentage // 0' "$USAGE_FILE")
fi
```

**조정 포인트:**
- [ ] calibration status도 확인할 것인가? (현재: NO)
- [ ] confidence도 확인할 것인가? (현재: NO)

---

## 🎯 캘리브레이션 모델 학습 조건

### Model Update (calibration_learner.py:251-385)

**우선순위:**
```
1. history가 있는가?
   └─ NO → status='no_data', 빈 모델 반환 ❌
   └─ YES ↓

2. len(history) >= 3 인가?
   └─ NO → status='insufficient_data', offset=0 모델 반환 ⚠️
   └─ YES ↓

3. 샘플 수에 따라 recent_history 선택:
   ├─ <= 10개 → 최근 5개 사용
   ├─ <= 30개 → 최근 20개 사용
   └─ > 30개  → 최근 50개 사용

4. Limit 학습 (토큰 데이터가 있는 샘플 >= 3개):
   - Input limit: input_tokens + cache_creation_tokens 기준 역산
   - Output limit: output_tokens 기준 역산
   - Exponential weighted average (decay_factor = 0.85)

5. offset_mean 계산 (exponential weighted average)
   - decay_factor = 0.9 (최신일수록 가중치 높음)

6. confidence 계산:
   - sample_confidence = min(sample_count / target_samples, 1.0)
   - stability_confidence = max(0.0, 1.0 - offset_std * 10)
   - confidence = (sample_confidence + stability_confidence) / 2.0

7. status 결정:
   ├─ confidence < 0.7 → status='learning'
   └─ confidence >= 0.7 → status='learned'
```

**Limit 역산 공식:**
```
limit_tpm = current_tokens / (actual_percentage / 100) / window_minutes

예시:
- Output tokens: 41,552
- Actual percentage: 9%
- Window: 300분 (5시간)
→ learned_output_limit = 41,552 / 0.09 / 300 = 1,539 TPM
```

**조정 포인트:**
- [x] **Limit 학습 및 실시간 계산** (2025-10-16)
- [ ] 최소 샘플 수: 3개 → ?개
- [ ] decay_factor: 0.9 → ?
- [ ] confidence 임계값: 0.7 → ?
- [ ] recent_history 샘플 수 조정

---

## 🔄 Global Fallback Limit 시스템

**최종 업데이트**: 2025-10-17

### 작동 원리

새 세션 또는 데이터 부족(샘플 < 3개) 시, 다른 세션의 learned limit을 가중 평균하여 fallback limit으로 사용합니다.

**핵심 개념**:
- 모든 세션은 동일한 API limit 공유 (예: Output 1,611 TPM)
- 세션 시간대는 다르지만 limit은 동일
- 다른 세션의 학습 데이터를 초기 기준으로 활용
- 각 세션은 독립적으로 계속 학습

### Fallback 우선순위

```python
# calibration_learner.py:566-604
if model['sample_count'] < 3:
    # 1. Global fallback limit 시도
    fallback_limit = get_global_fallback_limit()

    if fallback_limit and fallback_limit > 0 and window_key != "weekly":
        # Fallback limit으로 실시간 계산
        output_total = usage_data['session']['usage']['output_tokens']
        calibrated_pct = (output_total / (fallback_limit * 300)) * 100

        return {
            'status': 'learning_with_fallback',
            'method': 'fallback_limit',
            'fallback_limit': fallback_limit,
            'confidence': 0.5  # 중간 신뢰도
        }
    else:
        # Fallback 실패 시 원본값 사용
        return {
            'status': 'insufficient_data',
            'calibrated_value': monitor_value
        }
```

### 가중 평균 계산

```python
# calibration_learner.py:205-243
def get_global_fallback_limit() -> Optional[int]:
    """
    모든 세션의 learned_output_limit을 가중 평균하여 fallback limit 계산
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
```

### 실제 예시

**상황**: 새로운 세션 09:00-14:00 (샘플 2개)

**다른 세션 데이터**:
- 14:00-19:00: 29 샘플, learned_limit = 1,293 TPM
- 05:00-10:00: 1 샘플 (무시, < 3개)

**Fallback 계산**:
```python
# 14:00-19:00 세션만 사용 (3개 이상)
limits = [1293]
weights = [min(29 / 10.0, 1.0)] = [1.0]  # 최대 가중치

fallback_limit = 1293 * 1.0 / 1.0 = 1,293 TPM
```

**09:00-14:00 세션 퍼센트 계산**:
```python
# Output tokens: 6,408
# Fallback limit: 1,293 TPM
# Window: 300분 (5시간)

percentage = (6408 / (1293 * 300)) * 100 = 1.7%

# Status: 'learning_with_fallback'
# Confidence: 0.5
```

### Fallback 적용 조건

**적용됨**:
1. 세션 샘플 < 3개
2. 세션에 limit learning 없음 (has_limit_learning = False)
3. Weekly 윈도우 제외 (세션만)

**적용 안됨**:
1. Override 활성화 (최우선)
2. 샘플 >= 3개 + limit learning 있음
3. Weekly 윈도우

### 상태 (Status)

**`learning_with_fallback`**:
- 샘플 < 3개이지만 fallback limit으로 계산
- Confidence: 0.5 (중간 신뢰도)
- Method: `fallback_limit`
- 각 세션은 계속 독립적으로 학습
- 샘플 3개 이상 시 자체 learned_limit 사용

---

## 🔧 권장 조정 시나리오

### 시나리오 1: 빠른 학습, 낮은 정확도
```
calibration_learner.py:
  - sample_count 최소값: 3 → 2
  - confidence 임계값: 0.7 → 0.5

monitor_daemon.py:
  - 'learning' 상태에서도 적용: YES (현재 설정 유지)
  - confidence 확인 없음 (현재 설정 유지)
```

### 시나리오 2: 느린 학습, 높은 정확도
```
calibration_learner.py:
  - sample_count 최소값: 3 → 5
  - confidence 임계값: 0.7 → 0.8

monitor_daemon.py:
  - 'learning' 상태 제외: ['override', 'calibrated'] 만 적용
  - 또는 confidence >= 0.7 조건 추가
```

### 시나리오 3: 균형잡힌 설정 (현재 권장)
```
calibration_learner.py:
  - sample_count 최소값: 3 (현재 설정)
  - confidence 임계값: 0.7 (현재 설정)
  - Override 실시간 계산: YES ✅ (2025-10-16)

monitor_daemon.py:
  - 'learning' 상태에서도 적용: YES
  - 'override' 상태 최우선 적용: YES ✅ (2025-10-16)
  - confidence 확인: NO (신뢰도 낮아도 적용)
```

---

## 📝 수정이 필요한 경우

### 1. 최소 샘플 수 변경

**파일:** `src/calibration_learner.py`

```python
# Line 278: insufficient_data 조건
if len(history) < 3:  # ← 이 숫자 변경

# Line 440: calibrated_value 반환 조건
if model['sample_count'] < 3:  # ← 이 숫자 변경
```

### 2. Confidence 임계값 추가

**파일:** `src/monitor_daemon.py`

```python
# Line 565: 기존
if calibration['status'] in ['override', 'calibrated', 'learning']:
    display_percentage = calibration_info['calibrated_percentage']

# 수정안 1: status만 제한
if calibration['status'] in ['override', 'calibrated']:  # learning 제외
    display_percentage = calibration_info['calibrated_percentage']

# 수정안 2: confidence 추가 (override는 제외)
if calibration['status'] == 'override':
    display_percentage = calibration_info['calibrated_percentage']
elif calibration['status'] in ['calibrated', 'learning'] and calibration['confidence'] >= 0.6:
    display_percentage = calibration_info['calibrated_percentage']
```

### 3. SwiftBar에서 status/confidence 확인

**파일:** `plugins/ClaudeUsage.1m.sh`

```bash
# Line 49 이후 추가:
if [[ "$CALIBRATION_ENABLED" == "true" ]]; then
    CALIBRATED_PCT=$(jq -r '.calibration.info.calibrated_percentage // null' "$USAGE_FILE")
    CALIBRATION_STATUS=$(jq -r '.calibration.info.status // "no_data"' "$USAGE_FILE")
    CONFIDENCE=$(jq -r '.calibration.info.confidence // 0' "$USAGE_FILE")

    # 조건 추가 (override는 항상 적용)
    if [[ "$CALIBRATED_PCT" != "null" ]] && \
       ([[ "$CALIBRATION_STATUS" == "override" ]] || [[ "$CALIBRATION_STATUS" == "calibrated" ]]); then
        SESSION_PCT="$CALIBRATED_PCT"
    else
        SESSION_PCT=$(jq -r '.session.percentages.max_percentage // 0' "$USAGE_FILE")
    fi
fi
```

---

## 🧪 테스트 체크리스트

변경 후 다음을 확인하세요:

- [ ] `python3 src/calibration_learner.py --status` - 캘리브레이션 상태 확인
- [ ] `python3 src/monitor_daemon.py --once` - 모니터 한 번 실행
- [ ] JSON 출력에서 `calibration.info` 확인
- [ ] SwiftBar 메뉴바에서 표시값 확인
- [ ] 새로운 캘리브레이션 데이터 추가 후 재확인
- [x] **Override 실시간 계산 테스트** (2025-10-16)
  - [x] `claude-calibrate 9` 입력
  - [x] 토큰 증가 시 % 증가 확인

---

## 현재 설정 요약

| 항목 | 현재 값 | 위치 | 조정 가능? | 비고 |
|------|---------|------|-----------|------|
| 최소 샘플 수 | 3 | calibration_learner.py:278,440 | ✅ | |
| Confidence 임계값 (학습) | 0.7 | calibration_learner.py:374 | ✅ | |
| Display 적용 status | 'override', 'calibrated', 'learning' | monitor_daemon.py:565 | ✅ | Override 추가 (2025-10-16) |
| Display confidence 확인 | NO | monitor_daemon.py:565 | ✅ 추가 가능 | Override는 제외 |
| SwiftBar status 확인 | NO | ClaudeUsage.1m.sh:49 | ✅ 추가 가능 | |
| Decay factor (offset) | 0.9 | calibration_learner.py:348 | ✅ | |
| Decay factor (limit) | 0.85 | calibration_learner.py:336 | ✅ | |
| Recent samples (초기) | 5 | calibration_learner.py:298 | ✅ | |
| **Override 실시간 계산** | **YES** | calibration_learner.py:410-425 | ✅ | **신규 (2025-10-16)** |
| **Override limit 저장** | **Output only** | calibration_learner.py:719-723 | ✅ | **개선 (2025-10-16)** |
| **Global Fallback Limit** | **YES** | calibration_learner.py:205-243, 566-604 | ✅ | **신규 (2025-10-17)** |
| **Fallback 최소 샘플** | **3** | calibration_learner.py:220 | ✅ | **세션 데이터 3개 이상만 사용** |

---

## 🆕 최근 개선사항 (2025-10-16 ~ 2025-10-17)

### Override 실시간 계산 구현 (2025-10-16)

### 문제 상황

**사용자 요청:**
```
현재 모니터 7% → claude-calibrate 10 입력
→ 모니터 10% 노출 (즉시 반영 ✅)
→ 1분 후 원래 값 7%로 복원 ❌
```

**원인 분석:**
1. Override가 **고정값**을 저장하고 반환
2. 토큰이 계속 증가해도 10%로 고정
3. 학습된 limit이 있지만 사용하지 않음

**추가 문제:**
- `max(input_limit, output_limit)` 저장 → Input limit (큰 값) 저장
- Output limit으로 계산 시 과도하게 낮은 % 표시
- 예: Output 41,552 tokens, Limit 23,857 TPM → **0.6%** (잘못됨)

---

### 해결 방법

#### 1. Override 실시간 계산 구현

**파일:** `src/calibration_learner.py:401-450`

**Before (고정값 반환):**
```python
if window_key in data and 'latest_override' in data[window_key]:
    override = data[window_key]['latest_override']
    if datetime.now(ZoneInfo('Asia/Seoul')) < expires_at:
        # ❌ 고정값만 반환
        return {
            'calibrated_value': override['calibrated_percentage'] / 100,
            'status': 'override',
            'method': 'manual_override'
        }
```

**After (실시간 계산):**
```python
if window_key in data and 'latest_override' in data[window_key]:
    override = data[window_key]['latest_override']
    if datetime.now(ZoneInfo('Asia/Seoul')) < expires_at:
        learned_limit = override.get('learned_limit')

        if learned_limit and learned_limit > 0:
            # ✅ 실시간 토큰으로 percentage 계산
            output_file = Path.home() / '.claude_usage.json'
            with open(output_file, 'r') as f:
                usage_data = json.load(f)

            output_total = usage_data['session']['usage']['output_tokens']
            calibrated_pct = (output_total / (learned_limit * 300)) * 100
            calibrated_value = calibrated_pct / 100.0
            method = 'override_limit_based'
        else:
            # Learned limit 없으면 고정값 사용
            calibrated_value = override['calibrated_percentage'] / 100
            method = 'override_fixed'

        return {
            'calibrated_value': calibrated_value,
            'status': 'override',
            'method': method,
            'learned_limit': learned_limit
        }
```

---

#### 2. Output Limit 전용 사용

**파일:** `src/calibration_learner.py:717-724`

**Before (max 사용):**
```python
# Input과 Output 중 큰 값 저장
max_limit = max(learned_input_limit or 0, learned_output_limit or 0)
set_calibration_override(
    window_key,
    session_actual,
    max_limit,  # ❌ Input limit (큰 값) 저장됨
    window_end.isoformat()
)
```

**After (Output만 사용):**
```python
# Output limit만 저장 (실제 계산에 사용하는 값)
set_calibration_override(
    window_key,
    session_actual,
    learned_output_limit or 0,  # ✅ Output limit만 저장
    window_end.isoformat()
)
```

---

### 개선 효과

**Before:**
```
1. claude-calibrate 10 입력
   → Override: calibrated_percentage = 10% (고정)
   → learned_limit = 23,857 (input limit)

2. 모니터 실행 (1분 후)
   → Override 반환: 10% (고정값)
   ❌ 토큰 증가해도 10%로 고정

3. 또는 learned_limit으로 계산 시:
   → 41,552 / (23,857 * 300) = 0.6%
   ❌ 과도하게 낮음 (Input limit 사용)
```

**After:**
```
1. claude-calibrate 10 입력
   → Override: calibrated_percentage = 10%
   → learned_limit = 1,539 (output limit)
   → History 기록 (학습용)

2. 모니터 실행 (즉시)
   → Output: 41,552 tokens
   → 10.0% = 41,552 / (1,539 * 300) * 100
   ✅ 실시간 계산

3. 모니터 실행 (1분 후)
   → Output: 45,000 tokens (증가)
   → 10.8% = 45,000 / (1,539 * 300) * 100
   ✅ 토큰 증가에 따라 % 증가

4. 세션 끝 (19:00)
   → Override 만료
   → 모델의 learned_output_limit 사용
   ✅ 학습된 데이터로 계속 정확한 계산
```

---

### 데이터 구조 변경

**calibration_data.json:**
```json
{
  "14:00-19:00": {
    "latest_override": {
      "timestamp": "2025-10-16T14:45:00+09:00",
      "calibrated_percentage": 10.0,
      "expires_at": "2025-10-16T19:00:00+09:00",
      "learned_limit": 1539  // ✅ Output limit만 저장 (이전: 23857)
    },
    "history": [
      {
        "timestamp": "2025-10-16T14:45:00+09:00",
        "monitor_value": 0.093,
        "actual_value": 0.10,
        "offset": 0.007,
        "token_data": {
          "input_tokens": 1686,
          "output_tokens": 41552,
          "cache_creation_tokens": 730580,
          "total_counted_tokens": 773818
        }
      }
    ],
    "model": {
      "learned_input_limit": 24397,  // 참고용
      "learned_output_limit": 1539,  // ✅ 실제 사용
      "has_limit_learning": true,
      "status": "learned"
    }
  }
}
```

---

### 사용 방법

#### 기본 사용
```bash
# 1. Claude usage UI에서 정확한 % 확인
/usage
# Output: Session Output: 10%

# 2. 캘리브레이션 (즉시 반영 + Limit 학습)
claude-calibrate 10

# 출력:
# ✅ 즉시 반영: 10.0% → SwiftBar에 표시됨
#
# 📊 Calibration for 14:00-19:00:
#    Monitor: 9.3%
#    Actual:  10.0%
#    Offset:  +0.7%
#
# 🎯 학습된 Limit:
#    Input:  24,397 TPM
#    Output: 1,539 TPM
#
# ⏰ Override:
#    만료 시간: 19:00 (2025-10-16)
#    상태: 세션 끝날 때까지 실시간 계산 적용
```

#### 동작 확인
```bash
# 모니터 실행 (실시간 계산)
python3 src/monitor_daemon.py --once | jq '.calibration.info'

# 출력:
# {
#   "original_percentage": 9.5,
#   "calibrated_percentage": 10.2,  // ✅ 토큰 증가에 따라 증가
#   "status": "override",
#   "method": "override_limit_based",  // ✅ Limit 기반 실시간 계산
#   "learned_limit": 1539
# }
```

#### 세션 종료 후
```bash
# 19:00 이후 자동으로 Override 만료
# 모델의 learned_output_limit 사용하여 계속 정확한 계산 유지
```

---

### 주의사항

1. **Override 만료**
   - Override는 현재 세션 종료 시각까지만 유효
   - 다음 세션(19:00-00:00)에서는 모델 기반 계산 사용
   - 필요 시 새 세션에서 재조정

2. **Limit 역산 정확도**
   - 실제 사용량이 낮을 때(< 5%) 역산된 limit의 오차 증가
   - 가능한 10% 이상에서 캘리브레이션 권장
   - 여러 번 입력하여 exponential weighted average로 정확도 향상

3. **Input vs Output Limit**
   - Input limit: input_tokens + cache_creation_tokens 기준
   - Output limit: output_tokens 기준 (실제 디스플레이에 사용)
   - 두 값 모두 학습하지만 Override는 **Output limit만 사용**

4. **Method 확인**
   - `override_limit_based`: 실시간 계산 ✅
   - `override_fixed`: 고정값 사용 (learned_limit 없을 때)
   - `limit_based`: 모델의 learned_limit 사용
   - `offset_based`: Offset 보정 (초기 학습)

---

### 테스트 결과

**테스트 1: 실시간 계산 확인**
```bash
# Before calibration
cat ~/.claude_usage.json | jq '.calibration.info.calibrated_percentage'
# → 7.2

# Calibrate
claude-calibrate 9
# → ✅ 즉시 반영: 9.0%

# Immediately after
cat ~/.claude_usage.json | jq '.calibration.info'
# → calibrated_percentage: 9.0
# → method: "override_limit_based" ✅

# 1 minute later (after more tokens)
~/.local/bin/claude-usage-monitor --once
cat ~/.claude_usage.json | jq '.calibration.info.calibrated_percentage'
# → 9.2 ✅ (증가함)
```

**테스트 2: Limit 저장 확인**
```bash
# Check learned limit
cat ~/.claude-monitor/calibration_data.json | jq '.["14:00-19:00"].latest_override.learned_limit'
# → 1712 ✅ (Output limit, 이전: 23857)

# Verify calculation
# Output: 41,552 tokens
# 41,552 / (1712 * 300) * 100 = 8.1% ✅ (정상)
```

---

### Global Fallback Limit 시스템 구현 (2025-10-17)

**문제 상황:**
```
새로운 세션 09:00-14:00 시작
→ 샘플 0개 (또는 < 3개)
→ Learned limit 없음
→ Config limit 사용 (부정확)
→ 실제 35%인데 28% 표시 ❌
```

**원인 분석:**
- 각 세션 윈도우가 완전히 독립적으로 운영
- 모든 세션은 동일한 API limit 사용 (예: Output 1,611 TPM)
- 14:00-19:00 세션: 29 샘플, learned_limit = 1,293 TPM (정확)
- 09:00-14:00 세션: 2 샘플, learned_limit 없음 (부정확)
- 다른 세션의 학습 데이터를 활용하지 못함

**해결 방법:**

#### 1. Global Fallback Limit 함수 추가

**파일**: `src/calibration_learner.py:205-243`

```python
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
            # 샘플 수에 비례한 가중치
            weight = min(sample_count / 10.0, 1.0)  # 최대 1.0
            weights.append(weight)

    if not limits:
        return None

    # 가중 평균 계산
    total_weight = sum(weights)
    weighted_avg = sum(l * w for l, w in zip(limits, weights)) / total_weight

    return round(weighted_avg)
```

#### 2. Fallback Logic 추가 (샘플 < 3개)

**파일**: `src/calibration_learner.py:566-604`

```python
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
```

#### 3. Fallback Logic 추가 (Limit Learning 없음)

**파일**: `src/calibration_learner.py:630-652`

```python
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
```

**개선 효과:**

```
Before (새 세션):
→ Config limit 사용 (1,611 TPM)
→ 실제 35%인데 28% 표시 ❌

After (Global fallback):
→ 14:00-19:00 세션의 learned_limit 활용 (1,293 TPM)
→ 실제 35%, 모니터 34.8% 표시 ✅
→ Status: 'learning_with_fallback'
→ Confidence: 0.5

After (3개 샘플 수집):
→ 자체 learned_limit 사용
→ Status: 'learning' → 'learned'
→ Confidence: 0.7+
```

---

### Legacy limit_learner 제거 (2025-10-17)

**문제 상황:**
```
⚠️ Limit learning module not found. Using static limits.
```

모니터 실행 시마다 warning 메시지 표시. 실제로는 calibration_learner.py를 사용 중이므로 불필요한 메시지.

**해결 방법:**

**파일**: `src/monitor_daemon.py`

**Removed**:
```python
# Lines 15-21 삭제
try:
    from limit_learner import record_session_snapshot, analyze_and_learn_limits, get_effective_limits
    LIMIT_LEARNING_ENABLED = True
except ImportError:
    LIMIT_LEARNING_ENABLED = False
    print("⚠️  Limit learning module not found. Using static limits.")
```

**Simplified**:
```python
# Lines 496-506: Config에서 직접 로드
session_limits = config['rate_limits']['session']
weekly_limits = config['rate_limits']['weekly']
```

**Removed** (Lines 515-543):
- record_session_snapshot() 호출
- analyze_and_learn_limits() 호출
- LIMIT_LEARNING_ENABLED 조건문
- limit_learning JSON 출력

**개선 효과:**
```
Before:
⚠️ Limit learning module not found. Using static limits.
{
  "status": "active",
  "limit_learning": {...},
  ...
}

After:
{
  "status": "active",
  ...
}
✅ 깔끔한 출력, warning 없음
```

---

**개선 완료일**:
- Override 실시간 계산: 2025-10-16
- Global Fallback Limit: 2025-10-17
- Legacy 모듈 제거: 2025-10-17
- **v2.1 안정성 강화: 2025-10-22** 🆕

**관련 파일**:
- `src/calibration_learner.py:205-243` (Global fallback 함수)
- `src/calibration_learner.py:401-450` (Override 실시간 계산)
- `src/calibration_learner.py:566-652` (Fallback logic)
- `src/monitor_daemon.py` (Legacy 코드 제거)
- `~/.local/bin/claude-usage-monitor` (배포)
- `~/.local/bin/calibration_learner.py` (배포)

---

## 🆕 v2.1 안정성 강화 (2025-10-22)

### 문제 상황

**반복되는 오류들:**
1. 여러 daemon 프로세스가 동시 실행되어 파일 충돌
2. 과거 윈도우의 override가 새 윈도우에 영향
3. `claude-calibrate` 실행 시 오래된 데이터 사용
4. 너무 작거나 큰 learned_limit으로 이상한 값 계산
5. SwiftBar에서 calibration 상태 파악 어려움

### 해결 방법

#### 1. PID 파일 기반 중복 실행 방지

**파일**: `src/monitor_daemon.py`

**추가된 함수:**
```python
def check_pid():
    """PID 파일 확인 및 중복 실행 방지"""
    if PID_FILE.exists():
        try:
            with open(PID_FILE, 'r') as f:
                old_pid = int(f.read().strip())

            # 해당 PID가 실행 중인지 확인
            try:
                os.kill(old_pid, 0)  # 시그널 0: 프로세스 존재 확인
                print(f"⚠️  Daemon already running with PID {old_pid}")
                return False
            except OSError:
                # 프로세스가 없으면 오래된 PID 파일 삭제
                PID_FILE.unlink()
        except (ValueError, IOError):
            PID_FILE.unlink()

    return True

def write_pid():
    """현재 프로세스 PID 기록"""
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))

def cleanup_pid():
    """PID 파일 삭제"""
    if PID_FILE.exists():
        PID_FILE.unlink()
```

**개선 효과:**
- 중복 실행 자동 감지 및 방지
- 오래된 PID 파일 자동 정리
- `--force` 옵션으로 강제 시작 가능

---

#### 2. 윈도우 검증 시스템

**파일**: `src/calibration_learner.py:497-524`

**Before (시간만 체크):**
```python
if datetime.now(ZoneInfo('Asia/Seoul')) < expires_at:
    # Override 적용
```

**After (윈도우 + 시간 체크):**
```python
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
    # ... override 로직
```

**개선 효과:**
- 과거 윈도우 override 자동 만료
- 윈도우 불일치 오류 방지
- 현재 윈도우만 정확하게 적용

---

#### 3. Pre-Calibration 업데이트

**파일**: `~/.local/bin/claude-calibrate`

**Before:**
```bash
# Run calibration
python3 ~/.local/bin/calibration_learner.py "$@"
```

**After:**
```bash
# Force monitor update BEFORE calibration to get latest window data
if [ -n "$1" ] && [[ ! "$1" =~ ^-- ]]; then
    ~/.local/bin/claude-usage-monitor --once > /dev/null 2>&1
fi

# Run calibration
python3 ~/.local/bin/calibration_learner.py "$@"
```

**개선 효과:**
- 최신 윈도우 데이터로 calibration
- 오래된 데이터 사용 방지
- 정확한 learned_limit 계산

---

#### 4. Learned Limit 범위 검증

**파일**: `src/calibration_learner.py`

**Constants 추가:**
```python
MIN_LEARNED_LIMIT = 100  # TPM 최소값
MAX_LEARNED_LIMIT = 20000  # TPM 최대값
```

**검증 로직 추가:**
```python
def reverse_calculate_limit(...):
    limit_rounded = round(limit_per_minute)

    # 범위 검증
    if limit_rounded < MIN_LEARNED_LIMIT:
        print(f"⚠️  Warning: Calculated limit ({limit_rounded} TPM) too low")
        return MIN_LEARNED_LIMIT
    elif limit_rounded > MAX_LEARNED_LIMIT:
        print(f"⚠️  Warning: Calculated limit ({limit_rounded} TPM) too high")
        return MAX_LEARNED_LIMIT

    return limit_rounded

# Override 적용 시에도 검증
if learned_limit and learned_limit > 0:
    if learned_limit < MIN_LEARNED_LIMIT or learned_limit > MAX_LEARNED_LIMIT:
        # 범위 벗어나면 fallback로 처리
        learned_limit = None
```

**개선 효과:**
- 극단적인 learned_limit 값 방지
- 자동 조정 및 경고
- 안정적인 퍼센트 계산

---

#### 5. SwiftBar UI 개선

**파일**: `plugins/ClaudeUsage.1m.sh`

**Before (기본 표시):**
```bash
echo "📚 Calibration"
if [[ "$CALIB_STATUS" == "override" ]]; then
    echo "--Status: ⭐ Override (${CALIB_ADJUSTED}%)"
    echo "--Original: ${CALIB_ORIGINAL}%"
else
    echo "--Status: ⚠️ No calibration"
fi
```

**After (상세 표시):**
```bash
echo "📚 Calibration Status"
CALIB_WINDOW=$(jq -r '.calibration.session.window_key // "unknown"' "$USAGE_FILE")
CALIB_LIMIT=$(jq -r '.calibration.session.learned_limit // 0' "$USAGE_FILE")

if [[ "$CALIB_STATUS" == "override" ]]; then
    echo "--Session: ⭐ Override (${CALIB_ADJUSTED}%)"
    echo "--  Window: ${CALIB_WINDOW}"
    if [[ "$CALIB_LIMIT" != "0" ]] && [[ "$CALIB_LIMIT" != "null" ]]; then
        echo "--  Learned limit: ${CALIB_LIMIT} TPM"
    fi
    echo "--  Original: ${CALIB_ORIGINAL}%"
elif [[ "$CALIB_STATUS" == "calibrated" ]]; then
    echo "--Session: ✅ Calibrated (${CALIB_ADJUSTED}%)"
    echo "--  Window: ${CALIB_WINDOW}"
elif [[ "$CALIB_STATUS" == "learning" ]]; then
    echo "--Session: 📚 Learning (${CALIB_ADJUSTED}%)"
    echo "--  Window: ${CALIB_WINDOW}"
else
    echo "--Session: ⚠️ No calibration"
fi

# Weekly calibration status
WEEKLY_STATUS=$(jq -r '.calibration.weekly.status // "no_data"' "$USAGE_FILE")
WEEKLY_ADJUSTED=$(jq -r '.calibration.weekly.calibrated_percentage // 0' "$USAGE_FILE")
if [[ "$WEEKLY_STATUS" == "override" ]]; then
    echo "--Weekly: ⭐ Override (${WEEKLY_ADJUSTED}%)"
fi
```

**Monitor Daemon 출력 포함:**
```python
session_calibration_info = {
    'original_percentage': session_percentages['max_percentage'],
    'calibrated_percentage': round(calibration['calibrated_value'] * 100, 1),
    'offset_applied': round(calibration['offset_applied'] * 100, 1),
    'confidence': calibration['confidence'],
    'status': calibration['status'],
    'dynamic_threshold': round(calibration['threshold'] * 100, 1),
    'window_key': window_key,
    'learned_limit': calibration.get('learned_limit')  # 추가
}
```

**개선 효과:**
- 현재 윈도우 표시로 디버깅 용이
- Learned limit TPM 값 확인 가능
- 세션/주간 상태 분리 표시
- 원본/Calibrated 비교 가능

---

### 테스트 체크리스트

- [x] PID 파일 생성 확인
- [x] 중복 실행 시 경고 표시
- [x] 윈도우 변경 시 override 자동 삭제
- [x] Calibration 전 monitor 자동 업데이트
- [x] Learned limit 범위 검증 (100~20,000 TPM)
- [x] SwiftBar에 상세 정보 표시

### 개선 완료일

- **2025-10-22**: v2.1 안정성 강화 릴리스

### 관련 파일

- `src/monitor_daemon.py`: PID 파일 시스템
- `src/calibration_learner.py`: 윈도우 검증, limit 검증
- `~/.local/bin/claude-calibrate`: Pre-calibration 업데이트
- `plugins/ClaudeUsage.1m.sh`: UI 개선
- `CHANGELOG.md`: 버전별 변경사항
