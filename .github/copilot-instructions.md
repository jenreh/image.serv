---
applyTo: "**"
description: "Main Copilot instructions for image.serv - FastMCP server for image generation/editing with comprehensive development workflow"
---

# Image Generation MCP Server

**FastMCP server for image generation and editing using gpt-image-1 and FLUX.1-Kontext-pro models.**

> **Purpose:** Guide GitHub Copilot to align suggestions with this FastMCP+FastAPI project's tech stack, workflows, and quality standards.
> **Stacks:** Python 3.12+ · FastMCP · FastAPI · OpenAI/Azure · Google Genai · Pydantic

---

## 1) Golden Rules (Short, Actionable)
1. **Separation of concerns:** MCP server layer (`mcp_server.py`) → FastAPI routes (`api/routes.py`) → backend logic (`backend/`) → generators (OpenAI, Google).
2. **Tests are truth.** Async tests use `@pytest.mark.asyncio`; mock generators/clients in `conftest.py`. On failures: fix code first.
3. **No f-strings in logging.** Use parameterized logging: `log.info("Items: %d", count)` not `log.info(f"Items: {count}")`.
4. **Async-first.** All generators and services are async; use `async def` and `await` throughout.
5. **Pydantic for validation.** All inputs use Pydantic models (`GenerationInput`, `EditImageInput`, etc.) for type safety and docs.
6. **Composition over inheritance.** Generators use helper classes (`PromptEnhancer`, `ImageProcessor`) not deep hierarchies.
7. **NEVER** create files using "cat" or similar shell commands, NEVER! Use Python file I/O methods.
8. **NEVER** generate summary files and the end of a task. Keep the summaries brief and to the point.

> Focus: input → generator → response format (image/markdown/adaptive_card).

---

## 2) Architecture Overview

### Core Layers (Request Flow)
```
MCP Client (Claude, etc.)
    ↓
mcp_server.py [FastMCP tools: generate_image, edit_image]
    ↓
api/routes.py [FastAPI REST endpoints: /generate, /edit]
    ↓
backend/image_service.py [Service layer: generate_image_impl, edit_image_impl]
    ↓
backend/generators/ [Provider implementations: OpenAIImageGenerator, GoogleImageGenerator]
    ├─ prompt_enhancer.py [Refines prompts via LLM]
    ├─ image_processor.py [Converts formats, saves to backend]
    ├─ image_loaders.py [Loads images: URL, file, base64]
    └─ utils.py [generate_response: formats image as image/markdown/adaptive_card]
```

### Response Format Routing
```python
# All endpoints support 3 response formats via response_format parameter:
- "image": returns MCP Image object (bytes)
- "markdown": returns markdown string with embedded image
- "adaptive_card": returns Microsoft Adaptive Card JSON
```

### Key Models (Input/Output)
- **Input:** `GenerationInput` (prompt, size, enhance_prompt, etc.), `EditImageInput` (image_paths, mask_path, etc.)
- **Output:** `ImageGeneratorResponse` (state, images[], enhanced_prompt)
- **API Response:** `ImageResponse` (status, data{images/markdown/adaptive_card}, metadata, error)

---

## 3) Tooling Decision Matrix (Condensed)

