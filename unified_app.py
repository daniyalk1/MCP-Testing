import os
from mistralai import Mistral
from dotenv import load_dotenv
import sys
import textwrap
from github import Github
from atlassian import Jira, Confluence
import json
import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Configure logging
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.basicConfig(
    level=logging.ERROR,
    format='%(levelname)s: %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize API clients
mistral_api_key = os.getenv("MISTRAL_API_KEY")
github_token = os.getenv("GITHUB_TOKEN")
jira_url = os.getenv("JIRA_URL")
confluence_url = os.getenv("CONFLUENCE_URL")
atlassian_username = os.getenv("ATLASSIAN_USERNAME")
atlassian_api_token = os.getenv("ATLASSIAN_TOKEN")
slack_token = os.getenv("SLACK_API_TOKEN")

client = Mistral(api_key=mistral_api_key)
gh = Github(github_token)
jira = Jira(
    url=f"https://{jira_url}",
    username=atlassian_username,
    password=atlassian_api_token,
    cloud=True
)
confluence = Confluence(
    url=f"https://{confluence_url}",
    username=atlassian_username,
    password=atlassian_api_token,
    cloud=True
)
slack_client = WebClient(token=slack_token)

# Define all tools
tools = [
    # GitHub Tools
    {
        "type": "function",
        "function": {
            "name": "create_repository",
            "description": "Creates a new GitHub repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name of the repository"},
                    "description": {"type": "string", "description": "Description of the repository"},
                    "private": {"type": "boolean", "description": "Whether the repository should be private"}
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
                    "username": {"type": "string", "description": "GitHub username"}
                },
                "required": ["username"]
            }
        }
    },
    # Jira Tools
    {
        "type": "function",
        "function": {
            "name": "create_jira_issue",
            "description": "Creates a new Jira issue",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_key": {"type": "string", "description": "Project key (e.g., 'PROJ')"},
                    "summary": {"type": "string", "description": "Issue summary/title"},
                    "description": {"type": "string", "description": "Issue description"},
                    "issue_type": {"type": "string", "description": "Type of issue", "default": "Task"}
                },
                "required": ["project_key", "summary"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_jira_projects",
            "description": "Lists all available Jira projects",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    # Confluence Tools
    {
        "type": "function",
        "function": {
            "name": "create_confluence_page",
            "description": "Creates a new Confluence page",
            "parameters": {
                "type": "object",
                "properties": {
                    "space_key": {"type": "string", "description": "Space key"},
                    "title": {"type": "string", "description": "Page title"},
                    "content": {"type": "string", "description": "Page content"}
                },
                "required": ["space_key", "title", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_confluence_spaces",
            "description": "Lists all available Confluence spaces",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    # Slack Tools
    {
        "type": "function",
        "function": {
            "name": "send_slack_message",
            "description": "Sends a message to a Slack channel or DM",
            "parameters": {
                "type": "object",
                "properties": {
                    "channel": {
                        "type": "string",
                        "description": "Channel name (e.g., '#random') or ID"
                    },
                    "text": {
                        "type": "string",
                        "description": "Message text to send"
                    }
                },
                "required": ["channel", "text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "upload_file_to_slack",
            "description": "Uploads a file to Slack",
            "parameters": {
                "type": "object",
                "properties": {
                    "channels": {
                        "type": "string",
                        "description": "Channel name (e.g., '#random') or ID"
                    },
                    "filepath": {
                        "type": "string",
                        "description": "Local path to the file"
                    }
                },
                "required": ["channels", "filepath"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "slack_get_thread_replies",
            "description": "Get all replies in a message thread",
            "parameters": {
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "The channel containing the thread"
                    },
                    "thread_ts": {
                        "type": "string",
                        "description": "Timestamp of the parent message"
                    }
                },
                "required": ["channel_id", "thread_ts"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "slack_get_users",
            "description": "Get list of workspace users",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum users to return",
                        "default": 100
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "slack_get_user_profile",
            "description": "Get detailed profile information for a specific user",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "The user's ID"
                    }
                },
                "required": ["user_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "slack_list_channels",
            "description": "List public channels in the workspace",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of channels to return (max: 200)",
                        "default": 100
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "slack_post_message",
            "description": "Post a new message to a Slack channel",
            "parameters": {
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "The ID of the channel to post to"
                    },
                    "text": {
                        "type": "string",
                        "description": "The message text to post"
                    }
                },
                "required": ["channel_id", "text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "slack_reply_to_thread",
            "description": "Reply to a specific message thread",
            "parameters": {
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "The channel containing the thread"
                    },
                    "thread_ts": {
                        "type": "string",
                        "description": "Timestamp of the parent message"
                    },
                    "text": {
                        "type": "string",
                        "description": "The reply text"
                    }
                },
                "required": ["channel_id", "thread_ts", "text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "slack_add_reaction",
            "description": "Add an emoji reaction to a message",
            "parameters": {
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "The channel containing the message"
                    },
                    "timestamp": {
                        "type": "string",
                        "description": "Message timestamp to react to"
                    },
                    "reaction": {
                        "type": "string",
                        "description": "Emoji name without colons"
                    }
                },
                "required": ["channel_id", "timestamp", "reaction"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "slack_get_channel_history",
            "description": "Get recent messages from a channel",
            "parameters": {
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "The channel ID"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of messages to retrieve",
                        "default": 10
                    }
                },
                "required": ["channel_id"]
            }
        }
    }
]

# GitHub functions
def create_repository(name: str, description: str = "", private: bool = False):
    try:
        user = gh.get_user()
        repo = user.create_repo(name=name, description=description, private=private)
        return f"Repository created: {repo.html_url}"
    except Exception as e:
        return f"Error: {str(e)}"

def list_repositories(username: str):
    try:
        user = gh.get_user(username)
        repos = user.get_repos()
        return "\n".join([f"• {repo.name}: {repo.description or 'No description'}" for repo in repos])
    except Exception as e:
        return f"Error: {str(e)}"

# Jira functions
def create_jira_issue(project_key: str, summary: str, description: str = "", issue_type: str = "Task"):
    try:
        issue = jira.create_issue(
            fields={
                'project': {'key': project_key},
                'summary': summary,
                'description': description,
                'issuetype': {'name': issue_type}
            }
        )
        return f"Issue created: {issue['key']}"
    except Exception as e:
        return f"Error: {str(e)}"

def list_jira_projects():
    try:
        projects = jira.projects()
        return "\n".join([f"• {project['key']}: {project.get('name', 'No name')}" for project in projects])
    except Exception as e:
        return f"Error: {str(e)}"

# Confluence functions
def create_confluence_page(space_key: str, title: str, content: str):
    try:
        page = confluence.create_page(
            space=space_key,
            title=title,
            body=content,
            representation='storage'
        )
        return f"Page created in space {space_key}"
    except Exception as e:
        return f"Error: {str(e)}"

def list_confluence_spaces():
    try:
        spaces = confluence.get_all_spaces()
        return "\n".join([f"• {space['key']}: {space['name']}" for space in spaces['results']])
    except Exception as e:
        return f"Error: {str(e)}"

# Slack functions
def send_slack_message(channel: str, text: str):
    """Sends a message to a Slack channel or DM"""
    try:
        # Handle DM channels (starting with 'D')
        if channel.startswith('D'):
            # For DMs, we need to open a conversation first
            conversation = slack_client.conversations_open(users=[channel])
            if conversation['ok']:
                channel_id = conversation['channel']['id']
            else:
                return f"Error opening conversation: {conversation.get('error', 'Unknown error')}"
        else:
            channel_id = channel

        # Send the message
        response = slack_client.chat_postMessage(
            channel=channel_id,
            text=text
        )
        
        if response['ok']:
            return f"Message sent successfully"
        else:
            return f"Error sending message: {response.get('error', 'Unknown error')}"
            
    except SlackApiError as e:
        error = e.response['error']
        if error == 'channel_not_found':
            return "Error: Channel or user not found. Please check the channel ID or user ID."
        elif error == 'not_in_channel':
            return "Error: Bot is not in this channel. Please add the bot to the channel first."
        else:
            return f"Slack API Error: {error}"
    except Exception as e:
        return f"Error: {str(e)}"

def upload_file_to_slack(channels: str, filepath: str):
    """Uploads a file to Slack"""
    try:
        response = slack_client.files_upload(
            channels=channels,
            file=filepath
        )
        return f"File uploaded to {channels}"
    except SlackApiError as e:
        return f"Error: {str(e)}"

def slack_get_thread_replies(channel_id: str, thread_ts: str):
    """Gets all replies in a message thread"""
    try:
        result = slack_client.conversations_replies(
            channel=channel_id,
            ts=thread_ts
        )
        if result['ok']:
            replies = [f"[{m['ts']}] {m.get('user', 'Unknown')}: {m['text']}" 
                      for m in result['messages']]
            return "\n".join(replies)
        return f"Error getting replies: {result.get('error', 'Unknown error')}"
    except SlackApiError as e:
        return f"Error: {str(e)}"

def slack_get_users(limit: int = 100):
    """Gets list of workspace users"""
    try:
        result = slack_client.users_list(limit=min(limit, 200))
        if result['ok']:
            users = [f"• {u['name']} ({u['id']})" for u in result['members']]
            return "\n".join(users)
        return f"Error listing users: {result.get('error', 'Unknown error')}"
    except SlackApiError as e:
        return f"Error: {str(e)}"

def slack_get_user_profile(user_id: str):
    """Gets detailed profile information for a specific user"""
    try:
        result = slack_client.users_info(user=user_id)
        if result['ok']:
            user = result['user']
            profile = user['profile']
            return f"""User Profile:
• Name: {user.get('real_name', 'N/A')}
• Display Name: {profile.get('display_name', 'N/A')}
• Email: {profile.get('email', 'N/A')}
• Title: {profile.get('title', 'N/A')}
• Status: {profile.get('status_text', 'N/A')}"""
        return f"Error getting profile: {result.get('error', 'Unknown error')}"
    except SlackApiError as e:
        return f"Error: {str(e)}"

def slack_list_channels(limit: int = 100):
    """Lists public channels in the workspace"""
    try:
        result = slack_client.conversations_list(limit=min(limit, 200))
        if result['ok']:
            channels = [f"• {c['name']} ({c['id']})" for c in result['channels']]
            return "\n".join(channels)
        return f"Error listing channels: {result.get('error', 'Unknown error')}"
    except SlackApiError as e:
        return f"Error: {str(e)}"

def slack_post_message(channel_id: str, text: str):
    """Posts a new message to a Slack channel"""
    try:
        # Handle channel names without #
        if not channel_id.startswith('C'):
            channel_id = channel_id.lstrip('#')
            
        result = slack_client.chat_postMessage(
            channel=channel_id,
            text=text
        )
        if result['ok']:
            return f"Message posted successfully (ts: {result['ts']})"
        return f"Error posting message: {result.get('error', 'Unknown error')}"
    except SlackApiError as e:
        error = e.response['error']
        if error == 'not_in_channel':
            return "Error: Bot is not in this channel. Please add the bot using '/invite @your_bot_name'"
        elif error == 'channel_not_found':
            return "Error: Channel not found. Please check the channel name."
        else:
            return f"Slack API Error: {error}"
    except Exception as e:
        return f"Error: {str(e)}"

def slack_reply_to_thread(channel_id: str, thread_ts: str, text: str):
    """Replies to a specific message thread"""
    try:
        result = slack_client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text=text
        )
        if result['ok']:
            return f"Reply posted successfully (ts: {result['ts']})"
        return f"Error posting reply: {result.get('error', 'Unknown error')}"
    except SlackApiError as e:
        return f"Error: {str(e)}"

def slack_add_reaction(channel_id: str, timestamp: str, reaction: str):
    """Adds an emoji reaction to a message"""
    try:
        result = slack_client.reactions_add(
            channel=channel_id,
            timestamp=timestamp,
            name=reaction
        )
        if result['ok']:
            return f"Reaction '{reaction}' added successfully"
        return f"Error adding reaction: {result.get('error', 'Unknown error')}"
    except SlackApiError as e:
        return f"Error: {str(e)}"

def slack_get_channel_history(channel_id: str, limit: int = 10):
    """Gets recent messages from a channel"""
    try:
        result = slack_client.conversations_history(
            channel=channel_id,
            limit=limit
        )
        if result['ok']:
            messages = [f"[{m['ts']}] {m.get('user', 'Unknown')}: {m['text']}" 
                       for m in result['messages']]
            return "\n".join(messages)
        return f"Error getting history: {result.get('error', 'Unknown error')}"
    except SlackApiError as e:
        return f"Error: {str(e)}"

def get_ai_response(prompt):
    try:
        response = client.chat.complete(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": prompt}],
            tools=tools,
            tool_choice="auto"
        )
        
        if hasattr(response.choices[0].message, 'tool_calls') and response.choices[0].message.tool_calls:
            tool_call = response.choices[0].message.tool_calls[0]
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            # Execute the appropriate function
            if function_name == "create_repository":
                return create_repository(**function_args)
            elif function_name == "list_repositories":
                return list_repositories(**function_args)
            elif function_name == "create_jira_issue":
                return create_jira_issue(**function_args)
            elif function_name == "list_jira_projects":
                return list_jira_projects()
            elif function_name == "create_confluence_page":
                return create_confluence_page(**function_args)
            elif function_name == "list_confluence_spaces":
                return list_confluence_spaces()
            elif function_name == "send_slack_message":
                return send_slack_message(**function_args)
            elif function_name == "upload_file_to_slack":
                return upload_file_to_slack(**function_args)
            elif function_name == "slack_get_thread_replies":
                return slack_get_thread_replies(**function_args)
            elif function_name == "slack_get_users":
                return slack_get_users(**function_args)
            elif function_name == "slack_get_user_profile":
                return slack_get_user_profile(**function_args)
            elif function_name == "slack_list_channels":
                return slack_list_channels(**function_args)
            elif function_name == "slack_post_message":
                return slack_post_message(**function_args)
            elif function_name == "slack_reply_to_thread":
                return slack_reply_to_thread(**function_args)
            elif function_name == "slack_add_reaction":
                return slack_add_reaction(**function_args)
            elif function_name == "slack_get_channel_history":
                return slack_get_channel_history(**function_args)
        
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

def main():
    print("Welcome to Unified Terminal Chat (GitHub, Jira, Confluence, Slack)")
    print("Type 'quit' to exit")
    print("-" * 50)
    print("\nAvailable Slack commands:")
    print("• list channels - Show all Slack channels")
    print("• send message <text> to <channel> - Send a message")
    print("• reply <text> to thread <thread_ts> in <channel> - Reply to a thread")
    print("• add reaction <emoji> to message <ts> in <channel> - Add reaction")
    print("• show history <channel> [limit] - Show channel history")
    print("\n")
    
    while True:
        user_input = input("\nYou: ")
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("\nGoodbye!")
            break
        
        # Process common Slack commands
        if user_input.lower() == "list channels":
            response = slack_list_channels()
        elif user_input.lower().startswith("send message"):
            parts = user_input.split(" to ", 1)
            if len(parts) == 2:
                message = parts[0].replace("send message", "").strip()
                channel = parts[1].strip()
                response = slack_post_message(channel, message)
            else:
                response = "Please use format: send message <text> to <channel>"
        elif user_input.lower().startswith("reply"):
            # Example: reply Hello to thread 1234.5678 in general
            try:
                parts = user_input.split(" to thread ", 1)[1].split(" in ")
                thread_ts = parts[0].strip()
                channel = parts[1].strip()
                text = user_input.split(" to thread ")[0].replace("reply", "").strip()
                response = slack_reply_to_thread(channel, thread_ts, text)
            except:
                response = "Please use format: reply <text> to thread <thread_ts> in <channel>"
        elif user_input.lower().startswith("add reaction"):
            # Example: add reaction thumbsup to message 1234.5678 in general
            try:
                parts = user_input.split(" to message ", 1)[1].split(" in ")
                ts = parts[0].strip()
                channel = parts[1].strip()
                reaction = user_input.split(" to message ")[0].replace("add reaction", "").strip()
                response = slack_add_reaction(channel, ts, reaction)
            except:
                response = "Please use format: add reaction <emoji> to message <ts> in <channel>"
        elif user_input.lower().startswith("show history"):
            try:
                parts = user_input.replace("show history", "").strip().split()
                channel = parts[0]
                limit = int(parts[1]) if len(parts) > 1 else 10
                response = slack_get_channel_history(channel, limit)
            except:
                response = "Please use format: show history <channel> [limit]"
        else:
            response = get_ai_response(user_input)
        
        print("\n" + response)

if __name__ == "__main__":
    main() 