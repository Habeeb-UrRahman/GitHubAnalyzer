document.addEventListener('DOMContentLoaded', () => {
    const repoUrlInput = document.getElementById('repoUrl');
    const analyzeButton = document.getElementById('analyzeButton');
    const resultsDiv = document.getElementById('results');
    const errorDiv = document.getElementById('error');
    const loadingDiv = document.getElementById('loading');

    const repoDetailsDiv = document.getElementById('repoDetails');
    const commitActivityDiv = document.getElementById('commitActivity');
    const contributorStatsDiv = document.getElementById('contributorStats');
    const languageStatsDiv = document.getElementById('languageStats');
    const openIssuesDiv = document.getElementById('openIssues');
    const latestReleaseDiv = document.getElementById('latestRelease');
    const commitFrequencyDiv = document.getElementById('commitFrequency');

    analyzeButton.addEventListener('click', analyzeRepo);
    repoUrlInput.addEventListener('keypress', function(event) {
        if (event.key === 'Enter') {
            analyzeRepo();
        }
    });

    async function analyzeRepo() {
        const repoUrl = repoUrlInput.value.trim();

        // Clear previous results and errors
        resultsDiv.style.display = 'none';
        errorDiv.style.display = 'none';
        loadingDiv.style.display = 'block'; // Show loading message
        analyzeButton.disabled = true;

        repoDetailsDiv.innerHTML = '';
        commitActivityDiv.innerHTML = '';
        contributorStatsDiv.innerHTML = '';
        languageStatsDiv.innerHTML = '';
        openIssuesDiv.innerHTML = '';
        latestReleaseDiv.innerHTML = '';
        commitFrequencyDiv.innerHTML = '';

        if (!repoUrl) {
            showError("Please enter a GitHub repository URL.");
            loadingDiv.style.display = 'none';
            analyzeButton.disabled = false;
            return;
        }

        let owner, repoName;
        try {
            const url = new URL(repoUrl);
            if (url.hostname !== 'github.com') {
                throw new Error("Invalid GitHub URL. Hostname must be github.com.");
            }
            const pathParts = url.pathname.substring(1).split('/');
            if (pathParts.length < 2 || !pathParts[0] || !pathParts[1]) {
                throw new Error("Invalid GitHub repository path. Expected format: https://github.com/owner/repo");
            }
            owner = pathParts[0];
            repoName = pathParts[1].replace('.git', '');
        } catch (e) {
            showError(`Invalid URL: ${e.message}`);
            loadingDiv.style.display = 'none';
            analyzeButton.disabled = false;
            return;
        }

        try {
            const response = await fetch('/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ owner: owner, repo: repoName }),
            });

            const data = await response.json(); // Try to parse JSON regardless of response.ok

            if (!response.ok) {
                throw new Error(data.error || `Server error: ${response.status}`);
            }
            
            // Check for errors within the data structure itself from backend processing
            if (data.error) {
                showError(data.error);
            } else {
                displayRepoDetails(data.repo_details);
                displayCommitActivity(data.commit_activity);
                displayContributorStats(data.contributor_stats);
                displayLanguages(data.languages);
                displayOpenIssues(data.open_issues_list);
                displayLatestRelease(data.latest_release);
                displayCommitFrequency(data.commit_frequency);
                resultsDiv.style.display = 'block';
            }

        } catch (error) {
            showError(`Error analyzing repository: ${error.message}`);
            console.error("Fetch Error:", error);
        } finally {
            loadingDiv.style.display = 'none';
            analyzeButton.disabled = false;
        }
    }

    function displayRepoDetails(details) {
        if (!details || details.error) {
            document.getElementById('repoDetailsSection').classList.add('hidden');
            if(details && details.error) showErrorInResults('repoDetails', `Could not load repository details: ${details.error}`);
            return;
        }
        document.getElementById('repoDetailsSection').classList.remove('hidden');
        repoDetailsDiv.innerHTML = `
            <p><strong>Name:</strong> ${details.name || 'N/A'}</p>
            <p><strong>Description:</strong> ${details.description || 'N/A'}</p>
            <p><strong>Stars:</strong> ${details.stars !== undefined ? details.stars : 'N/A'}</p>
            <p><strong>Forks:</strong> ${details.forks !== undefined ? details.forks : 'N/A'}</p>
            <p><strong>Open Issues:</strong> ${details.open_issues !== undefined ? details.open_issues : 'N/A'}</p>
            <p><strong>Language:</strong> ${details.language || 'N/A'}</p>
            <p><strong>Created At:</strong> ${details.created_at ? new Date(details.created_at).toLocaleDateString() : 'N/A'}</p>
            <p><strong>Last Push:</strong> ${details.last_push ? new Date(details.last_push).toLocaleString() : 'N/A'}</p>
            <p><strong>URL:</strong> <a href="${details.url}" target="_blank">${details.url}</a></p>
        `;
    }

    function displayCommitActivity(activity) {
        if (!activity || activity.error || (Array.isArray(activity) && activity.length === 0)) {
            document.getElementById('commitActivitySection').classList.add('hidden');
            if(activity && activity.error) showErrorInResults('commitActivity', `Could not load commit activity: ${activity.error}`);
            else if (!activity || (Array.isArray(activity) && activity.length === 0)) showErrorInResults('commitActivity', 'No commit activity found or repository is empty.');
            return;
        }
        document.getElementById('commitActivitySection').classList.remove('hidden');
        const ul = document.createElement('ul');
        activity.forEach(commit => {
            const li = document.createElement('li');
            li.innerHTML = `
                <p class="commit-message">${escapeHtml(commit.message.split('\n')[0])}</p>
                <p class="commit-details">by <strong>${escapeHtml(commit.author)}</strong> on ${new Date(commit.date).toLocaleString()}</p>
                <p class="commit-details">SHA: ${escapeHtml(commit.sha.substring(0,7))}</p>
            `;
            ul.appendChild(li);
        });
        commitActivityDiv.innerHTML = ''; // Clear previous
        commitActivityDiv.appendChild(ul);
    }

    function displayContributorStats(stats) {
        if (!stats || stats.error || (Array.isArray(stats) && stats.length === 0)) {
            document.getElementById('contributorStatsSection').classList.add('hidden');
            if(stats && stats.error) showErrorInResults('contributorStats', `Could not load contributor stats: ${stats.error}`);
            else if (!stats || (Array.isArray(stats) && stats.length === 0)) showErrorInResults('contributorStats', 'No contributor data found.');
            return;
        }
        if (stats.message) { // Handle cases like GitHub calculating stats (202 response)
            document.getElementById('contributorStatsSection').classList.remove('hidden');
            contributorStatsDiv.innerHTML = `<p>${escapeHtml(stats.message)}</p>`;
            return;
        }

        document.getElementById('contributorStatsSection').classList.remove('hidden');
        const ul = document.createElement('ul');
        stats.forEach(contributor => {
            const li = document.createElement('li');
            li.innerHTML = `
                <img src="${escapeHtml(contributor.avatar_url)}" alt="${escapeHtml(contributor.login)}'s avatar" class="avatar">
                <div>
                    <a href="${escapeHtml(contributor.profile_url)}" target="_blank" class="contributor-login">${escapeHtml(contributor.login)}</a>
                    <p class="contributor-contributions">Contributions: ${contributor.contributions}</p>
                </div>
            `;
            ul.appendChild(li);
        });
        contributorStatsDiv.innerHTML = ''; // Clear previous
        contributorStatsDiv.appendChild(ul);
    }

    function showError(message) {
        errorDiv.innerHTML = `<p>${escapeHtml(message)}</p>`;
        errorDiv.style.display = 'block';
        resultsDiv.style.display = 'none';
    }

    function showErrorInResults(elementId, message) {
        const el = document.getElementById(elementId);
        if (el) {
            el.innerHTML = `<p class="error-message-inline">${escapeHtml(message)}</p>`;
        }
    }

    function escapeHtml(unsafe) {
        if (unsafe === null || unsafe === undefined) return '';
        return String(unsafe)
             .replace(/&/g, "&amp;")
             .replace(/</g, "&lt;")
             .replace(/>/g, "&gt;")
             .replace(/"/g, "&quot;")
             .replace(/'/g, "&#039;");
    }

    function displayLanguages(languages) {
        const section = document.getElementById('languageStatsSection');
        if (!languages || languages.error || Object.keys(languages).length === 0) {
            section.classList.add('hidden');
            if (languages && languages.error) showErrorInResults('languageStats', `Could not load languages: ${languages.error}`);
            else if (!languages || Object.keys(languages).length === 0) showErrorInResults('languageStats', 'No language data available.');
            return;
        }
        section.classList.remove('hidden');
        
        let totalBytes = 0;
        for (const lang in languages) {
            totalBytes += languages[lang];
        }

        if (totalBytes === 0) {
             showErrorInResults('languageStats', 'No language data available (0 bytes detected).');
             return;
        }

        const ul = document.createElement('ul');
        ul.className = 'language-list';
        Object.entries(languages).sort(([,a],[,b]) => b-a).forEach(([lang, bytes]) => {
            const percentage = ((bytes / totalBytes) * 100).toFixed(2);
            const li = document.createElement('li');
            li.innerHTML = `
                <span class="lang-name">${escapeHtml(lang)}</span>
                <span class="lang-percentage">${percentage}%</span>
                <div class="lang-bar-container">
                    <div class="lang-bar" style="width: ${percentage}%;"></div>
                </div>
            `;
            ul.appendChild(li);
        });
        languageStatsDiv.innerHTML = '';
        languageStatsDiv.appendChild(ul);
    }

    function displayOpenIssues(issues) {
        const section = document.getElementById('openIssuesSection');
        if (!issues || issues.error || (Array.isArray(issues) && issues.length === 0)) {
            section.classList.add('hidden');
            if (issues && issues.error) showErrorInResults('openIssues', `Could not load open issues: ${issues.error}`);
            else if (!issues || (Array.isArray(issues) && issues.length === 0)) showErrorInResults('openIssues', 'No open issues found.');
            return;
        }
        section.classList.remove('hidden');
        const ul = document.createElement('ul');
        issues.forEach(issue => {
            const li = document.createElement('li');
            li.className = 'issue-item';
            li.innerHTML = `
                <a href="${escapeHtml(issue.url)}" target="_blank" class="issue-title">#${issue.number}: ${escapeHtml(issue.title)}</a>
                <p class="issue-details">Opened by ${escapeHtml(issue.user)} on ${new Date(issue.created_at).toLocaleDateString()}</p>
            `;
            ul.appendChild(li);
        });
        openIssuesDiv.innerHTML = '';
        openIssuesDiv.appendChild(ul);
    }

    function displayLatestRelease(release) {
        const section = document.getElementById('latestReleaseSection');
        if (!release || release.error || release.message) { // release.message for 'No releases found'
            section.classList.add('hidden');
            if (release && release.error) showErrorInResults('latestRelease', `Could not load latest release: ${release.error}`);
            else if (release && release.message) showErrorInResults('latestRelease', release.message);
            else showErrorInResults('latestRelease', 'No release information available.');
            return;
        }
        section.classList.remove('hidden');
        let bodyHtml = 'No description provided.';
        if (release.body) {
            // Basic markdown to HTML conversion for release body (links, simple lists)
            // This is a very simplified version. For full markdown, a library would be better.
            bodyHtml = escapeHtml(release.body)
                .replace(/\n/g, '<br>')
                .replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank">$1</a>'); 
        }

        latestReleaseDiv.innerHTML = `
            <p><strong>Release Name:</strong> ${escapeHtml(release.name || 'N/A')}</p>
            <p><strong>Tag:</strong> <a href="${escapeHtml(release.url)}" target="_blank">${escapeHtml(release.tag_name)}</a></p>
            <p><strong>Published:</strong> ${new Date(release.published_at).toLocaleString()}</p>
            <div class="release-body">
                <strong>Notes:</strong>
                <div>${bodyHtml}</div>
            </div>
        `;
    }

    function displayCommitFrequency(frequencyData) {
        const section = document.getElementById('commitFrequencySection');
        if (!frequencyData || frequencyData.error || frequencyData.message || (Array.isArray(frequencyData) && frequencyData.length === 0)) {
            section.classList.add('hidden');
            if (frequencyData && frequencyData.error) showErrorInResults('commitFrequency', `Could not load commit frequency: ${frequencyData.error}`);
            else if (frequencyData && frequencyData.message) showErrorInResults('commitFrequency', frequencyData.message);
            else showErrorInResults('commitFrequency', 'No commit frequency data available.');
            return;
        }
        section.classList.remove('hidden');
        
        // For a real chart, use a library like Chart.js, D3.js, etc.
        // This is a very basic textual representation.
        const ul = document.createElement('ul');
        ul.className = 'frequency-list';
        frequencyData.forEach(week => {
            const li = document.createElement('li');
            const weekStartDate = new Date(week.week_start_timestamp * 1000).toLocaleDateString();
            li.innerHTML = `Week of ${weekStartDate}: <strong>${week.total_commits}</strong> commits`;
            ul.appendChild(li);
        });
        commitFrequencyDiv.innerHTML = '';
        commitFrequencyDiv.appendChild(ul);
        // Placeholder for chart: commitFrequencyDiv.innerHTML = '<p>Chart library integration needed for visualization.</p>';
    }
});
