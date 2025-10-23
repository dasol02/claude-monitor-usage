# 퍼센트 계산 로직 정리

## 1️⃣ 원본 퍼센트 계산 (monitor_daemon.py)

### 📍 위치: `monitor_daemon.py:275-304`

```python
def calculate_usage_percentage(usage, limits):
    """사용량 퍼센트 계산"""

    window_minutes = limits['window_hours'] * 60  # 5시간 = 300분

    # === INPUT 퍼센트 ===
    total_input_limit = limits['input_tokens_per_minute'] * window_minutes
    # 예: 40,000 TPM * 300분 = 12,000,000 tokens

    input_total = usage['input_tokens'] + usage['cache_creation_tokens']
    input_pct = (input_total / total_input_limit) * 100
    # 예: 3,200,000 / 12,000,000 * 100 = 26.7%


    # === OUTPUT 퍼센트 ===
    total_output_limit = limits['output_tokens_per_minute'] * window_minutes
    # 예: 1,611 TPM * 300분 = 483,300 tokens

    output_pct = (usage['output_tokens'] / total_output_limit) * 100
    # 예: 103,000 / 483,300 * 100 = 21.3%


    # === 최종 퍼센트 ===
    max_pct = max(input_pct, output_pct)
    # 예: max(26.7%, 21.3%) = 26.7%

    return {
        'input_percentage': 26.7,
        'output_percentage': 21.3,
        'max_percentage': 26.7   # ← 이 값이 원본 퍼센트
    }
```

**결과: 26.7% (원본)**

---

## 2️⃣ 캘리브레이션된 퍼센트 계산

### 방법 A: Offset 기반 (초기 학습)

📍 위치: `calibration_learner.py:373-375`

```python
# 모니터 값 + 학습된 offset
calibrated_value = monitor_value + model['offset_mean']

# 예시:
# - monitor_value = 0.267 (26.7%)
# - offset_mean = 0.097 (9.7%)
# → calibrated_value = 0.364 (36.4%)
```

**결과: 36.4% (캘리브레이션)**

---

### 방법 B: Limit 기반 (충분한 학습 후)

📍 위치: `calibration_learner.py:351-366`

```python
# 1. 학습된 limit으로 실제 퍼센트 계산
input_pct = (input_total / (learned_input_limit * 300)) * 100
output_pct = (output_total / (learned_output_limit * 300)) * 100
calibrated_value = max(input_pct, output_pct) / 100.0

# 예시:
# - output_tokens = 103,000
# - learned_output_limit = 940 TPM (학습된 실제 limit)
# → output_pct = (103,000 / (940 * 300)) * 100 = 36.5%
```

**결과: 36.5% (캘리브레이션)**

---

## 3️⃣ 최종 표시 값 결정

### 📍 위치: `monitor_daemon.py:545-565`

```python
# 기본값은 원본
display_percentage = 26.7  # 원본 퍼센트

# 캘리브레이션이 활성화되어 있고
if CALIBRATION_ENABLED:
    # 샘플이 3개 이상이면
    if calibration['status'] in ['calibrated', 'learning']:
        # 캘리브레이션된 값 사용
        display_percentage = 36.5  # 캘리브레이션된 퍼센트
```

**최종 결과:**
- ❌ 캘리브레이션 없음 → **26.7%** 표시
- ✅ 캘리브레이션 있음 → **36.5%** 표시

---

## 4️⃣ 전체 플로우

```
┌─────────────────────────────────────┐
│  1. 토큰 사용량 집계                │
│     - input: 6,000                  │
│     - output: 103,000               │
│     - cache_creation: 3,200,000     │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  2. 원본 퍼센트 계산                │
│     input_pct = 26.7%               │
│     output_pct = 21.3%              │
│     max_pct = 26.7%  ← 원본         │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  3. 캘리브레이션 확인                │
│     샘플 3개 이상?                   │
│     YES → offset 적용               │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  4. 캘리브레이션된 퍼센트           │
│     26.7% + 9.7% = 36.4%            │
│     또는                             │
│     limit 기반 = 36.5%              │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  5. 최종 표시                        │
│     🟢 36.5%                         │
└─────────────────────────────────────┘
```

---

## 📊 실제 예시

### 현재 상태:
```json
{
  "session": {
    "usage": {
      "output_tokens": 103279
    },
    "percentages": {
      "max_percentage": 26.2    // ← 원본 (config의 limit 기준)
    }
  },
  "calibration": {
    "info": {
      "original_percentage": 26.2,
      "calibrated_percentage": 36.5,   // ← 캘리브레이션 (실제 limit 기준)
      "offset_applied": 9.7,
      "confidence": 0.63
    }
  }
}
```

### 왜 차이가 나는가?

**원본 계산 (26.2%):**
- Config에 설정된 limit 사용: `1,611 TPM`
- 103,279 / (1,611 * 300) = **21.4%** (output)
- Cache 포함 input이 더 높아서 **26.2%**

**캘리브레이션 (36.5%):**
- 실제 학습된 limit 사용: `940 TPM` ← 실제는 이게 맞음
- 103,279 / (940 * 300) = **36.6%** (output)

→ Config의 1,611 TPM이 **잘못된 값**이고, 실제는 940 TPM이라서 차이가 남!

---

## ✅ 요약

| 항목 | 값 | 설명 |
|------|-----|------|
| Config limit | 1,611 TPM | 설정 파일의 값 (부정확) |
| 원본 퍼센트 | 26.2% | Config limit 기준 계산 |
| **실제 limit** | **940 TPM** | 학습으로 발견한 실제 값 |
| **캘리브레이션 퍼센트** | **36.5%** | 실제 limit 기준 계산 ✅ |
| 차이 | +10.3% | offset |

**결론: 36.5%가 실제 사용량에 가까운 정확한 값입니다.**
