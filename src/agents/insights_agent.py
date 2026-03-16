import os
import sys
import json
import pandas as pd
from loguru import logger
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class InsightsAgent:
    """
    An autonomous agent that analyzes the Peruvian GitHub ecosystem data.
    It has access to tools (functions) to query the datasets and synthesize insights.
    """
    def __init__(self, model="gpt-4o-mini"):
        self.client = OpenAI()
        self.model = model
        
        # Load necessary data for tools
        base_path = "data/"
        try:
            self.users = pd.read_csv(os.path.join(base_path, "processed/users.csv"))
            self.metrics = pd.read_csv(os.path.join(base_path, "metrics/user_metrics.csv"))
            self.repos = pd.read_csv(os.path.join(base_path, "processed/repositories.csv"))
            self.classifications = pd.read_csv(os.path.join(base_path, "processed/classifications.csv"))
            
            with open(os.path.join(base_path, "metrics/ecosystem_metrics.json"), "r") as f:
                self.eco_metrics = json.load(f)
        except Exception as e:
            logger.error(f"Agent failed to load data: {e}")
            self.users = None

    def get_top_developers(self, limit=5, by="impact_score"):
        """Tool: Returns the top developers based on a specific metric."""
        if self.metrics is None:
            return "Error: Data not loaded."
        
        valid_sorts = ["impact_score", "h_index", "total_stars_received", "followers"]
        if by not in valid_sorts:
            by = "impact_score"
            
        top_devs = self.metrics.sort_values(by=by, ascending=False).head(limit)
        results = top_devs[['login', 'name', by, 'h_index', 'total_stars_received']].to_dict(orient="records")
        return json.dumps(results)

    def get_ecosystem_overview(self):
        """Tool: Returns a high-level summary of the Peruvian tech ecosystem."""
        if not hasattr(self, 'eco_metrics'):
            return "Error: Data not loaded."
        return json.dumps(self.eco_metrics)

    def get_top_industries(self, limit=5):
        """Tool: Returns the most common industry classifications (CIIU) in Peru."""
        if self.classifications is None:
            return "Error: Data not loaded."
        inds = self.classifications['industry_name'].value_counts().head(limit).reset_index()
        inds.columns = ['industry', 'repository_count']
        return inds.to_json(orient="records")
        
    def get_top_languages(self, limit=5):
        """Tool: Returns the most used programming languages in the scraped repositories."""
        if self.repos is None:
            return "Error: Data not loaded."
        langs = self.repos['language'].dropna().value_counts().head(limit).reset_index()
        langs.columns = ['language', 'repository_count']
        return langs.to_json(orient="records")

    def run(self, user_question: str) -> str:
        """
        Executes the agentic loop to answer a user's question using OpenAI Function Calling tools.
        """
        logger.info(f"Agent received task: {user_question}")
        
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_top_developers",
                    "description": "Get the top Peruvian developers based on impact_score, h_index, total_stars_received, or followers.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Number of developers to return (default 5, max 10)"
                            },
                            "by": {
                                "type": "string",
                                "enum": ["impact_score", "h_index", "total_stars_received", "followers"],
                                "description": "Metric to sort developers by"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_ecosystem_overview",
                    "description": "Get high-level summary metrics of the entire Peru GitHub ecosystem (total devs, totals repos, overall averages).",
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_top_industries",
                    "description": "Get the most dominant CIIU industry categories for software produced in Peru.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "limit": {"type": "integer"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_top_languages",
                    "description": "Get the most popular programming languages in Peru's open source community.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "limit": {"type": "integer"}
                        }
                    }
                }
            }
        ]
        
        system_prompt = (
            "You are the Peru GitHub Ecosystem AI Data Analyst. "
            "You must answer user questions about developers and repositories in Peru accurately. "
            "ALWAYS use the provided tools to query the data before answering. Never make up data or developers. "
            "If a tool provides the data, synthesize it clearly and professionally."
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_question}
        ]
        
        try:
            # First LLM call - Let it decide which tools to run
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )
            
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls
            
            # If AI didn't want to use any tools, return its direct response
            if not tool_calls:
                return response_message.content
                
            # If it decided to use tools, append its desire to messages and execute the tools
            messages.append(response_message)
            
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                
                logger.debug(f"Agent Action: Calling tool '{function_name}' with args {arguments}")
                
                # Execute mapped function
                if function_name == "get_top_developers":
                    function_response = self.get_top_developers(
                        limit=arguments.get("limit", 5), 
                        by=arguments.get("by", "impact_score")
                    )
                elif function_name == "get_ecosystem_overview":
                    function_response = self.get_ecosystem_overview()
                elif function_name == "get_top_industries":
                    function_response = self.get_top_industries(limit=arguments.get("limit", 5))
                elif function_name == "get_top_languages":
                    function_response = self.get_top_languages(limit=arguments.get("limit", 5))
                else:
                    function_response = "Error: Unknown logic requested."
                
                # Append tool result to the conversation
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": function_response,
                })
             
            # Second LLM call - AI synthesizes the answer from the tool results
            final_response = self.client.chat.completions.create(
                model=self.model,
                messages=messages
            )
            
            return final_response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Agent Loop Failed: {e}")
            return f"I encountered an error querying the knowledge base: {e}"
