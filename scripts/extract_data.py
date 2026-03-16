import sys
import os
from loguru import logger

# Add project root to path so we can import src module
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

from src.extraction.user_extractor import DataExtractor

def main():
    logger.info("Initializing Data Extractor...")
    extractor = DataExtractor(raw_data_path="data/raw/")
    
    # We set max_repos_target to 1050 to ensure we have a safe margin above the required 1000 repos
    logger.info("Starting extraction to collect at least 1000 repositories from Peru...")
    extractor.extract_peru_ecosystem(max_repos_target=1050)

if __name__ == "__main__":
    main()
