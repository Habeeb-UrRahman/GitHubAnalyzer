import os
import requests
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

GITHUB_API_URL = "https://api.github.com"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Constructs headers for GitHub API requests, including authorization if a token is present.
def get_github_headers():
    headers = {
        "Accept": "application/vnd.github.v3+json",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    return headers

# Fetches basic repository metadata (name, stars, forks, etc.).
def fetch_repo_metadata(owner, repo):
    """Fetches basic repository metadata."""
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}"
    try:
        response = requests.get(url, headers=get_github_headers())
        response.raise_for_status()
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

# Fetches recent commit activity (last 5 commits).
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

# Fetches top 10 contributors to the repository.
def fetch_contributor_stats(owner, repo):
    """Fetches top 10 contributors."""
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/contributors?per_page=10&anon=0"
    try:
        response = requests.get(url, headers=get_github_headers())
        # Handle 202: contributor data is being calculated by GitHub.
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

        if e.response.status_code == 204:
            return []
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

# Serves the main HTML page.
@app.route('/')
def index():
    return render_template('index.html')

# API endpoint to analyze a GitHub repository.
@app.route('/analyze', methods=['POST'])
def analyze_repo_route():
    data = request.get_json()
    owner = data.get('owner')
    repo = data.get('repo')

    if not owner or not repo:
        return jsonify({"error": "Owner and repository name are required."}), 400

    repo_details = fetch_repo_metadata(owner, repo)

    # Return early if fetching basic repo details fails (e.g., repo not found).
    if isinstance(repo_details, dict) and repo_details.get("error") and "Repository not found" in repo_details.get("error"):
        return jsonify({"error": repo_details["error"]}), 404
    # Return early if rate limit is exceeded during initial metadata fetch.
    if isinstance(repo_details, dict) and repo_details.get("error") and "rate limit exceeded" in repo_details.get("error").lower():
         return jsonify({"error": repo_details["error"]}), 429 # Too Many Requests

    commit_activity = fetch_commit_activity(owner, repo)
    contributor_stats = fetch_contributor_stats(owner, repo)
    languages_data = fetch_languages(owner, repo)
    open_issues_data = fetch_open_issues(owner, repo)
    latest_release_data = fetch_latest_release(owner, repo)
    commit_frequency_data = fetch_commit_frequency(owner, repo)
    
    return jsonify({
        "repo_details": repo_details,
        "commit_activity": commit_activity,
        "contributor_stats": contributor_stats,
        "languages": languages_data,
        "open_issues_list": open_issues_data,
        "latest_release": latest_release_data,
        "commit_frequency": commit_frequency_data
    })


# Fetches the programming language breakdown for the repository.
def fetch_languages(owner, repo):
    """Fetches language breakdown for the repository."""
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/languages"
    try:
        response = requests.get(url, headers=get_github_headers())
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return {"message": "Language data not available."}
        return {"error": f"HTTP error fetching languages: {e.response.status_code} - {e.response.json().get('message', str(e))}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request error fetching languages: {str(e)}"}

# Fetches a specified number of recent open issues (default 5), excluding pull requests.
def fetch_open_issues(owner, repo, count=5):
    """Fetches a list of recent open issues."""
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/issues?state=open&sort=created&direction=desc&per_page={count}"
    try:
        response = requests.get(url, headers=get_github_headers())
        response.raise_for_status()
        issues_data = response.json()
        issues = []
        for issue_item in issues_data:
            if not issue_item.get('pull_request'): # Filter out pull requests
                issues.append({
                    "title": issue_item.get("title"),
                    "number": issue_item.get("number"),
                    "url": issue_item.get("html_url"),
                    "user": issue_item.get("user", {}).get("login"),
                    "created_at": issue_item.get("created_at")
                })
        return issues
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404: # Should not happen for issues if repo exists
            return {"error": "Issues not found (repository might be private or issues disabled)."}
        return {"error": f"HTTP error fetching open issues: {e.response.status_code} - {e.response.json().get('message', str(e))}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request error fetching open issues: {str(e)}"}

# Fetches details of the latest release for the repository.
def fetch_latest_release(owner, repo):
    """Fetches the latest release information for the repository."""
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/releases/latest"
    try:
        response = requests.get(url, headers=get_github_headers())
        response.raise_for_status()
        release_data = response.json()
        return {
            "name": release_data.get("name"),
            "tag_name": release_data.get("tag_name"),
            "published_at": release_data.get("published_at"),
            "url": release_data.get("html_url"),
            "body": release_data.get("body")
        }
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404: # Common if no releases are published
            return {"message": "No releases found for this repository."}
        return {"error": f"HTTP error fetching latest release: {e.response.status_code} - {e.response.json().get('message', str(e))}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request error fetching latest release: {str(e)}"}

# Fetches weekly commit activity for the last year.
def fetch_commit_frequency(owner, repo):
    """Fetches weekly commit activity for the last year."""
    # This endpoint provides data calculated by GitHub, might return 202 if not cached
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/stats/commit_activity"
    try:
        response = requests.get(url, headers=get_github_headers())
        # Handle 202: commit frequency data is being calculated by GitHub.
        if response.status_code == 202:
            # Retry logic could be implemented here, or just inform the user.
            # For simplicity, we'll try a second time after a short delay.
            # More robust: client-side polling or longer server-side wait with feedback.
            import time
            time.sleep(2) # Wait 2 seconds and try again
            response = requests.get(url, headers=get_github_headers())
            if response.status_code == 202:
                 return {"message": "Commit frequency data is being calculated by GitHub. Please try again in a moment."}

        response.raise_for_status()
        # Data is an array of objects, each with 'days' (commits per day of week) and 'total' (commits in week), 'week' (timestamp)
        # We'll simplify it to weekly totals for now.
        frequency_data = response.json()
        simplified_frequency = []
        if isinstance(frequency_data, list):
            for week_stat in frequency_data:
                simplified_frequency.append({
                    "week_start_timestamp": week_stat.get("week"),
                    "total_commits": week_stat.get("total")
                })
        return simplified_frequency[-12:] # Return last 12 weeks

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 204: # No content, e.g. empty repo or stats not yet computed
            return {"message": "No commit activity data available (repository might be new or empty, or data is being computed)."}
        if e.response.status_code == 404:
             return {"error": "Commit activity stats not found."}
        return {"error": f"HTTP error fetching commit frequency: {e.response.status_code} - {e.response.json().get('message', str(e))}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request error fetching commit frequency: {str(e)}"}

if __name__ == '__main__':
    # For development, Flask’s built-in server is fine.
    # Bind to 0.0.0.0 so Docker can route traffic into the container.
    app.run(host='0.0.0.0', port=5000, debug=True)
