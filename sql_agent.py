#!/usr/bin/env python3
"""
SQL Agentic Architect

A sophisticated ReAct-based SQL agent that demonstrates Cornell-level database intelligence.
Uses local Ollama for private, intelligent SQL generation and execution.

Author: [Your Name]
Date: March 2026
"""

import asyncio
import sys
import os
import sqlite3
import json
import re
from typing import Optional, Dict, Any, List, Tuple
import argparse
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_community.llms import Ollama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
import warnings

# Suppress deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)


class SQLDatabaseToolkit:
    """
    Advanced database toolkit for schema analysis and SQL execution.
    
    Attributes:
        db_path: Path to SQLite database
        schema_cache: Cached schema information
    """
    
    def __init__(self, db_path: str) -> None:
        """
        Initialize the database toolkit.
        
        Args:
            db_path: Path to SQLite database file
            
        Raises:
            FileNotFoundError: If database doesn't exist
            sqlite3.Error: If database connection fails
        """
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database not found: {db_path}")
        
        self.db_path = db_path
        self.schema_cache = self._analyze_schema()
    
    def _analyze_schema(self) -> Dict[str, Any]:
        """
        Perform comprehensive schema analysis.
        
        Returns:
            Detailed schema information including tables, columns, relationships, and statistics
        """
        schema = {
            "tables": {},
            "relationships": [],
            "statistics": {},
            "sample_data": {}
        }
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get all user tables
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                    ORDER BY name
                """)
                tables = [row[0] for row in cursor.fetchall()]
                
                for table in tables:
                    # Table structure
                    cursor.execute(f"PRAGMA table_info({table})")
                    columns = cursor.fetchall()
                    
                    # Foreign keys
                    cursor.execute(f"PRAGMA foreign_key_list({table})")
                    foreign_keys = cursor.fetchall()
                    
                    # Indexes
                    cursor.execute(f"PRAGMA index_list({table})")
                    indexes = cursor.fetchall()
                    
                    # Row count
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    row_count = cursor.fetchone()[0]
                    
                    # Sample data (first 3 rows)
                    cursor.execute(f"SELECT * FROM {table} LIMIT 3")
                    sample_rows = cursor.fetchall()
                    column_names = [desc[0] for desc in cursor.description] if cursor.description else []
                    
                    schema["tables"][table] = {
                        "columns": [
                            {
                                "cid": col[0],
                                "name": col[1],
                                "type": col[2],
                                "not_null": bool(col[3]),
                                "default_value": col[4],
                                "primary_key": bool(col[5])
                            }
                            for col in columns
                        ],
                        "foreign_keys": [
                            {
                                "column": fk[3],
                                "references_table": fk[2],
                                "references_column": fk[4]
                            }
                            for fk in foreign_keys
                        ],
                        "indexes": [
                            {
                                "name": idx[1],
                                "unique": bool(idx[2]),
                                "origin": idx[3]
                            }
                            for idx in indexes
                        ],
                        "row_count": row_count
                    }
                    
                    schema["sample_data"][table] = {
                        "columns": column_names,
                        "rows": sample_rows
                    }
                    
                    # Add to relationships
                    for fk in foreign_keys:
                        schema["relationships"].append({
                            "from_table": table,
                            "from_column": fk[3],
                            "to_table": fk[2],
                            "to_column": fk[4]
                        })
                
                # Database statistics
                cursor.execute("SELECT COUNT(DISTINCT name) FROM sqlite_master WHERE type='table'")
                schema["statistics"]["table_count"] = cursor.fetchone()[0]
                
                cursor.execute("SELECT SUM(COUNT(*)) FROM (SELECT COUNT(*) FROM sqlite_master WHERE type='table' UNION ALL SELECT COUNT(*) FROM pragma_table_list())")
                
        except sqlite3.Error as e:
            raise sqlite3.Error(f"Schema analysis failed: {str(e)}")
        
        return schema
    
    def get_schema_for_llm(self) -> str:
        """
        Generate LLM-optimized schema description.
        
        Returns:
            Formatted schema string for prompt engineering
        """
        description = "DATABASE SCHEMA ANALYSIS:\n\n"
        
        for table_name, table_info in self.schema_cache["tables"].items():
            description += f"📊 Table: {table_name} ({table_info['row_count']} rows)\n"
            
            # Columns
            description += "   Columns:\n"
            for col in table_info["columns"]:
                pk_marker = " 🔑" if col["primary_key"] else ""
                null_marker = " NULL" if not col["not_null"] else " NOT NULL"
                description += f"      • {col['name']}: {col['type']}{null_marker}{pk_marker}\n"
            
            # Sample data
            if table_name in self.schema_cache["sample_data"]:
                sample = self.schema_cache["sample_data"][table_name]
                if sample["rows"]:
                    description += "   Sample Data:\n"
                    for row in sample["rows"][:2]:  # Show only 2 rows
                        description += f"      {dict(zip(sample['columns'], row))}\n"
            
            description += "\n"
        
        # Relationships
        if self.schema_cache["relationships"]:
            description += "🔗 Relationships:\n"
            for rel in self.schema_cache["relationships"]:
                description += f"   {rel['from_table']}.{rel['from_column']} → {rel['to_table']}.{rel['to_column']}\n"
        
        return description
    
    def execute_sql_safely(self, sql_query: str) -> Tuple[bool, List[Tuple], str]:
        """
        Execute SQL with comprehensive safety checks.
        
        Args:
            sql_query: SQL query to execute
            
        Returns:
            Tuple of (success, results, error_message)
        """
        try:
            # Security: Check for dangerous operations
            dangerous_patterns = [
                r'\bDROP\b', r'\bDELETE\b', r'\bUPDATE\b', r'\bINSERT\b',
                r'\bALTER\b', r'\bCREATE\b', r'\bTRUNCATE\b'
            ]
            
            sql_upper = sql_query.upper()
            for pattern in dangerous_patterns:
                if re.search(pattern, sql_upper) and 'SELECT' not in sql_upper:
                    return False, [], f"🚫 Dangerous operation detected: {pattern}"
            
            # Execute query
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(sql_query)
                results = cursor.fetchall()
                
                # Get column names for better formatting
                column_names = [desc[0] for desc in cursor.description] if cursor.description else []
                
                return True, results, ""
        
        except sqlite3.Error as e:
            return False, [], f"❌ SQL Error: {str(e)}"
        except Exception as e:
            return False, [], f"❌ Execution Error: {str(e)}"


class SQLReActAgent:
    """
    ReAct-based SQL Agent with Think-Act-Observe-Answer loop.
    
    Attributes:
        llm: Language model for reasoning
        toolkit: Database toolkit
        conversation_history: Chat history for context
    """
    
    def __init__(self, db_path: str, use_ollama: bool = True, ollama_model: str = "gemma3:4b",
                 openai_api_key: Optional[str] = None, openai_model: str = "gpt-3.5-turbo") -> None:
        """
        Initialize the ReAct SQL Agent.
        
        Args:
            db_path: Path to database
            use_ollama: Whether to use Ollama (local) or OpenAI
            ollama_model: Ollama model name
            openai_api_key: OpenAI API key (if using OpenAI)
            openai_model: OpenAI model name
        """
        self.toolkit = SQLDatabaseToolkit(db_path)
        self.conversation_history = []
        
        # Initialize LLM
        if use_ollama:
            if not self._check_ollama_connection(ollama_model):
                raise ConnectionError(f"❌ Ollama not available or model '{ollama_model}' not found")
            self.llm = Ollama(model=ollama_model)
            self.model_type = "Ollama"
        else:
            if not openai_api_key:
                raise ValueError("❌ OpenAI API key required")
            self.llm = ChatOpenAI(model=openai_model, api_key=openai_api_key, temperature=0.1)
            self.model_type = "OpenAI"
        
        # Create ReAct prompts
        self.thinking_prompt = ChatPromptTemplate.from_template("""
        You are an expert database analyst. Analyze the user's question and the database schema to determine the best approach.
        
        DATABASE SCHEMA:
        {schema}
        
        USER QUESTION: {question}
        
        Think step by step:
        1. What information is the user asking for?
        2. Which tables contain this information?
        3. What joins or operations are needed?
        4. What SQL query would answer this question?
        
        Provide your analysis and the SQL query:
        """)
        
        self.verification_prompt = ChatPromptTemplate.from_template("""
        You are a SQL expert. Verify if this SQL query is correct and safe to execute.
        
        Question: {question}
        Proposed SQL: {sql_query}
        Schema: {schema}
        
        Check for:
        1. Syntax correctness
        2. Logical correctness (answers the question)
        3. Safety (no dangerous operations)
        4. Efficiency
        
        Respond with either "APPROVED" if the query is good, or provide corrections:
        """)
        
        self.interpretation_prompt = ChatPromptTemplate.from_template("""
        You are a data analyst providing insights to a Cornell business manager.
        
        Question: {question}
        SQL Query: {sql_query}
        Results: {results}
        
        Provide a clear, professional answer in business terms. Include:
        1. Direct answer to the question
        2. Key insights or patterns
        3. Business implications if relevant
        
        Answer:
        """)
    
    @staticmethod
    def _check_ollama_connection(model_name: str) -> bool:
        """Verify Ollama is running and model is available."""
        try:
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code != 200:
                return False
            
            models = response.json().get("models", [])
            available_models = [model["name"] for model in models]
            return model_name in available_models
        except:
            return False
    
    async def think(self, question: str) -> Dict[str, Any]:
        """
        THINK phase: Analyze question and generate SQL.
        
        Args:
            question: User's natural language question
            
        Returns:
            Dictionary with analysis and proposed SQL
        """
        schema = self.toolkit.get_schema_for_llm()
        
        chain = self.thinking_prompt | self.llm
        response = await chain.ainvoke({
            "schema": schema,
            "question": question
        })
        
        content = response.content if hasattr(response, 'content') else str(response)
        
        # Extract SQL query from response
        sql_match = re.search(r'```sql\s*(.*?)\s*```', content, re.IGNORECASE | re.DOTALL)
        if sql_match:
            sql_query = sql_match.group(1).strip()
        else:
            # Look for SQL in the text
            lines = content.split('\n')
            sql_lines = [line.strip() for line in lines if line.strip().upper().startswith(('SELECT', 'WITH'))]
            sql_query = '\n'.join(sql_lines) if sql_lines else content.strip()
        
        return {
            "question": question,
            "analysis": content,
            "proposed_sql": sql_query,
            "schema": schema
        }
    
    async def verify(self, question: str, sql_query: str, schema: str) -> Tuple[bool, str]:
        """
        VERIFY phase: Check SQL correctness and safety.
        
        Args:
            question: Original question
            sql_query: Proposed SQL query
            schema: Database schema
            
        Returns:
            Tuple of (is_approved, corrected_sql_or_reason)
        """
        chain = self.verification_prompt | self.llm
        response = await chain.ainvoke({
            "question": question,
            "sql_query": sql_query,
            "schema": schema
        })
        
        content = response.content if hasattr(response, 'content') else str(response)
        
        if "APPROVED" in content.upper():
            return True, sql_query
        else:
            # Extract corrected SQL if present
            sql_match = re.search(r'```sql\s*(.*?)\s*```', content, re.IGNORECASE | re.DOTALL)
            if sql_match:
                corrected_sql = sql_match.group(1).strip()
                return False, corrected_sql
            return False, content
    
    async def act(self, sql_query: str) -> Tuple[bool, List[Tuple], str]:
        """
        ACT phase: Execute the SQL query.
        
        Args:
            sql_query: SQL query to execute
            
        Returns:
            Tuple of (success, results, error_message)
        """
        return self.toolkit.execute_sql_safely(sql_query)
    
    async def observe(self, question: str, sql_query: str, results: List[Tuple]) -> str:
        """
        OBSERVE phase: Interpret the results.
        
        Args:
            question: Original question
            sql_query: Executed SQL query
            results: Query results
            
        Returns:
            Interpreted answer in natural language
        """
        # Format results for better readability
        if results:
            # Get column names from the toolkit
            try:
                with sqlite3.connect(self.toolkit.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(sql_query)
                    column_names = [desc[0] for desc in cursor.description] if cursor.description else []
                    
                    formatted_results = []
                    for row in results:
                        if column_names:
                            formatted_results.append(dict(zip(column_names, row)))
                        else:
                            formatted_results.append(row)
                    
                    results_str = json.dumps(formatted_results, indent=2, default=str)
            except:
                results_str = str(results)
        else:
            results_str = "No results returned"
        
        chain = self.interpretation_prompt | self.llm
        response = await chain.ainvoke({
            "question": question,
            "sql_query": sql_query,
            "results": results_str
        })
        
        return response.content if hasattr(response, 'content') else str(response)
    
    async def react_loop(self, question: str, max_iterations: int = 3) -> Dict[str, Any]:
        """
        Complete ReAct loop: Think -> Verify -> Act -> Observe -> Answer.
        
        Args:
            question: User's natural language question
            max_iterations: Maximum verification iterations
            
        Returns:
            Complete result with all phases
        """
        print(f"🤔 Starting ReAct analysis for: '{question}'")
        
        # THINK phase
        print("   🧠 Thinking...")
        thinking_result = await self.think(question)
        proposed_sql = thinking_result["proposed_sql"]
        
        print(f"   💡 Proposed SQL:\n      {proposed_sql}")
        
        # VERIFY phase (with retry)
        current_sql = proposed_sql
        for iteration in range(max_iterations):
            print(f"   🔍 Verifying (attempt {iteration + 1})...")
            approved, corrected = await self.verify(question, current_sql, thinking_result["schema"])
            
            if approved:
                print("   ✅ SQL approved!")
                break
            else:
                print(f"   ⚠️  SQL needs correction...")
                current_sql = corrected
                if iteration == max_iterations - 1:
                    print("   ⏰ Max verification attempts reached")
        
        # ACT phase
        print("   ⚡ Executing SQL...")
        success, results, error = await self.act(current_sql)
        
        if not success:
            return {
                "question": question,
                "success": False,
                "error": error,
                "sql_query": current_sql,
                "answer": f"❌ Failed to execute SQL: {error}"
            }
        
        print(f"   📊 Query returned {len(results)} rows")
        
        # OBSERVE phase
        print("   🎯 Interpreting results...")
        answer = await self.observe(question, current_sql, results)
        
        print("   ✅ Analysis complete!")
        
        return {
            "question": question,
            "success": True,
            "sql_query": current_sql,
            "results": results,
            "answer": answer,
            "model_used": self.model_type,
            "phases": {
                "thinking": thinking_result["analysis"],
                "verification": "Approved",
                "execution": f"{len(results)} rows returned",
                "interpretation": answer
            }
        }
    
    def query_sync(self, question: str) -> Dict[str, Any]:
        """Synchronous wrapper for the ReAct loop."""
        return asyncio.run(self.react_loop(question))


def main() -> None:
    """Main function for the SQL Agent CLI."""
    parser = argparse.ArgumentParser(
        description="Cornell Store SQL Agent - ReAct-based Database Intelligence"
    )
    parser.add_argument(
        "question",
        nargs='?',
        help="Natural language question about the database"
    )
    parser.add_argument(
        "--db",
        help="Path to database file",
        default="cornell_store.db"
    )
    parser.add_argument(
        "--use-ollama",
        help="Use local Ollama model (default)",
        action="store_true",
        default=True
    )
    parser.add_argument(
        "--ollama-model",
        help="Ollama model to use",
        default="gemma3:4b"
    )
    parser.add_argument(
        "--use-openai",
        help="Use OpenAI instead of Ollama",
        action="store_true"
    )
    parser.add_argument(
        "--api-key",
        help="OpenAI API key",
        default=None
    )
    parser.add_argument(
        "--openai-model",
        help="OpenAI model",
        default="gpt-3.5-turbo"
    )
    
    args = parser.parse_args()
    
    # Handle question requirement
    if not args.question:
        print("❌ Error: Question is required")
        print("Usage examples:")
        print(f"  python {sys.argv[0]} \"What are our top selling products?\"")
        print(f"  python {sys.argv[0]} \"Show sales by category\" --db cornell_store.db")
        print(f"  python {sys.argv[0]} --help")
        sys.exit(1)
    
    # Check database
    if not os.path.exists(args.db):
        print(f"❌ Database not found: {args.db}")
        print(f"💡 Create it first: python setup_db.py --db-path {args.db}")
        sys.exit(1)
    
    try:
        # Initialize agent
        if args.use_openai:
            print("🌐 Using OpenAI...")
            if not args.api_key:
                args.api_key = os.getenv("OPENAI_API_KEY")
            if not args.api_key:
                print("❌ OpenAI API key required")
                sys.exit(1)
            
            agent = SQLReActAgent(
                db_path=args.db,
                use_ollama=False,
                openai_api_key=args.api_key,
                openai_model=args.openai_model
            )
        else:
            print("🏠 Using local Ollama...")
            agent = SQLReActAgent(
                db_path=args.db,
                use_ollama=True,
                ollama_model=args.ollama_model
            )
        
        # Execute ReAct loop
        print(f"\n🚀 Starting SQL Agent Analysis")
        print("=" * 60)
        
        result = agent.query_sync(args.question)
        
        # Display results
        print("\n" + "=" * 80)
        print("🎯 SQL AGENT RESULTS")
        print("=" * 80)
        print(f"❓ Question: {result['question']}")
        print(f"🤖 Model: {result.get('model_used', 'Unknown')}")
        print(f"✅ Success: {result['success']}")
        print(f"💾 SQL Query:\n   {result['sql_query']}")
        
        if result['success']:
            print(f"\n📊 Results ({len(result.get('results', []))} rows):")
            for i, row in enumerate(result.get('results', [])[:5]):  # Show first 5 rows
                print(f"   {i+1}: {row}")
            if len(result.get('results', [])) > 5:
                print(f"   ... and {len(result.get('results', [])) - 5} more rows")
            
            print(f"\n💡 Answer:")
            print("-" * 60)
            print(result['answer'])
            print("-" * 60)
        else:
            print(f"\n❌ Error: {result.get('error', 'Unknown error')}")
            print(f"💬 Response: {result.get('answer', 'No answer available')}")
        
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Agent failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
