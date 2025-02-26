import os
from mistralai import Mistral
from dotenv import load_dotenv
import sys
import textwrap
from github import Github
import json

# Load environment variables
load_dotenv()

# Configure Mistral and GitHub clients
mistral_api_key = os.getenv("MISTRAL_API_KEY")
github_token = os.getenv("GITHUB_TOKEN")
client = Mistral(api_key=mistral_api_key)
gh = Github(github_token)

# Define GitHub-related functions
tools = [
    {
        "type": "function",
        "function": {
            "name": "create_repository",
            "description": "Creates a new GitHub repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the repository"
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of the repository"
                    },
                    "private": {
                        "type": "boolean",
                        "description": "Whether the repository should be private"
                    }
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_repositories",
            "description": "Lists all repositories for a GitHub user",
            "parameters": {
                "type": "object",
                "properties": {
                    "username": {
                        "type": "string",
                        "description": "GitHub username"
                    }
                },
                "required": ["username"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_github_issue",
            "description": "Creates a new issue on GitHub repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_name": {
                        "type": "string",
                        "description": "Name of the repository (format: owner/repo)"
                    },
                    "title": {
                        "type": "string",
                        "description": "Title of the issue"
                    },
                    "body": {
                        "type": "string",
                        "description": "Body content of the issue"
                    }
                },
                "required": ["repo_name", "title", "body"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_repository_issues",
            "description": "Lists open issues in a GitHub repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_name": {
                        "type": "string",
                        "description": "Name of the repository (format: owner/repo)"
                    }
                },
                "required": ["repo_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "upload_file",
            "description": "Uploads a Python file to a GitHub repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_name": {
                        "type": "string",
                        "description": "Name of the repository (format: owner/repo)"
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Local path to the Python file"
                    },
                    "commit_message": {
                        "type": "string",
                        "description": "Commit message for the upload"
                    }
                },
                "required": ["repo_name", "file_path"]
            }
        }
    }
]

def create_repository(name: str, description: str = "", private: bool = False):
    """Creates a new GitHub repository"""
    try:
        user = gh.get_user()
        repo = user.create_repo(
            name=name,
            description=description,
            private=private
        )
        return f"Repository created successfully: {repo.html_url}"
    except Exception as e:
        return f"Error creating repository: {str(e)}"

def create_github_issue(repo_name: str, title: str, body: str):
    """Creates a new issue on GitHub"""
    try:
        repo = gh.get_repo(repo_name)
        issue = repo.create_issue(title=title, body=body)
        return f"Issue created successfully: {issue.html_url}"
    except Exception as e:
        return f"Error creating issue: {str(e)}"

def list_repository_issues(repo_name: str):
    """Lists open issues in a repository"""
    try:
        repo = gh.get_repo(repo_name)
        issues = repo.get_issues(state='open')
        return "\n".join([f"#{issue.number}: {issue.title}" for issue in issues])
    except Exception as e:
        return f"Error listing issues: {str(e)}"

def list_repositories(username: str):
    """Lists all repositories for a GitHub user"""
    try:
        user = gh.get_user(username)
        repos = user.get_repos()
        return "\n".join([f"â€¢ {repo.name}: {repo.description or 'No description'}" for repo in repos])
    except Exception as e:
        return f"Error listing repositories: {str(e)}"

def upload_file(repo_name: str, file_path: str, commit_message: str = "Add Python script"):
    """Uploads a Python file to a GitHub repository"""
    try:
        repo = gh.get_repo(repo_name)
        with open(file_path, 'r') as file:
            content = file.read()
        
        # Get the filename from the path
        file_name = os.path.basename(file_path)
        
        # Create or update file in repository
        repo.create_file(
            path=file_name,
            message=commit_message,
            content=content,
            branch="main"  # or 'master' depending on your default branch
        )
        return f"File {file_name} uploaded successfully to {repo_name}"
    except Exception as e:
        return f"Error uploading file: {str(e)}"

def get_ai_response(prompt):
    try:
        print("Sending request to Mistral...")
        response = client.chat.complete(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": prompt}],
            tools=tools,
            tool_choice="auto"
        )
        
        print("Response received:", response)
        
        if hasattr(response.choices[0].message, 'tool_calls') and response.choices[0].message.tool_calls:
            print("Tool call detected")
            tool_call = response.choices[0].message.tool_calls[0]
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            print(f"Executing {function_name} with args: {function_args}")
            
            if function_name == "upload_file":
                result = upload_file(**function_args)
            elif function_name == "create_repository":
                result = create_repository(**function_args)
            elif function_name == "list_repositories":
                result = list_repositories(**function_args)
            elif function_name == "create_github_issue":
                result = create_github_issue(**function_args)
            elif function_name == "list_repository_issues":
                result = list_repository_issues(**function_args)
            
            print("Function result:", result)
            return result
        
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return f"Error: {str(e)}"

def main():
    print("Welcome to Terminal LLM Chat (type 'quit' to exit)")
    print("-" * 50)
    
    while True:
        # Get user input
        user_input = input("\nYou: ")
        
        # Check if user wants to quit
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("\nGoodbye!")
            break
            
        # Get AI response
        print("\nAI: ", end="")
        response = get_ai_response(user_input)
        
        # Format and print response
        for line in textwrap.wrap(response, width=70):
            print(line)

if __name__ == "__main__":
    main()
