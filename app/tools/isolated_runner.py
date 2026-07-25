import docker
import structlog

logger = structlog.get_logger(__name__)

class IsolatedRunner:
    """Executes code inside an ephemeral Docker container"""
    def __init__(self):
        try:
            self.client = docker.from_env()
            logger.info("IsolatedRunner initialized (Docker connected)")
        except Exception as e:
            logger.error("Failed to connect to Docker daemon", error=str(e))
            self.client = None

    def run_python_code(self, code: str, image: str = "python:3.12-alpine") -> str:
        """
        Runs Python code inside an ephemeral container.
        """
        if not self.client:
            return "Error: Docker client not initialized."
            
        logger.info(f"Running isolated Python code in {image}")
        try:
            # python -c "..."
            escaped_code = code.replace('"', '\\"')
            command = f'python -c "{escaped_code}"'
            
            output = self.client.containers.run(
                image,
                command,
                remove=True,  # Destroy immediately after run
                mem_limit="128m",
                network_mode="none"  # Completely offline for safety
            )
            return output.decode('utf-8').strip()
        except docker.errors.ContainerError as e:
            logger.error("ContainerError", error=str(e))
            return f"ContainerError: {e.stderr.decode('utf-8') if getattr(e, 'stderr', None) else str(e)}"
        except Exception as e:
            logger.error("Isolated execution failed", error=str(e))
            return f"Error: {str(e)}"
