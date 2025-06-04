document.addEventListener('DOMContentLoaded', () => {
    const repoUrlInput = document.getElementById('repoUrl');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const loadingDiv = document.getElementById('loading');
    const errorDiv = document.getElementById('error');
    const resultsDiv = document.getElementById('results');
    const repoDetailsDiv = document.getElementById('repoDetails');
    const contributorsDiv = document.getElementById('contributors');
    const commitsDiv = document.getElementById('commits');

    analyzeBtn.addEventListener('click', async () => {
        const repoUrl = repoUrlInput.value.trim();
        if (!repoUrl) {
            showError('Please enter a GitHub repository URL.');
            return;
        }

        const repoPath = parseGitHubUrl(repoUrl);
        if (!repoPath) {
            showError('Invalid GitHub URL. Please use the format https://github.com/owner/repo');
            return;
        }

        clearPreviousResults();
        showLoading(true);

        try {
            // Fetch repository details
            const repoData = await fetchData(`https://api.github.com/repos/${repoPath}`);
            displayRepoDetails(repoData);

            // Fetch contributors
            const contributorsData = await fetchData(`https://api.github.com/repos/${repoPath}/contributors`);
            displayContributors(contributorsData);

            // Fetch commit activity (last 100 commits)
            const commitsData = await fetchData(`https://api.github.com/repos/${repoPath}/commits?per_page=5`); // Limiting to 5 for demo
            displayCommits(commitsData);

            resultsDiv.classList.remove('hidden');
        } catch (err) {
            showError(`Failed to fetch data: ${err.message}. Check the console for more details and ensure the repository is public.`);
            console.error(err);
        } finally {
            showLoading(false);
        }
    });

    function parseGitHubUrl(url) {
        try {
            const urlObj = new URL(url);
            if (urlObj.hostname !== 'github.com') {
                return null;
            }
            const pathParts = urlObj.pathname.split('/').filter(part => part.length > 0);
            if (pathParts.length >= 2) {
                return `${pathParts[0]}/${pathParts[1]}`;
            }
            return null;
        } catch (e) {
            return null;
        }
    }

    async function fetchData(url) {
        const response = await fetch(url);
        if (!response.ok) {
            if (response.status === 403) {
                 const rateLimitReset = response.headers.get('X-RateLimit-Reset');
                 const resetTime = new Date(rateLimitReset * 1000);
                 throw new Error(`API rate limit exceeded. Try again after ${resetTime.toLocaleTimeString()}. (Status: ${response.status})`);
            }
            throw new Error(`Network response was not ok. Status: ${response.status} - ${response.statusText}`);
        }
        return response.json();
    }

    function displayRepoDetails(data) {
        repoDetailsDiv.innerHTML = `
            <p><strong>Name:</strong> <a href="${data.html_url}" target="_blank">${data.name}</a></p>
            <p><strong>Description:</strong> ${data.description || 'N/A'}</p>
            <p><strong>Stars:</strong> ${data.stargazers_count}</p>
            <p><strong>Forks:</strong> ${data.forks_count}</p>
            <p><strong>Open Issues:</strong> ${data.open_issues_count}</p>
            <p><strong>Language:</strong> ${data.language || 'N/A'}</p>
            <p><strong>Owner:</strong> <a href="${data.owner.html_url}" target="_blank">${data.owner.login}</a></p>
        `;
    }

    function displayContributors(data) {
        if (!Array.isArray(data) || data.length === 0) {
            contributorsDiv.innerHTML = '<p>No contributor data available.</p>';
            return;
        }
        contributorsDiv.innerHTML = data.map(contributor => `
            <div class="contributor-item">
                <img src="${contributor.avatar_url}" alt="${contributor.login}" />
                <a href="${contributor.html_url}" target="_blank">${contributor.login}</a>
                <span>(${contributor.contributions} contributions)</span>
            </div>
        `).join('');
    }

    function displayCommits(data) {
        if (!Array.isArray(data) || data.length === 0) {
            commitsDiv.innerHTML = '<p>No commit data available.</p>';
            return;
        }
        commitsDiv.innerHTML = data.map(commitItem => `
            <div class="commit-item">
                <p class="commit-message">${commitItem.commit.message.split('\n')[0]}</p>
                <p class="commit-author">Author: ${commitItem.commit.author.name} (${commitItem.author ? `<a href="${commitItem.author.html_url}" target="_blank">${commitItem.author.login}</a>` : 'N/A'})</p>
                <p class="commit-date">Date: ${new Date(commitItem.commit.author.date).toLocaleString()}</p>
            </div>
        `).join('');
    }

    function showLoading(isLoading) {
        if (isLoading) {
            loadingDiv.classList.remove('hidden');
            resultsDiv.classList.add('hidden');
            errorDiv.classList.add('hidden');
        } else {
            loadingDiv.classList.add('hidden');
        }
    }

    function showError(message) {
        errorDiv.textContent = message;
        errorDiv.classList.remove('hidden');
        resultsDiv.classList.add('hidden');
    }

    function clearPreviousResults() {
        errorDiv.classList.add('hidden');
        errorDiv.textContent = '';
        repoDetailsDiv.innerHTML = '';
        contributorsDiv.innerHTML = '';
        commitsDiv.innerHTML = '';
        resultsDiv.classList.add('hidden');
    }
});
