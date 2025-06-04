# GitHub Repo Analyzer

A tool to analyze public GitHub repositories and display insights such as metadata, contributor activity, and commit frequencies.

## Features
- Input GitHub repository URL.
- Display repository metadata (name, description, stars, forks, open issues).
- Show contributor statistics.
- Visualize commit activity.
- Handle GitHub API rate limits and errors.

## Setup
1. Clone the repository (or use the files created here).
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. (Optional but Recommended) Create a `.env` file in the root directory (`GitHubRepoAnalyzer/`) and add your GitHub Personal Access Token:
   ```
   GITHUB_TOKEN=your_github_pat_here
   ```
   Replace `your_github_pat_here` with your actual token. This helps avoid API rate limits.
6. Run the application: `flask run`
7. Open your browser and go to `http://127.0.0.1:5000`.
