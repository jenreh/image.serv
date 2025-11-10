"""FastMCP server for image generation and editing.

Orchestrates image generation and editing tools with lazy-loaded generators.
Provides two main tools:
- generate_image: Generate new images from text prompts
- edit_image: Edit existing images with prompts and optional masks
"""

import logging
import os

from dotenv import load_dotenv
from fastmcp import FastMCP

from server.backend.generators import OpenAIImageGenerator
from server.mcp_tools import create_edit_image_tool, create_generate_image_tool

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


class ImageMCPServer:
    """MCP server for image generation and editing operations.

    Manages initialization, configuration, and tool registration for
    image processing tasks.
    """

    def __init__(self) -> None:
        """Initialize MCP server with configuration."""
        self.mcp = FastMCP(name="Image Generation Server")
        self._generators: dict[str, OpenAIImageGenerator] = {}
        self._initialized = False

    def _init_generators(self) -> None:
        """Initialize generators from environment variables.

        Uses lazy initialization to avoid unnecessary setup on import.
        Supports both gpt-image-1 and FLUX.1-Kontext-pro models.
        """
        if self._initialized:
            return

        self._initialized = True

        openai_key = os.environ.get("OPENAI_API_KEY")
        openai_base_url = os.environ.get("OPENAI_BASE_URL")
        google_key = os.environ.get("GOOGLE_API_KEY")
        backend_server = os.environ.get("BACKEND_SERVER")

        if openai_key and openai_base_url:
            self._generators["gpt-image-1"] = OpenAIImageGenerator(
                api_key=openai_key,
                base_url=openai_base_url,
                backend_server=backend_server,
                model="gpt-image-1",
            )
            logger.info("Initialized gpt-image-1 generator")

            self._generators["FLUX.1-Kontext-pro"] = OpenAIImageGenerator(
                api_key=google_key,
                backend_server=backend_server,
            )
            logger.info("Initialized FLUX.1-Kontext-pro generator")

        if not self._generators:
            logger.warning("No generators initialized - check environment variables")

    def _register_tools(self) -> None:
        """Register image tools with the MCP server.

        Creates tool instances with injected generator dependencies
        and registers them with FastMCP.
        """
        if not self._generators.get("gpt-image-1"):
            logger.error("Cannot register tools: gpt-image-1 generator not available")
            return

        generator = self._generators["gpt-image-1"]

        # Register generation tool
        generate_tool = create_generate_image_tool(generator)
        self.mcp.tool(generate_tool)
        logger.info("Registered generate_image tool")

        # Register editing tool
        edit_tool = create_edit_image_tool(generator)
        self.mcp.tool(edit_tool)
        logger.info("Registered edit_image tool")

    def run(self) -> None:
        """Start the MCP server.

        Initializes generators and registers tools before starting
        the server.
        """
        self._init_generators()
        self._register_tools()
        self.mcp.run()


# Module-level cache for server instance
_server_instance: ImageMCPServer | None = None


def get_server() -> ImageMCPServer:
    """Get or create the global MCP server instance.

    Uses lazy initialization to avoid setup costs until needed.
    """
    global _server_instance  # noqa: PLW0603
    if _server_instance is None:
        _server_instance = ImageMCPServer()
    return _server_instance


if __name__ == "__main__":
    # Run the MCP server
    server = get_server()
    server.run()
