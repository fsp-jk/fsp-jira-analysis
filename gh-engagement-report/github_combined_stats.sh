#!/bin/bash

# Combined script to get PR data and comment data for Flight-Schedule-Pro organization
# Requires GitHub CLI (gh) to be installed and authenticated

# Set the start date
START_DATE="2025-01-01"
ORG="Flight-Schedule-Pro"

echo "Fetching DETAILED merged PR and comment data for $ORG since $START_DATE..."
echo

# Create output CSV files with headers
PR_CSV_FILE="merged_prs_since_${START_DATE}.csv"
COMMENT_CSV_FILE="pr_comments_since_${START_DATE}.csv"

echo "repository,pr_number,author,title,created_at,merged_at,base_branch,lines_added,lines_deleted,total_lines_changed,files_changed" > $PR_CSV_FILE
echo "repository,pr_number,comment_id,comment_type,comment_author,comment_body,comment_created_at,comment_updated_at,pr_author,pr_title" > $COMMENT_CSV_FILE

# Create a temp file for summary stats
temp_summary=$(mktemp)

# Function to process PR data and comments for a repository
process_repo_data() {
  local repo=$1
  local pr_data_file=$2
  
  local repo_pr_count=0
  
  # Filter out automated PRs, former employees, and process the rest
  jq -r '.[] | select(.author.login != "app/github-actions" and .author.login != "dependabot[bot]" and .author.login != "github-actions[bot]" and .author.login != "josephdavis-fsp" and .author.login != "gypseez22") | [.number, .author.login, .title, .createdAt, .mergedAt, .baseRefName] | join("|")' $pr_data_file | while IFS='|' read -r pr_number pr_author pr_title created_at merged_at base_branch; do
    echo "  Processing $repo PR #$pr_number by $pr_author..."
    
    # Get PR diff stats
    pr_stats=$(gh api repos/$ORG/$repo/pulls/$pr_number --jq '[.additions, .deletions, .changed_files] | join("|")' 2>/dev/null || echo "0|0|0")
    IFS='|' read -r additions deletions changed_files <<< "$pr_stats"
    
    # Calculate total lines changed
    total_changes=$((additions + deletions))
    
    # Write PR data to CSV with proper escaping
    echo "$repo,$pr_number,$pr_author,\"$(echo "$pr_title" | sed 's/"/""/g')\",$created_at,$merged_at,$base_branch,$additions,$deletions,$total_changes,$changed_files" >> $PR_CSV_FILE
    
    # Get ALL types of comments for this PR
    echo "    Getting all comments for PR #$pr_number..."
    
    # 1. Get issue comments (general PR comments)
    gh api repos/$ORG/$repo/issues/$pr_number/comments --jq '.[] | select(.user.login | test("bot|github-actions|app/github-actions|josephdavis-fsp|gypseez22"; "i") | not) | [
      "'"$repo"'",
      "'"$pr_number"'",
      .id,
      "issue",
      .user.login,
      "\"" + (.body | gsub("\n"; " ") | gsub("\""; "\"\"")) + "\"",
      .created_at,
      .updated_at,
      "'"$pr_author"'",
      "\"" + ("'"$(echo "$pr_title" | sed 's/"/""/g')"'" | gsub("\""; "\"\"")) + "\""
    ] | join(",")' >> $COMMENT_CSV_FILE 2>/dev/null
    
    # 2. Get review comments (code-specific comments)
    gh api repos/$ORG/$repo/pulls/$pr_number/comments --jq '.[] | select(.user.login | test("bot|github-actions|app/github-actions|josephdavis-fsp|gypseez22"; "i") | not) | [
      "'"$repo"'",
      "'"$pr_number"'",
      .id,
      "review",
      .user.login,
      "\"" + (.body | gsub("\n"; " ") | gsub("\""; "\"\"")) + "\"",
      .created_at,
      .updated_at,
      "'"$pr_author"'",
      "\"" + ("'"$(echo "$pr_title" | sed 's/"/""/g')"'" | gsub("\""; "\"\"")) + "\""
    ] | join(",")' >> $COMMENT_CSV_FILE 2>/dev/null
    
    # 3. Get review summary comments
    gh api repos/$ORG/$repo/pulls/$pr_number/reviews --jq '.[] | select(.user.login | test("bot|github-actions|app/github-actions|josephdavis-fsp|gypseez22"; "i") | not) | select(.body != null and .body != "") | [
      "'"$repo"'",
      "'"$pr_number"'",
      .id,
      "review_summary",
      .user.login,
      "\"" + (.body | gsub("\n"; " ") | gsub("\""; "\"\"")) + "\"",
      .submitted_at,
      .submitted_at,
      "'"$pr_author"'",
      "\"" + ("'"$(echo "$pr_title" | sed 's/"/""/g')"'" | gsub("\""; "\"\"")) + "\""
    ] | join(",")' >> $COMMENT_CSV_FILE 2>/dev/null
    
    repo_pr_count=$((repo_pr_count + 1))
  done
  
  echo "$repo_pr_count"
}

