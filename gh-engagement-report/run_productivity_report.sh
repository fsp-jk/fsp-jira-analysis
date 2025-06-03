#!/bin/bash

echo "=========================================="
echo "Developer Productivity Report Generator"
echo "Flight-Schedule-Pro Organization - 2025 YTD"
echo "=========================================="
echo

# Check if required tools are installed
if ! command -v gh &> /dev/null; then
    echo "Error: GitHub CLI (gh) is required. Please install it first."
    exit 1
fi

if ! command -v jq &> /dev/null; then
    echo "Error: jq is required. Please install it first."
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required. Please install it first."
    exit 1
fi

echo "Step 1: Collecting GitHub PR and comment data..."
echo "----------------------------------------------"
./github_combined_stats.sh

if [ $? -ne 0 ]; then
    echo "Error: Failed to collect data. Please check your GitHub authentication."
    exit 1
fi

echo
echo "Step 2: Collecting GitHub PR comment data..."
echo "--------------------------------------------"
# (This step is now combined with Step 1)
echo "Combined with Step 1 for efficiency"

echo
echo "Step 3: Installing Python dependencies..."
echo "----------------------------------------"
pip3 install -r requirements.txt

echo
echo "Step 4: Generating visual report..."
echo "----------------------------------"
python3 generate_developer_report.py

if [ $? -eq 0 ]; then
    echo
    echo "=========================================="
    echo "Report Generation Complete!"
    echo "=========================================="
    echo "Files created:"
    echo "- merged_prs_since_2025-01-01.csv (PR data)"
    echo "- pr_comments_since_2025-01-01.csv (Comment data)"
    echo "- combined_developer_productivity_report.png (Combined visual report)"
    echo
    echo "The combined script efficiently collected both PR and comment data!"
    echo "Open combined_developer_productivity_report.png to view all developer charts!"
else
    echo "Error: Failed to generate visual report."
    exit 1
fi 