#!/usr/bin/env python3
"""
Weather Agent Script

A LangChain-based agent that searches for current weather information using DuckDuckGo Search
and provides summarized weather reports for specified cities.

Author: [Your Name]
Date: March 2026
"""

import asyncio
import sys
from typing import Optional, Dict, Any
import argparse

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import Tool
from langchain_duckduckgo_search import DuckDuckGoSearchRun
from langchain_core.messages import SystemMessage


class WeatherAgent:
    """
    A weather information agent that uses DuckDuckGo Search to find current weather data
    and LangChain for intelligent summarization.
    
    Attributes:
        llm: The language model for processing and summarization
        search_tool: DuckDuckGo search tool for web queries
        agent_executor: LangChain agent executor for running the agent
    """
    
    def __init__(self, openai_api_key: str, model_name: str = "gpt-3.5-turbo") -> None:
        """
        Initialize the WeatherAgent with OpenAI API key and model.
        
        Args:
            openai_api_key: OpenAI API key for language model access
            model_name: Name of the OpenAI model to use (default: gpt-3.5-turbo)
        
        Raises:
            ValueError: If openai_api_key is None or empty
        """
        if not openai_api_key:
            raise ValueError("OpenAI API key is required")
            
        self.llm = ChatOpenAI(
            model=model_name,
            api_key=openai_api_key,
            temperature=0.1  # Low temperature for consistent weather reports
        )
        
        # Initialize DuckDuckGo search tool
        self.search_tool = DuckDuckGoSearchRun()
        
        # Create tools for the agent
        tools = [
            Tool(
                name="weather_search",
                description="Search for current weather information for a specific city",
                func=self._search_weather
            )
        ]
        
        # Create the prompt template
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""You are a helpful weather assistant. When given a city name, 
            search for current weather information and provide a clear, concise summary including:
            - Current temperature
            - Weather conditions (sunny, cloudy, rainy, etc.)
            - Humidity
            - Wind speed/direction
            - Any weather alerts or warnings
            
            Always cite your sources and be specific about the current conditions."""),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}")
        ])
        
        # Create the agent
        agent = create_openai_tools_agent(self.llm, tools, prompt)
        self.agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    
    def _search_weather(self, city: str) -> str:
        """
        Search for weather information for a given city using DuckDuckGo.
        
        Args:
            city: Name of the city to search weather for
            
        Returns:
            Raw search results as a string
        """
        search_query = f"current weather in {city} today temperature conditions"
        return self.search_tool.run(search_query)
    
    async def get_weather_summary(self, city: str) -> Dict[str, Any]:
        """
        Get a comprehensive weather summary for the specified city.
        
        Args:
            city: Name of the city to get weather information for
            
        Returns:
            Dictionary containing weather summary and metadata
            
        Raises:
            Exception: If there's an error during weather search or summarization
        """
        try:
            # Construct the query for the agent
            query = f"Please provide a detailed weather summary for {city}, including current temperature, conditions, humidity, and wind information."
            
            # Execute the agent
            result = await self.agent_executor.ainvoke({"input": query})
            
            return {
                "city": city,
                "summary": result.get("output", ""),
                "success": True,
                "source": "DuckDuckGo Search + OpenAI"
            }
            
        except Exception as e:
            return {
                "city": city,
                "summary": f"Error retrieving weather information: {str(e)}",
                "success": False,
                "source": "Error"
            }
    
    def get_weather_summary_sync(self, city: str) -> Dict[str, Any]:
        """
        Synchronous wrapper for get_weather_summary.
        
        Args:
            city: Name of the city to get weather information for
            
        Returns:
            Dictionary containing weather summary and metadata
        """
        return asyncio.run(self.get_weather_summary(city))


def main() -> None:
    """
    Main function to run the weather agent from command line.
    
    Usage:
        python weather_agent.py "New York"
        python weather_agent.py "London" --api-key YOUR_API_KEY
    """
    parser = argparse.ArgumentParser(
        description="Get current weather information for any city using AI-powered search"
    )
    parser.add_argument(
        "city", 
        help="Name of the city to get weather for"
    )
    parser.add_argument(
        "--api-key", 
        help="OpenAI API key (can also be set via OPENAI_API_KEY environment variable)",
        default=None
    )
    parser.add_argument(
        "--model", 
        help="OpenAI model to use (default: gpt-3.5-turbo)",
        default="gpt-3.5-turbo"
    )
    
    args = parser.parse_args()
    
    # Get API key from argument or environment
    api_key = args.api_key
    if not api_key:
        import os
        api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("Error: OpenAI API key is required. Provide it via --api-key argument or OPENAI_API_KEY environment variable.")
        sys.exit(1)
    
    try:
        # Initialize the weather agent
        print(f"Initializing weather agent for {args.city}...")
        agent = WeatherAgent(openai_api_key=api_key, model_name=args.model)
        
        # Get weather summary
        print(f"Searching for weather information in {args.city}...")
        result = agent.get_weather_summary_sync(args.city)
        
        # Display results
        print("\n" + "="*60)
        print(f"Weather Summary for {result['city']}")
        print("="*60)
        print(f"Source: {result['source']}")
        print(f"Success: {result['success']}")
        print("\nSummary:")
        print("-"*40)
        print(result['summary'])
        print("-"*40)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
