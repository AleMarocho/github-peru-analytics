import os
import json
import pandas as pd
from typing import List, Dict, Any
from openai import OpenAI
from loguru import logger
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

class IndustryClassifier:
    def __init__(self, model: str = "gpt-4o-mini"):
        self.client = OpenAI() # Automatically uses OPENAI_API_KEY from environment
        self.model = model
        self.industries = {
            "A": "Agriculture, forestry and fishing",
            "B": "Mining and quarrying",
            "C": "Manufacturing",
            "D": "Electricity, gas, steam supply",
            "E": "Water supply; sewerage",
            "F": "Construction",
            "G": "Wholesale and retail trade",
            "H": "Transportation and storage",
            "I": "Accommodation and food services",
            "J": "Information and communication",
            "K": "Financial and insurance activities",
            "L": "Real estate activities",
            "M": "Professional, scientific activities",
            "N": "Administrative and support activities",
            "O": "Public administration and defense",
            "P": "Education",
            "Q": "Human health and social work",
            "R": "Arts, entertainment and recreation",
            "S": "Other service activities",
            "T": "Activities of households",
            "U": "Extraterritorial organizations"
        }

    @retry(
        # Removed retry_if_exception_type entirely so it allows exceptions like 401 to bubble up and fail fast!
        wait=wait_exponential(multiplier=1, min=2, max=20),
        stop=stop_after_attempt(5)
    )
    def classify_repository(
        self, name: str, description: str, readme: str, topics: list[str], language: str
    ) -> dict:
        """
        Classify a repository into an industry category based on the provided metadata.
        Returns: dict with keys: industry_code, industry_name, confidence, reasoning
        """
        # Ensure values are safely formatted string representations
        description_clean = str(description) if description and pd.notna(description) else 'No description'
        readme_clean = str(readme) if readme and pd.notna(readme) else 'No README'
        language_clean = str(language) if language and pd.notna(language) else 'Not specified'
        
        # Format topics correctly whether it's a list or a comma separated string
        if not topics or pd.isna(topics):
            topics_clean = 'None'
        elif isinstance(topics, list):
            topics_clean = ', '.join([str(t) for t in topics])
        else:
            topics_clean = str(topics)

        prompt = f"""Analyze this GitHub repository and classify it into ONE of the following industry categories based on its potential application or the industry it serves.

REPOSITORY INFORMATION:
- Name: {name}
- Description: {description_clean}
- Primary Language: {language_clean}
- Topics: {topics_clean}
- README (first 2000 chars): {readme_clean[:2000]}

INDUSTRY CATEGORIES:
{json.dumps(self.industries, indent=2)}

INSTRUCTIONS:
1. Analyze the repository's purpose, functionality, and potential use cases
2. Consider what industry would most benefit from or use this software
3. If it's a general-purpose tool (e.g., utility library), classify based on the most likely industry application
4. If truly generic (e.g., "hello world"), use "J" (Information and communication)

Respond in JSON format:
{{
  "industry_code": "X",
  "industry_name": "Full industry name",
  "confidence": "high|medium|low",
  "reasoning": "Brief explanation of why this classification was chosen"
}}
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at classifying software projects by industry. Always respond with valid JSON."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            # Ensure the required keys are present
            return {
                "industry_code": result.get("industry_code", "J"),
                "industry_name": result.get("industry_name", self.industries.get(result.get("industry_code", "J"))),
                "confidence": result.get("confidence", "low"),
                "reasoning": result.get("reasoning", "Fallback due to missing fields in response")
            }
        except Exception as e:
            logger.error(f"Error classifying {name}: {e}")
            raise e

    def batch_classify(self, repositories: list[dict], batch_size: int = 10) -> list[dict]:
        """
        Classify multiple repositories. Iterates sequentially and handles AI calls.
        """
        results = []
        total = len(repositories)
        logger.info(f"Starting batch classification of {total} repositories.")
        
        for idx, repo in enumerate(repositories):
            try:
                classification = self.classify_repository(
                    name=repo.get("name", ""),
                    description=repo.get("description", ""),
                    readme=repo.get("readme", ""),
                    topics=repo.get("topics", ""),
                    language=repo.get("language", "")
                )
                
                results.append({
                    "repo_id": repo["id"],
                    "repo_name": repo["name"],
                    **classification
                })
                
                if (idx + 1) % batch_size == 0 or (idx + 1) == total:
                    logger.info(f"Classified {idx + 1}/{total} repositories...")
                    
            except Exception as e:
                logger.error(f"Failed to classify repo {repo.get('name')} entirely: {e}")
                # Append a default classification so the dataframe aligns
                results.append({
                    "repo_id": repo.get("id"),
                    "repo_name": repo.get("name"),
                    "industry_code": "J",
                    "industry_name": "Information and communication",
                    "confidence": "low",
                    "reasoning": "Error during API call."
                })
                
        return results
