# Privacy Policy for Claude Usage Monitor

**Last Updated: October 23, 2025**

## Overview

Claude Usage Monitor is a Chrome Extension that helps users monitor their Claude AI usage limits. This privacy policy explains what data we collect, how we use it, and your rights.

## Data Collection

### What Data We Collect

This extension collects the following data **locally on your device**:

1. **Claude Usage Statistics**
   - Session usage percentage
   - Weekly usage percentage
   - Reset times for usage limits
   - Last update timestamp

### How We Collect Data

- Data is scraped from the publicly visible Claude.ai usage page (`https://claude.ai/settings/usage`) that you can already access when logged into your Claude account
- No additional or hidden data is collected beyond what you can already see on the Claude.ai website

## Data Storage and Usage

### Local Storage Only

- All collected data is stored **locally** in your browser using `chrome.storage.local`
- **No data is transmitted** to external servers
- **No data is uploaded** to the internet
- **No analytics or tracking** services are used

### How Data is Used

Data is used exclusively for:
1. Displaying usage statistics in the extension popup
2. Showing usage percentage in the extension badge
3. Optionally exporting to a local JSON file in your Downloads folder (for advanced users integrating with SwiftBar on macOS)

## Permissions Explained

### Required Permissions

- **storage**: Store usage data locally in your browser
- **alarms**: Schedule automatic usage checks every 5 minutes
- **tabs**: Open Claude.ai usage page in background for data scraping
- **activeTab**: Interact with Claude.ai pages when you click "Scrape Now"
- **downloads**: Export usage data as JSON file to your Downloads folder (optional)
- **host_permissions (https://claude.ai/*)**: Access the Claude.ai usage page to read your usage statistics

### What We DON'T Do

- ❌ We do NOT collect personal information (name, email, passwords)
- ❌ We do NOT track your browsing history
- ❌ We do NOT share data with third parties
- ❌ We do NOT sell your data
- ❌ We do NOT use analytics or tracking tools
- ❌ We do NOT access your Claude conversations or chat history
- ❌ We do NOT transmit data to external servers

## Data Security

- All data remains on your local device
- No network requests are made except to `https://claude.ai/settings/usage` (which you already have access to)
- Data is only accessible to you through the extension

## Your Rights

### Data Access and Deletion

You can:
- View your data anytime in the extension popup
- Clear your data by:
  - Removing the extension (all data is automatically deleted)
  - Clearing browser storage
  - Using the browser's extension data management tools

### Opt-Out

You can stop data collection at any time by:
- Disabling the extension
- Uninstalling the extension

## Third-Party Services

This extension does NOT use any third-party services, analytics, or tracking tools.

## Children's Privacy

This extension does not knowingly collect information from children under 13. If you are under 13, please do not use this extension.

## Open Source

This extension is open source. You can review the complete source code at:
https://github.com/dasol02/claude-monitor-usage

## Changes to This Policy

We may update this privacy policy from time to time. Any changes will be reflected in the "Last Updated" date at the top of this document and in the extension's GitHub repository.

## Contact

For questions or concerns about this privacy policy, please open an issue on GitHub:
https://github.com/dasol02/claude-monitor-usage/issues

## Consent

By installing and using Claude Usage Monitor, you consent to this privacy policy.
