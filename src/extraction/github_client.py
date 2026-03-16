import os
import time
import requests
from typing import List, Dict, Any
from loguru import logger
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from dotenv import load_dotenv

load_dotenv()

class GitHubRateLimitError(Exception):
    """Exception raised when GitHub API rate limit is exceeded."""
    pass

class GitHubClient:
    """Client for interacting with the GitHub REST API securely and efficiently."""
    
    BASE_URL = "https://api.github.com"
    
    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN")
        if not self.token:
            logger.error("GITHUB_TOKEN is missing in the environment variables.")
            raise ValueError("GITHUB_TOKEN is required.")
            
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
    
    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(5),
        retry=retry_if_exception_type((requests.exceptions.RequestException, GitHubRateLimitError))
    )
    def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Make an HTTP GET request to the GitHub API with retry logic and rate limit handling.
        """
        if params is None:
            params = {}
            
        url = f"{self.BASE_URL}/{endpoint}"
        logger.debug(f"Requesting: {url}")
        
        response = requests.get(url, headers=self.headers, params=params)
        
        # Check for rate limiting
        if response.status_code == 403 and "rate limit exceeded" in response.text.lower():
            reset_time = int(response.headers.get("X-RateLimit-Reset", time.time() + 60))
            sleep_duration = max(reset_time - time.time(), 0) + 1
            logger.warning(f"Rate limit exceeded. Sleeping for {sleep_duration:.2f} seconds...")
            time.sleep(sleep_duration)
            raise GitHubRateLimitError("Rate limit exceeded. Retrying after cool-down.")
            
        response.raise_for_status()
        return response.json()

    def search_users(self, location: str, per_page: int = 100, max_users: int = 150) -> List[Dict[str, Any]]:
        """
        Search for users based on location.
        """
        logger.info(f"Searching for users in {location}...")
        users = []
        page = 1
        
        while len(users) < max_users:
            query = f"location:{location} type:user"
            params = {
                "q": query,
                "per_page": per_page,
                "page": page
            }
            
            try:
                data = self._make_request("search/users", params=params)
                items = data.get("items", [])
                
                if not items:
                    logger.info("No more users found.")
                    break
                    
                users.extend(items)
                logger.info(f"Fetched {len(items)} users from page {page}. Total collected: {len(users)}")
                
                # Handling pagination limit of GitHub search API (1000 results max)
                if len(users) >= data.get("total_count", 0):
                    break
                    
                page += 1
                
            except Exception as e:
                logger.error(f"Error fetching users: {e}")
                break
                
        return users[:max_users]

    def get_user_repositories(self, username: str) -> List[Dict[str, Any]]:
        """
        Fetch all public repositories for a specific user.
        """
        logger.debug(f"Fetching repositories for user: {username}")
        repos = []
        page = 1
        
        while True:
            params = {
                "per_page": 100,
                "page": page,
                "type": "owner"
            }
            
            try:
                data = self._make_request(f"users/{username}/repos", params=params)
                if not data:
                    break
                    
                repos.extend(data)
                page += 1
                
            except Exception as e:
                logger.error(f"Error fetching repos for {username}: {e}")
                break
                
        return repos
        
    def get_repository_readme(self, owner: str, repo: str) -> str:
        """
        Fetch the README content for a specific repository.
        """
        try:
            headers = self.headers.copy()
            headers["Accept"] = "application/vnd.github.raw+json" # Request raw content
            url = f"{self.BASE_URL}/repos/{owner}/{repo}/readme"
            
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.text
            elif response.status_code == 404:
                return "" # No README found
            else:
                response.raise_for_status()
                
        except Exception as e:
            logger.debug(f"Failed to fetch README for {owner}/{repo}: {e}")
            return ""
