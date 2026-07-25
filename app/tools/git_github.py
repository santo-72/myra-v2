import structlog
from pathlib import Path
from app.config import settings
import git
from github import Github, GithubException

logger = structlog.get_logger(__name__)

class GitTools:
    def __init__(self):
        self.workspace_root = Path(settings.workspace_dir).resolve()
        self.github_client = Github(settings.github_token) if settings.github_token else None

    def git_init(self) -> str:
        try:
            git.Repo.init(self.workspace_root)
            logger.info("git_repo_initialized", path=str(self.workspace_root))
            return "Successfully initialized local Git repository."
        except Exception as e:
            logger.error("git_init_error", error=str(e))
            return f"Error initializing git: {str(e)}"

    def git_commit(self, message: str) -> str:
        try:
            repo = git.Repo(self.workspace_root)
            repo.git.add(A=True)
            repo.index.commit(message)
            logger.info("git_committed", message=message)
            return f"Successfully committed changes: '{message}'"
        except git.exc.InvalidGitRepositoryError:
            return "Error: Not a git repository. Call git_init first."
        except Exception as e:
            return f"Error committing: {str(e)}"

    def create_github_repo(self, repo_name: str, private: bool = True) -> str:
        if not self.github_client:
            return "Error: GITHUB_TOKEN is not configured."
            
        try:
            user = self.github_client.get_user()
            repo = user.create_repo(name=repo_name, private=private)
            
            # Setup local remote
            local_repo = git.Repo(self.workspace_root)
            origin = local_repo.create_remote('origin', repo.clone_url)
            
            logger.info("github_repo_created", name=repo_name, url=repo.html_url)
            return f"Successfully created GitHub repository at {repo.html_url} and added remote 'origin'."
        except GithubException as ge:
            return f"GitHub API Error: {ge.data.get('message', str(ge))}"
        except Exception as e:
            return f"Error creating remote repo: {str(e)}"
