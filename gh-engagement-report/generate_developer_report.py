#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
from datetime import datetime, timedelta
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Set style for better looking plots
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

def load_and_process_pr_data(csv_file):
    """Load PR data and process by developer and date"""
    print(f"Loading PR data from {csv_file}...")
    
    # List of former employees to filter out
    former_employees = ['josephdavis-fsp', 'gypseez22']
    
    df = pd.read_csv(csv_file)
    
    # Filter out former employees
    df = df[~df['author'].isin(former_employees)]
    print(f"Filtered out former employees: {', '.join(former_employees)}")
    
    # Convert merged_at to datetime and extract date
    df['merged_at'] = pd.to_datetime(df['merged_at'])
    df['date'] = df['merged_at'].dt.date
    
    # Group by developer and date (keep daily granularity)
    daily_prs = df.groupby(['author', 'date']).agg({
        'pr_number': 'count',
        'total_lines_changed': ['sum', 'mean']
    }).reset_index()
    
    # Flatten column names
    daily_prs.columns = ['author', 'date', 'pr_count', 'total_lines', 'avg_lines_per_pr']
    daily_prs['date'] = pd.to_datetime(daily_prs['date'])
    
    print(f"Processed daily data for {daily_prs['author'].nunique()} developers")
    
    return daily_prs

def load_and_process_comment_data(csv_file):
    """Load comment data and process by developer and date"""
    print(f"Loading comment data from {csv_file}...")
    
    # List of former employees to filter out
    former_employees = ['josephdavis-fsp', 'gypseez22']
    
    df = pd.read_csv(csv_file)
    
    # Filter out bots from comments (they should already be filtered but double-check)
    print(f"Original comment count: {len(df)}")
    df = df[~df['comment_author'].str.contains('bot|github-actions|app/github-actions', case=False, na=False)]
    print(f"After filtering bots: {len(df)}")
    
    # Filter out former employees
    df = df[~df['comment_author'].isin(former_employees)]
    print(f"After filtering former employees: {len(df)}")
    
    if len(df) == 0:
        print("WARNING: No human comments found after filtering!")
        # Return empty dataframe with proper structure
        return pd.DataFrame(columns=['author', 'date', 'comment_count'])
    
    # Show comment type breakdown
    print("Comment types found:", df['comment_type'].value_counts().to_dict())
    
    # Convert comment_created_at to datetime and extract date (handle malformed data)
    df['comment_created_at'] = pd.to_datetime(df['comment_created_at'], errors='coerce')
    
    # Remove rows with invalid dates
    invalid_dates = df['comment_created_at'].isna().sum()
    if invalid_dates > 0:
        print(f"Removing {invalid_dates} rows with invalid timestamps")
        df = df.dropna(subset=['comment_created_at'])
    
    df['date'] = df['comment_created_at'].dt.date
    
    # Group by developer and date (keep daily granularity)
    daily_comments = df.groupby(['comment_author', 'date']).agg({
        'comment_id': 'count'
    }).reset_index()
    
    daily_comments.columns = ['author', 'date', 'comment_count']
    daily_comments['date'] = pd.to_datetime(daily_comments['date'])
    
    print(f"Processed daily comment data for {daily_comments['author'].nunique()} developers")
    
    return daily_comments

def create_complete_date_range(start_date='2025-01-01'):
    """Create complete daily date range from start of 2025 to today"""
    start = pd.to_datetime(start_date)
    end = pd.to_datetime('today')
    return pd.date_range(start=start, end=end, freq='D')

def fill_missing_dates(df, date_range, authors):
    """Fill missing dates with zero values for all developers"""
    # Create all combinations of authors and dates
    author_dates = [(author, date) for author in authors for date in date_range]
    complete_df = pd.DataFrame(author_dates, columns=['author', 'date'])
    
    # Merge with actual data, filling missing values with 0
    merged = complete_df.merge(df, on=['author', 'date'], how='left').fillna(0)
    return merged

