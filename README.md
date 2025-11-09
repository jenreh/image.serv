# Image Generation MCP Server

FastMCP server for image generation and editing using **gpt-image-1** and **FLUX.1-Kontext-pro** models.

## Features

- **Image Generation**: Create images from text prompts using OpenAI's gpt-image-1 or Google's FLUX.1-Kontext-pro
- **Image Editing**: Edit existing images with prompts and optional masks (gpt-image-1 only)
- **Multi-Image Support**: Edit up to 16 images simultaneously
- **Inpainting**: Use mask images to specify edit regions
- **Flexible Output**: PNG, JPEG, or WEBP formats with customizable quality and compression

## Installation

1. Install dependencies:

```bash
uv sync
```

2. Set up environment variables:

```bash
# Required for gpt-image-1
export OPENAI_API_KEY="your_api_key"
export OPENAI_BASE_URL="https://your-azure-endpoint.openai.azure.com"

# Optional for FLUX.1-Kontext-pro
export GOOGLE_API_KEY="your_google_api_key"

# Required for image storage
export BACKEND_SERVER="http://localhost:8000"
export TMP_PATH="/tmp/app_images"
```

## Usage

### Running the Server

```bash
cd app/backend
python mcp_server.py
```

Or use with FastMCP:

```bash
fastmcp run app.backend.mcp_server
```

### MCP Configuration

Add to your MCP settings (e.g., Claude Desktop):

```json
{
  "mcpServers": {
    "image-generation": {
      "command": "uv",
      "args": ["run", "python", "app/backend/mcp_server.py"],
      "cwd": "/path/to/image.serv",
      "env": {
        "OPENAI_API_KEY": "your_key",
        "OPENAI_BASE_URL": "your_endpoint",
        "BACKEND_SERVER": "http://localhost:8000"
      }
    }
  }
}
```

## Tools

### 1. generate_image

Generate images from text prompts.

**Parameters:**

- `prompt` (required): Text description of the desired image (max 32000 chars)
- `model`: "gpt-image-1" or "FLUX.1-Kontext-pro" (default: "gpt-image-1")
- `n`: Number of images to generate (1-10, default: 1)
- `size`: Image dimensions - "1024x1024", "1536x1024", "1024x1536", or "auto" (default: "auto")
- `quality`: Quality level - "low", "medium", "high", or "auto" (default: "auto")
- `user`: User identifier for monitoring (default: "default")

**Example:**

```python
generate_image(
    prompt="A serene mountain landscape at sunset",
    model="gpt-image-1",
    n=2,
    size="1536x1024",
    quality="high"
)
```

**Returns:** Markdown with base64-encoded images

### 2. edit_image

Edit existing images with text prompts and optional masks.

**Parameters:**

- `prompt` (required): Text description of desired edits (max 32000 chars)
- `image_paths` (required): List of image URLs, file paths, or base64 data URLs (max 16)
- `model`: Must be "gpt-image-1" (only model supporting editing)
- `mask_path`: Optional mask image for inpainting (PNG with alpha channel)
- `n`: Number of edited variations (1-10, default: 1)
- `size`: Output dimensions (default: "auto")
- `quality`: Output quality (default: "auto")
- `output_format`: "png", "jpeg", or "webp" (default: "png")
- `user`: User identifier (default: "default")

**Example:**

```python
edit_image(
    prompt="Add a rainbow in the sky",
    image_paths=["https://example.com/landscape.jpg"],
    mask_path="https://example.com/sky_mask.png",
    model="gpt-image-1",
    quality="high",
    output_format="png"
)
```

**Returns:** Markdown with base64-encoded edited images

## Image Input Formats

The server supports three input formats for images:

1. **URLs**: `https://example.com/image.jpg`
2. **File paths**: `/path/to/image.png`
3. **Base64 data URLs**: `data:image/png;base64,iVBORw0KG...`

## Masks for Inpainting

For selective editing with masks:

1. Create a PNG image with transparency
2. Fully transparent areas (alpha=0) indicate regions to edit
3. Opaque areas remain unchanged
4. Mask must have same dimensions as input image
