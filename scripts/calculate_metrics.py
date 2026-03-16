import pandas as pd
import json
import os
from loguru import logger
from datetime import datetime
import numpy as np

def calculate_h_index(stars_list):
    """
    Calculate h-index for a list of repository stargazers counts.
    A user has index h if h of their N repos have at least h stars each.
    """
    if not stars_list:
        return 0
    
    stars_sorted = sorted(stars_list, reverse=True)
    h_index = 0
    for i, stars in enumerate(stars_sorted):
        if stars >= i + 1:
            h_index = i + 1
        else:
            break
    return h_index

def assign_score(value, percentiles):
    """Assign a score 1-10 based on where the value falls in the percentiles"""
    if value == 0:
        return 0
    for i, p in enumerate(percentiles):
        if value <= p:
            return i + 1
    return 10

def process_metrics(users_path="data/processed/users.csv", repos_path="data/processed/repositories.csv",
                    classifications_path="data/processed/classifications.csv", output_dir="data/metrics/"):
    
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info("Loading processed data...")
    try:
        users_df = pd.read_csv(users_path)
        repos_df = pd.read_csv(repos_path)
        class_df = pd.read_csv(classifications_path)
    except FileNotFoundError as e:
        logger.error(f"Missing data file: {e}. Please run extraction and classification first.")
        return
        
    """ 
    MERGE REPOS WITH CLASSIFICATIONS
    """
    # Merge repos with their industry classifications
    repos_full = pd.merge(repos_df, class_df[['repo_id', 'industry_code', 'industry_name', 'confidence']], 
                          left_on='id', right_on='repo_id', how='left')
    
    """
    USER-LEVEL METRICS (Section 8.1)
    """
    logger.info("Computing User-Level Metrics...")
    
    # 1. Activity & Engagement Metrics
    repo_stats = repos_full.groupby('owner_login').agg(
        total_stars_received=('stargazers_count', 'sum'),
        total_forks_received=('forks_count', 'sum'),
        total_open_issues=('open_issues_count', 'sum'),
        avg_stars_per_repo=('stargazers_count', 'mean'),
        has_license_pct=('url', lambda x: 0.0), # Simplification as license wasn't strictly extracted in MVP
        has_readme_pct=('url', lambda x: 100.0) # We specifically fetched repos with readmes for classification
    ).reset_index()
    
    # Calculate H-index per user
    h_indices = repos_full.groupby('owner_login')['stargazers_count'].apply(list).apply(calculate_h_index).reset_index(name='h_index')
    
    # Calculate language and industry diversity
    diversity = repos_full.groupby('owner_login').agg(
        primary_languages=('language', lambda x: x.dropna().nunique()),
        industries_served=('industry_name', lambda x: x.dropna().nunique())
    ).reset_index()
    
    # Calculate Days since last push / active status
    # Note: Using 'updated_at' from user profile as proxy for activity
    current_date = datetime.now()
    
    # Remove timezone info (tz-naive) to avoid pandas TypeError when calculating differences
    users_df['updated_at_dt'] = pd.to_datetime(users_df['updated_at']).dt.tz_localize(None)
    users_df['created_at_dt'] = pd.to_datetime(users_df['created_at']).dt.tz_localize(None)
    
    users_df['days_since_last_push'] = (current_date - users_df['updated_at_dt']).dt.days
    users_df['is_active'] = users_df['days_since_last_push'] <= 90
    users_df['account_age_days'] = (current_date - users_df['created_at_dt']).dt.days
    users_df['repos_per_year'] = (users_df['public_repos'] / (users_df['account_age_days'] / 365.25)).replace([np.inf, -np.inf], 0).fillna(0)
    users_df['follower_ratio'] = (users_df['followers'] / users_df['following'].replace(0, 1)).fillna(0)
    
    # Merge all user metrics
    user_metrics = users_df.merge(repo_stats, left_on='login', right_on='owner_login', how='left')
    user_metrics = user_metrics.merge(h_indices, left_on='login', right_on='owner_login', how='left')
    user_metrics = user_metrics.merge(diversity, left_on='login', right_on='owner_login', how='left')
    
    # Fill NAs
    user_metrics.fillna(0, inplace=True)
    
    # Calculate Impact Score (Custom heuristic: 40% stars, 30% h-index, 20% followers, 10% forks)
    # Normalize values for fair scoring using clipping
    max_stars = user_metrics['total_stars_received'].quantile(0.95) or 1
    max_h = user_metrics['h_index'].max() or 1
    max_foll = user_metrics['followers'].quantile(0.95) or 1
    
    user_metrics['impact_score'] = (
        0.4 * (user_metrics['total_stars_received'].clip(upper=max_stars) / max_stars * 100) +
        0.3 * (user_metrics['h_index'] / max_h * 100) +
        0.2 * (user_metrics['followers'].clip(upper=max_foll) / max_foll * 100) +
        0.1 * (user_metrics['total_forks_received'].clip(upper=user_metrics['total_forks_received'].quantile(0.95) or 1) / (user_metrics['total_forks_received'].quantile(0.95) or 1) * 100)
    ).round(2)
    
    # Clean up redundant columns
    cols_to_drop = ['updated_at_dt', 'created_at_dt', 'owner_login_x', 'owner_login_y']
    user_metrics.drop(columns=[c for c in cols_to_drop if c in user_metrics.columns], inplace=True)
    
    user_metrics_path = os.path.join(output_dir, "user_metrics.csv")
    user_metrics.to_csv(user_metrics_path, index=False)
    logger.success(f"Saved {len(user_metrics)} user metrics to {user_metrics_path}")
    
    """
    ECOSYSTEM-LEVEL METRICS (Section 8.3)
    """
    logger.info("Computing Ecosystem-Level Metrics...")
    
    most_popular_langs = repos_full['language'].value_counts().head(10).to_dict()
    industry_dist = repos_full['industry_name'].value_counts().to_dict()
    
    ecosystem_metrics = {
        "ecosystem_size": {
            "total_developers": len(users_df),
            "total_repositories": len(repos_full),
            "total_stars": int(repos_full['stargazers_count'].sum())
        },
        "averages": {
            "avg_repos_per_user": round(float(users_df['public_repos'].mean()), 2),
            "avg_stars_per_repo": round(float(repos_full['stargazers_count'].mean()), 2),
            "avg_account_age_years": round(float(users_df['account_age_days'].mean() / 365.25), 2)
        },
        "health_indicators": {
            "active_developer_pct": round(float(users_df['is_active'].mean() * 100), 2),
            "repos_with_issues_pct": round(float((repos_full['open_issues_count'] > 0).mean() * 100), 2)
        },
        "top_technologies": {
            "most_popular_languages": most_popular_langs
        },
        "industry_distribution": industry_dist
    }
    
    eco_metrics_path = os.path.join(output_dir, "ecosystem_metrics.json")
    with open(eco_metrics_path, 'w') as f:
        json.dump(ecosystem_metrics, f, indent=4)
        
    logger.success(f"Saved ecosystem metrics to {eco_metrics_path}")

if __name__ == "__main__":
    process_metrics()