| Situation | Primary | Use For |
|---|---|---|
| Generator API uncertainty | **Context7** | OpenAI/Google SDK docs; response formats |
| Test fixture issues | **conftest.py** | Mock patterns in this project |
| Async pattern questions | **server/backend/generators/** | Real implementations; use as reference |
| Response format routing | **backend/utils.py** | generate_response() implementation |
| New generator scaffold | **OpenAIImageGenerator** | Inherit from ImageGenerator; implement generate/edit |

**Baseline: Always check conftest.py fixtures and existing generators before adding new patterns.**

---

## 4) SOP — Development Workflow

### Prepare
1. **Understand the flow:** Input model → Generator (async) → Response formatter → Client receives.
2. **Sync tools:** `make install` (uses **uv**, Python 3.12+).
3. **Baseline:** `make test` to snapshot current state.

### Testing Pattern (Critical)
All new code must include async tests with mocks:
```python
@pytest.mark.asyncio
async def test_generator_behavior() -> None:
    """Test async generator with mocked client."""
    generator = AsyncMock()
    generator.generate.return_value = ImageGeneratorResponse(
        state=ImageResponseState.SUCCEEDED,
        images=["data:image/png;base64,..."],
        enhanced_prompt="Refined"
    )
    result = await generate_image_impl(input_data, generator)
    assert result[1] == "Refined"  # enhanced_prompt
```

### Response Format Routing
When adding features, ensure all 3 formats are supported:
```python
# In routes.py - call generate_response() with appropriate format
response_obj = await generate_response(
    image_bytes,
    format=input_data.response_format  # "image", "markdown", or "adaptive_card"
)
```

### Generators: Composition Pattern
Add helpers, don't inherit:
```python
class OpenAIImageGenerator(ImageGenerator):
    def __init__(self, api_key, ...):
        self.prompt_enhancer = PromptEnhancer(self.client)  # ✅ Composition
        self.image_processor = ImageProcessor(self)  # ✅ Composition
```

### Quality Gates
- Lint/format: `make check` and `make format`
- Tests: `make test` with coverage ≥ **80%**
- No f-strings in logger calls (use `log.info("Value: %s", var)`)

### Commit & PR
- Conventional Commits (`feat:`, `fix:`, `refactor:`…).
- PR includes: description, model/endpoint tested, test coverage increase.

## 5) Code Generation Rules
- **Python 3.12+** only; deps via **uv**.
- Use FastMCP, FastAPI, Pydantic, OpenAI SDK, Google Genai.
- **No f-strings in logger calls.**
- All I/O is async (`async def`, `await`).
- Input validation via Pydantic models.
- Unit tests for every new endpoint/generator method.

## 6) Testing Strategy
- Tests in `tests/server/**/*.py` (mirrors source structure).
- Tests in `tests/integration/**/*.py` for end-to-end scenarios. Exclude when running the test suite.
- Use `@pytest.mark.asyncio` for all async tests.
- Mock external APIs (OpenAI, Google) in `conftest.py`.
- Coverage target **≥ 80%**.
- Fixtures: `sample_image_bytes`, `mock_openai_client`, `mock_google_client` provided in `conftest.py`.

## 7) Search SOPs
- **Context7 first** for OpenAI/Google SDK docs.
- **DuckDuckGo** for cross-version issues.
- Check `tests/conftest.py` for fixture patterns before adding new ones.

## 8) Security & Config Hygiene
- No credentials in code; use `.env` locally, environment variables in prod.
- API keys loaded from `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `OPENAI_BASE_URL` environment variables.
- Parameterized logs; avoid logging sensitive values.
- Update vulnerable deps promptly.

## 9) Pre-PR Checklist
- [ ] Tests added/updated; all green (`make test`)
- [ ] Lint/format checks pass (`make check`, `make format`)
- [ ] Coverage ≥ 80%
- [ ] PR description includes: endpoint/method tested, test coverage delta
- [ ] No f-strings in logger calls


---

# Key Patterns & Integration Points

## Generator Pattern (Composition-Based)

**All image generators inherit from `ImageGenerator` base class and compose helper services:**

```python
class OpenAIImageGenerator(ImageGenerator):
    def __init__(self, api_key: str, ...):
        self.client = AsyncAzureOpenAI(...)
        self.prompt_enhancer = PromptEnhancer(self.client)  # Helper
        self.image_processor = ImageProcessor(self)        # Helper

    async def generate(self, input_data: GenerationInput) -> ImageGeneratorResponse:
        """Main entry point - orchestrates helpers."""
        pass
```

**To add a new generator:** Copy `OpenAIImageGenerator` structure, implement `generate()` and `edit()` methods.

## Request → Response Flow

1. **MCP Tool** (`mcp_server.py::generate_image`) receives `prompt`, `response_format`, etc.
2. **Route Handler** (`api/routes.py`) validates input → calls service
3. **Service** (`image_service.py`) calls generator.generate(input_data)
4. **Generator** uses helpers:
   - `PromptEnhancer.enhance()` – LLM-based prompt refinement
   - `ImageProcessor.save()` – Format conversion & storage
   - `ImageLoader.load()` – Handles URL/file/base64 sources
5. **Response Formatter** (`utils.py::generate_response()`) wraps in requested format
6. **Client** receives Image, markdown, or Adaptive Card JSON

## Testing Mocks Pattern

All tests mock external APIs in `conftest.py`:

```python
@pytest.fixture
def mock_openai_client() -> AsyncMock:
    client = AsyncMock()
    mock_gen_response = MagicMock()
    mock_gen_response.data = [MagicMock(b64_json="dGVzdA==", url=None)]
    client.images.generate.return_value = mock_gen_response
    return client
```

**Always inject mocked clients into generators in tests.** See `tests/server/backend/generators/` for examples.

## Image Format Conversions

The `ImageProcessor` handles PNG↔JPEG↔WEBP conversions. Output format controlled by:
- `output_format` input param: "png" | "jpeg" | "webp" (default: "jpeg")
- Stored in `TMP_PATH` environment variable (default: "./images")

## Async-First Pattern

All I/O operations are async:
- Generator.generate/edit → async
- PromptEnhancer.enhance → async
- ImageProcessor.save → async
- Routes handlers → async

Use `await` to call async functions; wrap in `@pytest.mark.asyncio` for tests.

## Critical Integration Points

1. **API Keys:** From environment (`OPENAI_API_KEY`, `GOOGLE_API_KEY`)
2. **Image Storage:** `BACKEND_SERVER` + `TMP_PATH` for persisted images
3. **Response Formats:** Always support `image` | `markdown` | `adaptive_card`
4. **Logging:** Parameterized only (no f-strings)
