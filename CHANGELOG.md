# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2025-10-22

### Added
- **PID File Lock System**: Prevents multiple daemon instances from running simultaneously
  - Creates `~/.claude-monitor/daemon.pid` for process tracking
  - Automatic cleanup of stale PID files
  - `--force` flag to override PID check if needed
  - Proper cleanup on daemon exit (Ctrl+C or crash)

- **Window Validation System**: Ensures calibration data matches current session window
  - Automatically expires override data from previous windows
  - Only applies calibration for the current active window
  - Prevents errors from window mismatches

- **Pre-Calibration Update**: Forces monitor update before calibration
  - `claude-calibrate` now updates monitor data before reading
  - Ensures calibration uses latest window information
  - Prevents using stale data

- **Learned Limit Validation**: Validates learned limit ranges
  - Minimum limit: 100 TPM
  - Maximum limit: 20,000 TPM
  - Automatic adjustment with warning when out of range
  - Validation during both calibration and override application

- **Enhanced SwiftBar Display**: Improved calibration status information
  - Shows current session window (e.g., "14:00-19:00")
  - Displays learned limit in TPM
  - Shows both original and calibrated percentages
  - Separate status for session and weekly calibration

### Changed
- Monitor daemon now includes `learned_limit` in output JSON
- SwiftBar plugin now reads from `.calibration.session` instead of `.calibration.info`
- Calibration output/input percentages now scaled proportionally to max percentage

### Fixed
- Multiple daemon processes no longer run simultaneously
- Override data from wrong windows no longer affects current session
- Calibration no longer uses outdated window data
- Extreme learned limit values (too low/high) no longer cause incorrect calculations
- SwiftBar now correctly displays all calibration information

### Technical Details
- `monitor_daemon.py`: Added `check_pid()`, `write_pid()`, `cleanup_pid()` functions
- `calibration_learner.py`: Added window validation in `get_calibrated_value()`
- `calibration_learner.py`: Added `MIN_LEARNED_LIMIT` and `MAX_LEARNED_LIMIT` constants
- `claude-calibrate`: Added pre-calibration monitor update
- `ClaudeUsage.1m.sh`: Enhanced calibration status display with window and limit info

## [2.0.0] - 2025-10-15

### Initial Release
- Real-time monitoring of Claude Code usage (session + weekly)
- Calibration system with learned limit calculation
- Global fallback limit for new sessions
- SwiftBar integration for menu bar display
- macOS notifications at 80%, 90%, 95% thresholds
- Multi-PC support with independent calibration data

[2.1.0]: https://github.com/dslee02/claude-team-usage-monitor/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/dslee02/claude-team-usage-monitor/releases/tag/v2.0.0
