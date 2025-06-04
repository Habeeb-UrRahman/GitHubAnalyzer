import os
import requests
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

app = Flask(__name__)

GITHUB_API_URL = "https://api.github.com"
# It's good practice to use a User-Agent header
# GITHUB_USER_AGENT = "GitHubRepoAnalyzer/1.0 (YourNameOrAppName)" # Optional: Replace with your info
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def get_github_headers():
    headers = {
        "Accept": "application/vnd.github.v3+json",
        # "User-Agent": GITHUB_USER_AGENT # Optional
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    return headers

def fetch_repo_metadata(owner, repo):
    """Fetches basic repository metadata."""
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}"
    try:
        response = requests.get(url, headers=get_github_headers())
        response.raise_for_status() # Raises an HTTPError for bad responses (4XX or 5XX)
        data = response.json()
        return {
            "name": data.get("name"),
            "description": data.get("description"),
            "stars": data.get("stargazers_count"),
            "forks": data.get("forks_count"),
            "open_issues": data.get("open_issues_count"),
            "language": data.get("language"),
            "created_at": data.get("created_at"),
            "last_push": data.get("pushed_at"),
            "url": data.get("html_url")
        }
    except requests.exceptions.HTTPError as e:
        error_message = f"HTTP error: {e.response.status_code}"
        try:
            error_details = e.response.json().get('message', str(e))
            error_message += f" - {error_details}"
        except ValueError: # If response is not JSON
            error_message += f" - {e.response.text[:100]}" # Show first 100 chars of text response
        
        if e.response.status_code == 404:
            return {"error": "Repository not found."}
        elif e.response.status_code == 403:
            rate_limit_remaining = e.response.headers.get('X-RateLimit-Remaining')
            if rate_limit_remaining == '0':
                return {"error": "GitHub API rate limit exceeded. Please try again later or use a GitHub Personal Access Token."}
            return {"error": f"GitHub API access forbidden. Check token permissions or rate limits. Details: {error_details}"}
        return {"error": error_message}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request error fetching repo metadata: {str(e)}"}

def fetch_commit_activity(owner, repo):
    """Fetches the last 5 commits for simplicity."""
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/commits?per_page=5"
    try:
        response = requests.get(url, headers=get_github_headers())
        response.raise_for_status()
        commits_data = response.json()
        
        commits = []
        for commit_item in commits_data:
            commits.append({
                "sha": commit_item.get("sha"),
                "message": commit_item.get("commit", {}).get("message", "No commit message"),
                "author": commit_item.get("commit", {}).get("author", {}).get("name", "Unknown author"),
                "date": commit_item.get("commit", {}).get("author", {}).get("date"),
            })
        return commits
    except requests.exceptions.HTTPError as e:
        error_message = f"HTTP error: {e.response.status_code}"
        try:
            error_details = e.response.json().get('message', str(e))
            error_message += f" - {error_details}"
        except ValueError:
            error_message += f" - {e.response.text[:100]}"

        if e.response.status_code == 404 or (e.response.status_code == 409 and "Git Repository is empty" in error_details): # 409 for empty repo
            return {"error": "Commit history not found or repository is empty."}
        elif e.response.status_code == 403:
            rate_limit_remaining = e.response.headers.get('X-RateLimit-Remaining')
            if rate_limit_remaining == '0':
                return {"error": "GitHub API rate limit exceeded for commit activity."}
            return {"error": f"GitHub API access forbidden for commit activity. Details: {error_details}"}
        return {"error": error_message}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request error fetching commit activity: {str(e)}"}

def fetch_contributor_stats(owner, repo):
    """Fetches top 5 contributors."""
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/contributors?per_page=5&anon=0" # anon=0 to exclude anonymous
    try:
        response = requests.get(url, headers=get_github_headers())
        # GitHub API returns 202 if data is being computed, frontend should handle this possibility or we wait.
        # For simplicity, we'll treat 202 as data not yet ready / or just proceed if it returns JSON.
        if response.status_code == 202:
            return {"message": "Contributor data is being calculated by GitHub. Please try again shortly."}
        
        response.raise_for_status()
        contributors_data = response.json()
        
        contributors = []
        if isinstance(contributors_data, list):
            for contributor_item in contributors_data:
                contributors.append({
                    "login": contributor_item.get("login"),
                    "contributions": contributor_item.get("contributions"),
                    "avatar_url": contributor_item.get("avatar_url"),
                    "profile_url": contributor_item.get("html_url")
                })
        return contributors
    except requests.exceptions.HTTPError as e:
        error_message = f"HTTP error: {e.response.status_code}"
        try:
            error_details = e.response.json().get('message', str(e))
            error_message += f" - {error_details}"
        except ValueError:
            error_message += f" - {e.response.text[:100]}"

        if e.response.status_code == 204: # No content, e.g., no contributors
            return [] # Return empty list, not an error
        if e.response.status_code == 404:
            return {"error": "Contributor data not found (repository might be private or have no contributors)."}
        elif e.response.status_code == 403:
            rate_limit_remaining = e.response.headers.get('X-RateLimit-Remaining')
            if rate_limit_remaining == '0':
                return {"error": "GitHub API rate limit exceeded for contributor stats."}
            return {"error": f"GitHub API access forbidden for contributor stats. Details: {error_details}"}
        return {"error": error_message}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request error fetching contributor stats: {str(e)}"}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_repo_route(): # Renamed to avoid conflict with any 'analyze' variable/import
    data = request.get_json()
    owner = data.get('owner')
    repo = data.get('repo')

    if not owner or not repo:
        return jsonify({"error": "Owner and repository name are required."}), 400

    repo_details = fetch_repo_metadata(owner, repo)
    # If fetching basic repo details fails (e.g., repo not found, critical rate limit), 
    # return early with that error.
    if isinstance(repo_details, dict) and repo_details.get("error") and "Repository not found" in repo_details.get("error"):
        return jsonify({"error": repo_details["error"]}), 404
    if isinstance(repo_details, dict) and repo_details.get("error") and "rate limit exceeded" in repo_details.get("error").lower():
         return jsonify({"error": repo_details["error"]}), 429 # Too Many Requests

    commit_activity = fetch_commit_activity(owner, repo)
    contributor_stats = fetch_contributor_stats(owner, repo)
    
    return jsonify({
        "repo_details": repo_details,
        "commit_activity": commit_activity,
        "contributor_stats": contributor_stats
    })

if __name__ == '__main__':
    # For development, Flask's built-in server is fine.
    # For production, use a WSGI server like Gunicorn or Waitress.
    app.run(debug=True) # debug=True enables auto-reloading and debugger
