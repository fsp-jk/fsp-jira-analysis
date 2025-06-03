# Developer Productivity Report Generator

A comprehensive tool for generating developer productivity reports from GitHub PR data and comments for the Flight-Schedule-Pro organization. This system collects PR statistics, comment data, and generates visual reports with trend analysis.

## Overview

This tool generates detailed productivity reports including:
- Pull Request statistics (count, lines changed, files modified)
- Comment activity (issue comments, review comments, review summaries)
- Visual trend analysis with team averages
- Individual developer performance metrics
- Year-to-date summaries and comparisons

## Prerequisites

### Required Tools
1. **GitHub CLI (gh)** - Must be installed and authenticated
   ```bash
   # Install GitHub CLI (macOS)
   brew install gh
   
   # Authenticate with GitHub
   gh auth login
   ```

2. **Python 3.7+** with required packages:
   ```bash
   pip install pandas matplotlib seaborn numpy
   ```

### Authentication Setup
- Ensure you have access to the Flight-Schedule-Pro GitHub organization
- Your GitHub CLI must be authenticated with appropriate permissions to read repositories and PRs

## Files in This System

### Data Collection Scripts
- **`github_combined_stats.sh`** - Main data collection script that gathers both PR and comment data
- **Output Files:**
  - `merged_prs_since_2025-01-01.csv` - PR data with statistics
  - `pr_comments_since_2025-01-01.csv` - Comment data from PRs

### Report Generation
- **`generate_developer_report.py`** - Python script that creates visual productivity reports
- **Output Files:**
  - `combined_developer_productivity_report.png` - Visual report with trends and comparisons

## Usage Instructions

### Step 1: Collect Data
Run the data collection script to gather PR and comment statistics:

```bash
chmod +x github_combined_stats.sh
./github_combined_stats.sh
```

**What this script does:**
- Fetches all merged PRs since January 1, 2025 from Flight-Schedule-Pro repositories
- Collects detailed statistics: lines added/deleted, files changed, merge dates
- Gathers all types of comments: issue comments, review comments, review summaries
- Filters out automated PRs (dependabot, github-actions, etc.)
- Excludes former employees (josephdavis-fsp, gypseez22)
- Processes up to 1000 PRs per repository to ensure complete data collection

**Expected output:**
```
Processing FSP-V4 (up to 1000 PRs)...
Processing FSP-Mobile (up to 1000 PRs)...
...
Total developer PRs found: 652
Total lines changed (developer PRs): 286,967
Total human comments found: 46
```

### Step 2: Generate Visual Report
Run the Python script to create the productivity report:

```bash
python3 generate_developer_report.py
```

**What this script does:**
- Processes the CSV data files created in Step 1
- Creates daily trend analysis with 21-day rolling averages for smoothing
- Generates individual developer reports vs team averages
- Shows top 10 most active developers
- Creates a combined report with all developers in one file

**Expected output:**
```
Loading PR data from merged_prs_since_2025-01-01.csv...
Processed daily data for 15 developers
Creating combined report for 10 developers...
Combined report saved as combined_developer_productivity_report.png
```

### Step 3: View Results
Open the generated report file:
- **`combined_developer_productivity_report.png`** - Main visual report

## Report Features

### Visual Report Layout
Each developer gets one row with three graphs:
1. **PRs per Day** - Daily PR merge activity vs team average
2. **Comments per Day** - Daily comment activity vs team average  
3. **Average Lines per PR** - Code change magnitude vs team average

### Data Smoothing
- Uses 21-day rolling averages for individual developer trends
- Uses 14-day rolling averages for team averages
- Provides smooth trend lines while maintaining daily granularity

### Statistics Included
- Total PRs merged per developer
- Total lines of code changed
- Average lines per PR
- Comment activity breakdown by type
- Team comparisons and rankings

## Data Filtering

### Automatically Excluded
- **Automated accounts:** dependabot[bot], github-actions[bot], app/github-actions
- **Former employees:** josephdavis-fsp, gypseez22
- **Bot comments:** Any comments from automated systems

### Date Range
- **Default:** January 1, 2025 to present (year-to-date)
- **Configurable:** Modify `START_DATE` in `github_combined_stats.sh`

## Troubleshooting

### Common Issues

1. **"gh: command not found"**
   ```bash
   # Install GitHub CLI
   brew install gh  # macOS
   # or follow instructions at https://cli.github.com/
   ```

2. **Authentication errors**
   ```bash
   gh auth login
   # Follow prompts to authenticate
   ```

3. **Python package errors**
   ```bash
   pip install pandas matplotlib seaborn numpy
   ```

4. **No data collected**
   - Verify you have access to Flight-Schedule-Pro organization
   - Check that PRs exist in the specified date range
   - Ensure GitHub CLI authentication is working: `gh repo list Flight-Schedule-Pro`

5. **Empty comment data**
   - This is normal if there are few human comments
   - Bot comments are automatically filtered out
   - The report will show "No human comments" in comment graphs

### Performance Notes
- Data collection can take 5-10 minutes depending on repository size
- FSP-V4 repository has the most PRs and takes longest to process
- The script processes up to 1000 PRs per repository for complete coverage

## Customization

### Modifying Date Range
Edit the `START_DATE` variable in `github_combined_stats.sh`:
```bash
START_DATE="2024-01-01"  # Change to desired start date
```

### Changing Repository Limits
Modify the `--limit` parameter in the script:
```bash
gh pr list --repo $ORG/$repo --limit 2000  # Increase if needed
```

### Adding/Removing Developers
Edit the filtering logic in both scripts to include/exclude specific developers.

## Output Files Description

### CSV Data Files
- **`merged_prs_since_2025-01-01.csv`** - Contains: repository, PR number, author, title, dates, line counts, file counts
- **`pr_comments_since_2025-01-01.csv`** - Contains: repository, PR number, comment details, authors, timestamps

### Visual Report
- **`combined_developer_productivity_report.png`** - Multi-panel visualization showing all developers with trend analysis

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Verify all prerequisites are installed
3. Ensure proper GitHub authentication and organization access
4. Review the console output for specific error messages

## Version History

- **v1.0** - Initial separate scripts for PRs and comments
- **v2.0** - Combined data collection script with enhanced filtering
- **v3.0** - Added visual report generation with trend analysis
- **v4.0** - Improved smoothing and daily granularity with rolling averages