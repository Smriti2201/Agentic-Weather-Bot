#!/usr/bin/env python3
"""
Weather Agent Script

A simplified weather agent that uses DuckDuckGo Search to find current weather information
and OpenAI for intelligent summarization.

Author: [Your Name]
Date: March 2026
"""

import asyncio
import sys
import os
import requests
from typing import Optional, Dict, Any
import argparse

from langchain_openai import ChatOpenAI
from langchain_community.llms import Ollama
from langchain_core.prompts import ChatPromptTemplate
from ddgs import DDGS
import warnings

# Suppress deprecation warnings for cleaner output
warnings.filterwarnings("ignore", category=DeprecationWarning)


class WeatherAgent:
    """
    A weather information agent that uses DuckDuckGo Search to find current weather data
    and either OpenAI or Ollama for intelligent summarization.
    
    Attributes:
        llm: The language model for processing and summarization
        ddgs: DuckDuckGo search instance
        model_type: Type of model being used ('openai' or 'ollama')
    """
    
    @staticmethod
    def check_ollama_connection(model_name: str = "llama2") -> bool:
        """
        Check if Ollama is running and the specified model is available.
        
        Args:
            model_name: Name of the Ollama model to check
            
        Returns:
            True if Ollama is accessible and model is available, False otherwise
        """
        try:
            # Check if Ollama is running
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code != 200:
                return False
            
            # Check if the specific model is available
            models = response.json().get("models", [])
            model_names = [model["name"] for model in models]  # Use full name including tag
            
            if model_name not in model_names:
                print(f"Model '{model_name}' not found. Available models: {', '.join(model_names)}")
                print(f"Run: ollama pull {model_name}")
                return False
            
            return True
            
        except requests.exceptions.RequestException:
            return False
    
    def __init__(self, openai_api_key: Optional[str] = None, model_name: str = "gpt-3.5-turbo", use_ollama: bool = False, ollama_model: str = "llama2") -> None:
        """
        Initialize the WeatherAgent with either OpenAI or Ollama.
        
        Args:
            openai_api_key: OpenAI API key (required if use_ollama is False)
            model_name: Name of the OpenAI model to use (default: gpt-3.5-turbo)
            use_ollama: Whether to use Ollama instead of OpenAI (default: False)
            ollama_model: Name of the Ollama model to use (default: llama2)
        
        Raises:
            ValueError: If OpenAI API key is required but not provided
        """
        if use_ollama:
            # Check Ollama connection and model availability
            if not WeatherAgent.check_ollama_connection(ollama_model):
                raise ConnectionError(f"Cannot connect to Ollama or model '{ollama_model}' not available. Make sure Ollama is running and the model is downloaded.")
            
            self.llm = Ollama(model=ollama_model)
            self.model_type = "ollama"
        else:
            if not openai_api_key:
                raise ValueError("OpenAI API key is required when not using Ollama")
            self.llm = ChatOpenAI(
                model=model_name,
                api_key=openai_api_key,
                temperature=0.1  # Low temperature for consistent weather reports
            )
            self.model_type = "openai"
        
        # Initialize DuckDuckGo search
        self.ddgs = DDGS()
        
        # Create the summarization prompt
        self.prompt = ChatPromptTemplate.from_template("""
        You are a helpful weather assistant. Based on the following search results about weather in {city},
        provide a clear, concise summary including:
        - Current temperature
        - Weather conditions (sunny, cloudy, rainy, etc.)
        - Humidity
        - Wind speed/direction
        - Any weather alerts or warnings
        
        Search Results:
        {search_results}
        
        Please provide a comprehensive weather summary for {city}:
        """)
    
    def search_weather(self, city: str) -> str:
        """
        Search for weather information for a given city using DuckDuckGo.
        
        Args:
            city: Name of the city to search weather for
            
        Returns:
            Raw search results as a string
        """
        search_query = f"current weather in {city} today temperature conditions humidity wind"
        try:
            results = list(self.ddgs.text(search_query, max_results=5))
            if results:
                return "\n".join([f"{result['title']}: {result['body']}" for result in results])
            else:
                return f"No weather information found for {city}"
        except Exception as e:
            return f"Error searching for weather: {str(e)}"
    
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
            # Search for weather information
            search_results = self.search_weather(city)
            
            # Create the prompt chain
            chain = self.prompt | self.llm
            
            # Generate the summary
            response = await chain.ainvoke({
                "city": city,
                "search_results": search_results
            })
            
            return {
                "city": city,
                "summary": response.content if hasattr(response, 'content') else str(response),
                "search_results": search_results,
                "success": True,
                "source": f"DuckDuckGo Search + {self.model_type.upper()}"
            }
            
        except Exception as e:
            return {
                "city": city,
                "summary": f"Error retrieving weather information: {str(e)}",
                "search_results": "",
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
    parser.add_argument(
        "--use-ollama", 
        help="Use Ollama instead of OpenAI (requires Ollama to be running locally)",
        action="store_true"
    )
    parser.add_argument(
        "--ollama-model", 
        help="Ollama model to use (default: llama2)",
        default="llama2"
    )
    
    args = parser.parse_args()
    
    # Check if using Ollama
    if args.use_ollama:
        print("Using Ollama for local LLM processing...")
        api_key = None
    else:
        # Get API key from argument or environment
        api_key = args.api_key
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            print("Error: OpenAI API key is required when not using Ollama.")
            print("Either:")
            print("  1. Provide it via --api-key argument")
            print("  2. Set OPENAI_API_KEY environment variable")
            print("  3. Use --use-ollama flag for local processing")
            sys.exit(1)
    
    try:
        # Initialize the weather agent
        if args.use_ollama:
            print(f"Initializing weather agent for {args.city} with Ollama ({args.ollama_model})...")
            agent = WeatherAgent(use_ollama=True, ollama_model=args.ollama_model)
        else:
            print(f"Initializing weather agent for {args.city} with OpenAI ({args.model})...")
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
        
        if not result['success']:
            print(f"\nDebug Info - Search Results:")
            print(result.get('search_results', 'No search results available'))
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
