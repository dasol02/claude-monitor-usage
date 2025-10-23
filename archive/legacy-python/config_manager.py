#!/usr/bin/env python3
"""
Claude Monitor - Configuration Manager
플랜 설정 및 변경 관리
"""

import json
import os
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

# Team Premium 플랜 정의 (Claude Code)
TEAM_PREMIUM_PLAN = {
    "id": "team_premium",
    "name": "Team Premium (Claude Code)",
    "price": 150,
    "currency": "USD",
    "rate_limits": {
        "session": {
            "requests_per_minute": 50,
            "input_tokens_per_minute": 40000,
            "output_tokens_per_minute": 1611,
            "window_hours": 5,
            "note": "5시간 고정 세션 윈도우 (15:00-20:00, 20:00-01:00, etc.)"
        },
        "weekly": {
            "input_tokens_per_minute": 40000,
            "output_tokens_per_minute": 193,
            "window_hours": 168,
            "note": "7일 rolling 윈도우"
        }
    },
    "features": {
        "auto_learning": True,
        "p90_analysis": True,
        "confidence_threshold": 0.7,
        "description": "Automatic limit learning via P90 analysis of usage history"
    }
}

CONFIG_DIR = Path.home() / '.claude-monitor'
CONFIG_FILE = CONFIG_DIR / 'config.json'


def ensure_config_dir():
    """설정 디렉토리 생성"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config():
    """설정 파일 로드"""
    if not CONFIG_FILE.exists():
        return None

    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️  설정 파일 로드 실패: {e}")
        return None


def save_config():
    """Team Premium 설정 저장"""
    ensure_config_dir()

    config = {
        "plan": {
            "id": TEAM_PREMIUM_PLAN["id"],
            "name": TEAM_PREMIUM_PLAN["name"],
            "price": TEAM_PREMIUM_PLAN["price"],
            "currency": TEAM_PREMIUM_PLAN["currency"],
            "note": "This monitor is designed specifically for Team Premium plan"
        },
        "rate_limits": TEAM_PREMIUM_PLAN["rate_limits"],
        "reset_schedule": {
            "type": "fixed_5h",
            "description": "고정된 5시간 세션 윈도우 (15:00-20:00, 20:00-01:00, etc.)"
        },
        "display_settings": {
            "timezone": "Asia/Seoul",
            "timezone_abbr": "KST",
            "time_format": "24h",
            "show_percentage": True,
            "show_reset_time": True,
            "progress_bar_style": "battery"
        },
        "notifications": {
            "enabled": True,
            "thresholds": [80, 90, 95],
            "note": "Notify when session usage exceeds these percentages (once per session)"
        },
        "learning": {
            "enabled": TEAM_PREMIUM_PLAN["features"]["auto_learning"],
            "p90_analysis": TEAM_PREMIUM_PLAN["features"]["p90_analysis"],
            "confidence_threshold": TEAM_PREMIUM_PLAN["features"]["confidence_threshold"],
            "description": TEAM_PREMIUM_PLAN["features"]["description"]
        },
        "metadata": {
            "plan_type": "team_premium",
            "configured_at": datetime.now(ZoneInfo('Asia/Seoul')).isoformat(),
            "last_updated": datetime.now(ZoneInfo('Asia/Seoul')).isoformat()
        }
    }

    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

    return config


def display_current_config(config):
    """현재 설정 표시"""
    print("\n" + "=" * 60)
    print("Claude Usage Monitor")
    print("=" * 60)
    print(f"\n✓ Plan: {config['plan']['name']}")
    print(f"✓ Auto-learning: Enabled")
    print(f"✓ Timezone: {config['display_settings']['timezone_abbr']}")
    print(f"\nLimits will be automatically learned from your usage patterns.")
    print("=" * 60 + "\n")


def setup_config():
    """초기 설정"""
    print("\n🚀 Claude Usage Monitor Setup")
    print("   Team Premium (Claude Code)")

    # 기존 설정 확인
    existing_config = load_config()
    if existing_config:
        print("\n✓ Already configured")
        print(f"  Plan: {existing_config['plan']['name']}")
        print(f"  Timezone: {existing_config['display_settings']['timezone_abbr']}")

        confirm = input("\nReconfigure? (y/N): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print("✅ Using existing configuration")
            return existing_config

    # Team Premium 설정 저장
    print("\n💾 Configuring...")
    config = save_config()

    print("✅ Configuration complete!")
    print(f"\nAuto-learning enabled - limits will be refined as you use Claude.")
    print(f"Configuration saved to: {CONFIG_FILE}\n")

    return config


def main():
    """메인 함수 (CLI 실행용)"""
    setup_config()


if __name__ == '__main__':
    main()