# Get list of all repositories in the organization
repos=$(gh repo list $ORG --limit 1000 --json name -q '.[].name')

# Process each repository with same logic (1000 PR limit for all)
total_pr_count=0
for repo in $repos; do
  echo "Processing $repo (up to 1000 PRs)..."
  
  # Get merged PRs with 1000 limit for ALL repos
  gh pr list --repo $ORG/$repo --state merged --json number,author,title,createdAt,mergedAt,baseRefName --search "merged:>=$START_DATE" --limit 1000 > /tmp/repo_prs.json
  
  # Count PRs before and after filtering
  repo_total=$(jq '. | length' /tmp/repo_prs.json)
  repo_automated=$(jq '[.[] | select(.author.login == "app/github-actions" or .author.login == "dependabot[bot]" or .author.login == "github-actions[bot]")] | length' /tmp/repo_prs.json)
  repo_former=$(jq '[.[] | select(.author.login == "josephdavis-fsp" or .author.login == "gypseez22")] | length' /tmp/repo_prs.json)
  repo_filtered=$((repo_automated + repo_former))
  repo_count=$((repo_total - repo_filtered))
  total_pr_count=$((total_pr_count + repo_count))
  
  # Process PRs and comments for this repo
  if [ $repo_count -gt 0 ]; then
    echo "Processing $repo PRs and comments..."
    repo_processed=$(process_repo_data "$repo" "/tmp/repo_prs.json")
  fi
  
  # Append to summary
  if [ $repo_filtered -gt 0 ]; then
    if [ $repo_former -gt 0 ]; then
      echo "$repo: $repo_total total PRs ($repo_automated automated + $repo_former former employees filtered, $repo_count developer PRs)" >> $temp_summary
    else
      echo "$repo: $repo_total total PRs ($repo_automated automated filtered, $repo_count developer PRs)" >> $temp_summary
    fi
  else
    echo "$repo: $repo_count PRs" >> $temp_summary
  fi
done

# Count total comments collected
total_comment_lines=$(wc -l < $COMMENT_CSV_FILE)
total_comments=$((total_comment_lines - 1))  # Subtract header

echo
echo "REPOSITORY SUMMARY (sorted by PR count):"
echo "----------------------------------------"
sort -t: -k2 -nr $temp_summary

echo
echo "PR counts per developer since $START_DATE:"
echo "----------------------------------------"
awk -F, '{print $3}' $PR_CSV_FILE | grep -v "author" | sort | uniq -c | sort -nr

echo
echo "Comment counts per developer since $START_DATE:"
echo "----------------------------------------------"
if [ $total_comments -gt 0 ]; then
  echo "All comment types:"
  awk -F, '{print $5}' $COMMENT_CSV_FILE | grep -v "comment_author" | sort | uniq -c | sort -nr
  echo
  echo "Comment types breakdown:"
  awk -F, 'NR>1 {print $4}' $COMMENT_CSV_FILE | sort | uniq -c
else
  echo "No human comments found (only bot comments were filtered out)"
fi

echo
echo "Line change statistics per developer since $START_DATE:"
echo "-------------------------------------------------------"
awk -F, 'NR>1 {author=$3; lines=$10; total_lines[author]+=lines; pr_count[author]++} END {for(a in total_lines) printf "%-25s %8d lines (%d PRs, avg: %d lines/PR)\n", a, total_lines[a], pr_count[a], total_lines[a]/pr_count[a]}' $PR_CSV_FILE | sort -k2 -nr

# Print overall totals
echo
echo "Overall statistics since $START_DATE:"
echo "-------------------------------------"
total_lines=$(awk -F, 'NR>1 {sum+=$10} END {print sum}' $PR_CSV_FILE)
total_automated=$(awk 'BEGIN{sum=0} /automated filtered/ {match($0, /\(([0-9]+) automated/, arr); sum+=arr[1]} END{print sum}' $temp_summary)
total_former=$(awk 'BEGIN{sum=0} /former employees filtered/ {match($0, /\+ ([0-9]+) former employees/, arr); sum+=arr[1]} END{print sum}' $temp_summary)

echo "Total developer PRs found: $total_pr_count"
echo "Total filtered PRs: $((total_automated + total_former)) ($total_automated automated + $total_former former employees)"
echo "Total lines changed (developer PRs): $total_lines"
echo "Total human comments found: $total_comments"
if [ $total_pr_count -gt 0 ]; then
  echo "Average lines per developer PR: $((total_lines / total_pr_count))"
fi
echo
echo "Note: Excluded josephdavis-fsp and gypseez22 (former employees)"
echo "Note: Collected issue comments, review comments, and review summaries"
echo "Data saved to:"
echo "- $PR_CSV_FILE (PR data)"
echo "- $COMMENT_CSV_FILE (Comment data)"

# Clean up
rm $temp_summary /tmp/repo_prs.json 2>/dev/null 