def plot_developer_trends(pr_data, comment_data, output_file='developer_productivity_report.png'):
    """Create individual developer productivity visualizations vs team averages"""
    
    # Get all unique developers from both datasets
    pr_authors = set(pr_data['author'].unique())
    comment_authors = set(comment_data['author'].unique()) if not comment_data.empty else set()
    all_authors = pr_authors.union(comment_authors)
    
    # Remove any automated accounts that might have slipped through
    all_authors = {author for author in all_authors 
                  if not any(bot in author.lower() for bot in ['bot', 'github-actions', 'app/github-actions'])}
    
    # Filter to top 10 most active developers by total PRs
    top_developers = pr_data.groupby('author')['pr_count'].sum().nlargest(10).index.tolist()
    all_authors = [author for author in top_developers if author in all_authors]
    
    print(f"Creating combined report for {len(all_authors)} developers...")
    
    # Create date range
    date_range = create_complete_date_range()
    
    # Fill missing dates for both datasets
    pr_complete = fill_missing_dates(pr_data, date_range, all_authors)
    comment_complete = fill_missing_dates(comment_data, date_range, all_authors) if not comment_data.empty else pd.DataFrame()
    
    # Calculate team averages with longer rolling windows for smoothing
    print("Calculating team averages...")
    
    # PR averages
    pr_daily_avg = pr_complete.groupby('date').agg({
        'pr_count': 'mean',
        'avg_lines_per_pr': 'mean'
    }).reset_index()
    pr_daily_avg['pr_count_ma'] = pr_daily_avg['pr_count'].rolling(window=14, center=True, min_periods=3).mean()  # 14-day rolling average
    pr_daily_avg['avg_lines_ma'] = pr_daily_avg['avg_lines_per_pr'].rolling(window=14, center=True, min_periods=3).mean()
    
    # Comment averages (if we have comment data)
    if not comment_complete.empty:
        comment_daily_avg = comment_complete.groupby('date')['comment_count'].mean().reset_index()
        comment_daily_avg['comment_count_ma'] = comment_daily_avg['comment_count'].rolling(window=14, center=True, min_periods=3).mean()
    else:
        comment_daily_avg = pd.DataFrame()
    
    # Create combined report with all developers
    num_devs = len(all_authors)
    # Each developer gets one row with 3 columns (PRs, Comments, Lines)
    rows = num_devs
    cols = 3
    
    # Create large figure for combined report
    fig, axes = plt.subplots(rows, cols, figsize=(18, 4 * rows))
    fig.suptitle('Developer Productivity Report - All Developers\n2025 Year to Date vs Team Average (Daily Trends with Smoothing)', 
                fontsize=20, fontweight='bold')
    
    # Handle case where we have only one developer
    if num_devs == 1:
        axes = axes.reshape(1, -1)
    
    for i, author in enumerate(all_authors):
        print(f"Adding {author} to combined report ({i+1}/{num_devs})...")
        
        # Each developer gets row i
        row = i
        
        # Get this developer's data with longer rolling windows for smoothing
        author_pr_data = pr_complete[pr_complete['author'] == author].sort_values('date')
        author_pr_data['pr_count_ma'] = author_pr_data['pr_count'].rolling(window=21, center=True, min_periods=3).mean()  # 21-day rolling average
        author_pr_data['avg_lines_ma'] = author_pr_data['avg_lines_per_pr'].rolling(window=21, center=True, min_periods=3).mean()
        
        if not comment_complete.empty:
            author_comment_data = comment_complete[comment_complete['author'] == author].sort_values('date')
            author_comment_data['comment_count_ma'] = author_comment_data['comment_count'].rolling(window=21, center=True, min_periods=3).mean()
        else:
            author_comment_data = pd.DataFrame()
        
        # Plot 1: PRs per day vs team average (Column 0)
        ax1 = axes[row, 0]
        ax1.plot(pr_daily_avg['date'], pr_daily_avg['pr_count_ma'], 
                label='Team Avg', color='gray', linewidth=2, alpha=0.7, linestyle='--')
        ax1.plot(author_pr_data['date'], author_pr_data['pr_count_ma'], 
                label=author, color='#1f77b4', linewidth=2)
        
        ax1.set_title(f'{author} - PRs per Day', fontsize=14, fontweight='bold')
        ax1.set_ylabel('PRs per Day', fontsize=12)
        ax1.legend(fontsize=10)
        ax1.grid(True, alpha=0.3)
        ax1.tick_params(axis='both', which='major', labelsize=10)
        
        # Add stats text
        author_total_prs = pr_data[pr_data['author'] == author]['pr_count'].sum()
        team_avg_prs = pr_data.groupby('author')['pr_count'].sum().mean()
        ax1.text(0.02, 0.98, f'Total: {author_total_prs} (Avg: {team_avg_prs:.1f})', 
                transform=ax1.transAxes, verticalalignment='top', fontsize=10,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
        
        # Plot 2: Comments per day vs team average (Column 1)
        ax2 = axes[row, 1]
        if not comment_daily_avg.empty and not author_comment_data.empty:
            ax2.plot(comment_daily_avg['date'], comment_daily_avg['comment_count_ma'], 
                    label='Team Avg', color='gray', linewidth=2, alpha=0.7, linestyle='--')
            ax2.plot(author_comment_data['date'], author_comment_data['comment_count_ma'], 
                    label=author, color='#ff7f0e', linewidth=2)
            ax2.legend(fontsize=10)
        else:
            ax2.text(0.5, 0.5, 'No human comments', ha='center', va='center', 
                    transform=ax2.transAxes, fontsize=12,
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray"))
        
        ax2.set_title(f'{author} - Comments per Day', fontsize=14, fontweight='bold')
        ax2.set_ylabel('Comments per Day', fontsize=12)
        ax2.grid(True, alpha=0.3)
        ax2.tick_params(axis='both', which='major', labelsize=10)
        
        # Plot 3: Average lines changed per PR vs team average (Column 2)
        ax3 = axes[row, 2]
        
        # Filter to only show data where there were actual PRs
        author_pr_with_lines = author_pr_data[author_pr_data['pr_count'] > 0]
        team_pr_with_lines = pr_daily_avg[pr_daily_avg['pr_count'] > 0]
        
        if len(team_pr_with_lines) > 0:
            ax3.plot(team_pr_with_lines['date'], team_pr_with_lines['avg_lines_ma'], 
                    label='Team Avg', color='gray', linewidth=2, alpha=0.7, linestyle='--')
        
        if len(author_pr_with_lines) > 0:
            ax3.plot(author_pr_with_lines['date'], author_pr_with_lines['avg_lines_ma'], 
                    label=author, color='#2ca02c', linewidth=2)
        
        ax3.set_title(f'{author} - Avg Lines per PR', fontsize=14, fontweight='bold')
        ax3.set_ylabel('Lines per PR', fontsize=12)
        ax3.legend(fontsize=10)
        ax3.grid(True, alpha=0.3)
        ax3.tick_params(axis='both', which='major', labelsize=10)
        
        # Add stats text
        author_avg_lines = pr_data[pr_data['author'] == author]['avg_lines_per_pr'].mean()
        team_avg_lines = pr_data['avg_lines_per_pr'].mean()
        ax3.text(0.02, 0.98, f'Avg: {author_avg_lines:.0f} (Team: {team_avg_lines:.0f})', 
                transform=ax3.transAxes, verticalalignment='top', fontsize=10,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
        
        # Format dates on x-axis for all three graphs (daily ticks but spaced out)
        for ax in [ax1, ax2, ax3]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))  # Every 2 weeks
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, fontsize=10)
            ax.set_xlabel('Date', fontsize=12)
    
    plt.tight_layout()
    
    # Save combined report
    combined_file = "combined_developer_productivity_report.png"
    plt.savefig(combined_file, dpi=300, bbox_inches='tight')
    print(f"Combined report saved as {combined_file}")
    
    plt.close(fig)  # Close to save memory
    
    print(f"Combined report created!")
    return combined_file

