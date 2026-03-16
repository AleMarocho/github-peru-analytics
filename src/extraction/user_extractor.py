import os
import pandas as pd
from loguru import logger
from typing import List, Dict, Any
from .github_client import GitHubClient

class DataExtractor:
    def __init__(self, raw_data_path: str = "data/raw/"):
        self.client = GitHubClient()
        self.raw_data_path = raw_data_path
        
        # Ensure raw directories exist
        os.makedirs(os.path.join(self.raw_data_path, "users"), exist_ok=True)
        os.makedirs(os.path.join(self.raw_data_path, "repos"), exist_ok=True)

    def extract_peru_ecosystem(self, max_repos_target: int = 1000):
        """
        Main extraction pipeline to collect at least max_repos_target repositories 
        from Peruvian owners along with their details.
        """
        locations = ["Peru", "Lima", "Arequipa", "Trujillo", "Cusco"]
        
        users_data = []
        repos_data = []
        
        collected_repos = 0
        
        # 1. Search for users in Peru
        for loc in locations:
            # We fetch 150 users per location to ensure we eventually hit > 1000 repos
            # Some users might have 0 public repos.
            if collected_repos >= max_repos_target:
                break
                
            logger.info(f"--- Starting extraction for location: {loc} ---")
            users = self.client.search_users(location=loc, max_users=100)
            
            for base_user in users:
                username = base_user.get("login")
                
                # Fetch detailed user info
                try:
                    detailed_user = self.client._make_request(f"users/{username}")
                    users_data.append({
                        "id": detailed_user.get("id"),
                        "login": detailed_user.get("login"),
                        "name": detailed_user.get("name"),
                        "company": detailed_user.get("company"),
                        "blog": detailed_user.get("blog"),
                        "location": detailed_user.get("location"),
                        "email": detailed_user.get("email"),
                        "hireable": detailed_user.get("hireable"),
                        "bio": detailed_user.get("bio"),
                        "public_repos": detailed_user.get("public_repos"),
                        "followers": detailed_user.get("followers"),
                        "following": detailed_user.get("following"),
                        "created_at": detailed_user.get("created_at"),
                        "updated_at": detailed_user.get("updated_at")
                    })
                except Exception as e:
                    logger.warning(f"Could not fetch details for {username}: {e}")
                    continue
                
                # Fetch user's repositories (only if they have public repos)
                if detailed_user.get("public_repos", 0) > 0:
                    repos = self.client.get_user_repositories(username)
                    
                    for repo in repos:
                        repo_name = repo.get("name")
                        readme_content = self.client.get_repository_readme(username, repo_name)
                        
                        repos_data.append({
                            "id": repo.get("id"),
                            "name": repo_name,
                            "full_name": repo.get("full_name"),
                            "owner_login": username,
                            "description": repo.get("description"),
                            "url": repo.get("html_url"),
                            "language": repo.get("language"),
                            "topics": ",".join(repo.get("topics", [])),
                            "stargazers_count": repo.get("stargazers_count"),
                            "watchers_count": repo.get("watchers_count"),
                            "forks_count": repo.get("forks_count"),
                            "open_issues_count": repo.get("open_issues_count"),
                            "created_at": repo.get("created_at"),
                            "updated_at": repo.get("updated_at"),
                            "readme": readme_content
                        })
                        collected_repos += 1
                        
                        if collected_repos % 50 == 0:
                            logger.info(f"Collected {collected_repos}/{max_repos_target} repos...")
                            
                if collected_repos >= max_repos_target:
                    logger.success(f"Target of {max_repos_target} repositories reached!")
                    break
        
        # Save raw data
        self._save_to_csv(users_data, os.path.join(self.raw_data_path, "users/raw_users.csv"))
        self._save_to_csv(repos_data, os.path.join(self.raw_data_path, "repos/raw_repos.csv"))
        
        logger.success(f"Extraction complete! Saved {len(users_data)} users and {len(repos_data)} repos.")
        return users_data, repos_data

    def _save_to_csv(self, data: List[Dict], filepath: str):
        if not data:
            logger.warning(f"No data to save for {filepath}")
            return
            
        df = pd.DataFrame(data)
        df.to_csv(filepath, index=False, encoding='utf-8')
        logger.info(f"Data saved successfully to {filepath}")