def generate_summary_stats(pr_data, comment_data):
    """Generate summary statistics for the report"""
    print("\n" + "="*60)
    print("DEVELOPER PRODUCTIVITY SUMMARY - 2025 YTD")
    print("="*60)
    
    # Filter out former employees from summary stats
    former_employees = ['josephdavis-fsp', 'gypseez22']
    
    # PR Statistics (filter by original author data before aggregation)
    original_pr_data = pd.read_csv("merged_prs_since_2025-01-01.csv")
    original_pr_data = original_pr_data[~original_pr_data['author'].isin(former_employees)]
    
    pr_stats = original_pr_data.groupby('author').agg({
        'pr_number': 'count',
        'total_lines_changed': ['sum', 'mean']
    })
    
    # Flatten multi-level columns properly
    pr_stats.columns = ['pr_count', 'total_lines', 'avg_lines_per_pr']
    pr_stats = pr_stats.round(2)
    
    # Comment Statistics (if we have comment data)
    if not comment_data.empty:
        original_comment_data = pd.read_csv("pr_comments_since_2025-01-01.csv")
        # Filter bots and former employees
        original_comment_data = original_comment_data[
            ~original_comment_data['comment_author'].str.contains('bot|github-actions|app/github-actions', case=False, na=False)
        ]
        original_comment_data = original_comment_data[~original_comment_data['comment_author'].isin(former_employees)]
        
        if len(original_comment_data) > 0:
            comment_stats = original_comment_data.groupby('comment_author')['comment_id'].count()
            comment_stats.name = 'comment_count'
        else:
            comment_stats = pd.Series(dtype=int, name='comment_count')
    else:
        comment_stats = pd.Series(dtype=int, name='comment_count')
    
    # Combine stats
    combined_stats = pr_stats.merge(comment_stats, left_index=True, right_index=True, how='left').fillna(0)
    combined_stats = combined_stats.sort_values('pr_count', ascending=False)
    
    print(f"{'Developer':<25} {'PRs':<6} {'Lines':<8} {'Avg/PR':<8} {'Comments':<10}")
    print("-"*60)
    
    for author, row in combined_stats.iterrows():
        print(f"{author:<25} {int(row['pr_count']):<6} {int(row['total_lines']):<8} {row['avg_lines_per_pr']:<8.0f} {int(row['comment_count']):<10}")
    
    # Overall totals
    total_prs = combined_stats['pr_count'].sum()
    total_lines = combined_stats['total_lines'].sum()
    total_comments = combined_stats['comment_count'].sum()
    
    print("-"*60)
    print(f"{'TOTALS':<25} {int(total_prs):<6} {int(total_lines):<8} {'':<8} {int(total_comments):<10}")
    print(f"\nAverage lines per PR across all developers: {total_lines/total_prs:.0f}")
    print("Note: Former employees (josephdavis-fsp, gypseez22) excluded from analysis")

def main():
    """Main function to generate the developer productivity report"""
    print("Generating Developer Productivity Report for 2025...")
    
    # File paths
    pr_file = "merged_prs_since_2025-01-01.csv"
    comment_file = "pr_comments_since_2025-01-01.csv"
    
    # Check if files exist
    if not Path(pr_file).exists():
        print(f"Error: {pr_file} not found. Please run github_pr_stats.sh first.")
        return
        
    if not Path(comment_file).exists():
        print(f"Error: {comment_file} not found. Please run github_pr_comments.sh first.")
        return
    
    # Load and process data
    pr_data = load_and_process_pr_data(pr_file)
    comment_data = load_and_process_comment_data(comment_file)
    
    # Generate visualizations
    combined_file = plot_developer_trends(pr_data, comment_data)
    
    # Generate summary statistics
    generate_summary_stats(pr_data, comment_data)
    
    print(f"\nReport generation complete!")
    print("Files created:")
    print(f"- {combined_file} (combined visual report)")
    print(f"\nTo view the report, open {combined_file}")

if __name__ == "__main__":
    main() 