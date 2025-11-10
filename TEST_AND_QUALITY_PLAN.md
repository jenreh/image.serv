# Comprehensive Test & Quality Plan for `image.serv`

**Date:** November 10, 2025  
**Project:** Image Generation MCP Service  
**Python Version:** 3.12+  
**Status:** Analysis Complete - Ready for Implementation

---

## Executive Summary

The `image.serv` project is a FastMCP server for image generation and editing using OpenAI's gpt-image-1 and Google's FLUX.1-Kontext-pro models. Current test coverage is **incomplete**, with critical bugs in the REST API routes layer and missing unit tests for multiple untested functions.

### Key Findings
- ✅ **Backend generators** (OpenAI, Google) have solid implementations
- ✅ **Image service layer** (`edit_image_impl`, `generate_image_impl`) is well-structured
- ❌ **REST API routes** (`routes.py`) contains parameter mismatches and undefined function references
- ❌ **No test coverage** for `routes.py` endpoints
- ⚠️ **Test improvements needed** for existing backend tests

---

## Part 1: Critical Code Issues to Fix

### 1.1 Issue: Parameter Mismatch in `_build_success_response`

**File:** `server/api/routes.py` (lines 160-175)

**Problem:**
```python
def _build_success_response(
    response_obj: str | object,
    response_format: str,
    prompt: str,
    size: str,
    processing_time_ms: int,
    enhanced_prompt: str | None = None,
) -> ImageResponse:
```

**Docstring claims:** `prompt, model, size, quality, user, processing_time_ms, enhanced_prompt`  
**Actual signature:** `response_obj, response_format, prompt, size, processing_time_ms, enhanced_prompt`  
**Missing:** `model`, `quality`, `user` parameters  
**Extra:** `response_obj`, `response_format` parameters

**Call in `generate_image_route` (line ~201):**
```python
return _build_success_response(
    response_obj,
    request.response_format,
    enhanced_prompt,  # ❌ WRONG! Should be request.prompt
    request.size,
    processing_time_ms,
    enhanced_prompt,  # ❌ DUPLICATE! Already passed as 3rd arg
)
```

**Impact:** 
- Prompt metadata is incorrect (gets `enhanced_prompt` twice)
- Response metadata missing model, quality, user info

---

### 1.2 Issue: Undefined Function in `_error_response`

**File:** `server/api/routes.py` (line 99)

**Problem:**
```python
def _error_response(
    prompt: str,
    model: str,
    size: str,
    quality: str,
    user: str,
    response_format: str,
    code: str,
    message: str,
    details: str = "",
) -> ImageResponse:
    metadata = _build_response_metadata(  # ❌ UNDEFINED FUNCTION!
        prompt, model, size, quality, user, response_format, 0
    )
```

**Reality:** Function `_build_response_metadata()` does not exist in the file.

**Calls to `_error_response` (lines ~205, ~230):**
```python
return _error_response(
    request.prompt,
    request.size,
    request.response_format,
    "INTERNAL_ERROR",
    "Internal server error",
    str(e),
)
```

**Problem:** Only 6 args passed, but function signature expects 9!

**Impact:** 
- Runtime error when exception occurs
- Error responses never reach client

---

### 1.3 Issue: Missing Imports & Type Annotations

**File:** `server/api/routes.py`

**Problem:** Models imported from wrong locations:
```python
from server.backend.models import EditImageInput, GenerationInput
```

Should check:
- Are these classes in `server/backend/models.py`? ✅ YES (lines 41-72)
- Are they properly exported? Need to verify `__all__`

**Additional:** `ResponseMetadata` is defined in `server/api/models.py` but used without import in `_build_success_response`.

---

## Part 2: Test Coverage Analysis

### 2.1 Current Test Status

| Module | File | Coverage | Status |
|--------|------|----------|--------|
| **REST API Routes** | `server/api/routes.py` | 0% | ❌ Untested |
| **Image Service** | `server/backend/image_service.py` | ? | ⚠️ Need verification |
| **Utils** | `server/backend/utils.py` | Partial | ⚠️ `url_to_base64`, `generate_response` |
| **MCP Server** | `server/mcp_server.py` | ~60% | ⚠️ Needs expansion |
| **OpenAI Generator** | `server/backend/generators/openai.py` | ? | ⚠️ Need verification |
| **Google Generator** | `server/backend/generators/google.py` | ? | ⚠️ Need verification |
| **Prompt Enhancer** | `server/backend/prompt_enhancer.py` | ? | ⚠️ Need verification |
| **Image Processor** | `server/backend/image_processor.py` | ? | ⚠️ Need verification |

---

### 2.2 Untested Functions (Priority Order)

#### **Tier 1: Critical (REST API)**
1. **`get_generator(request: Request)`** - Dependency injection
   - Line: 118-130
   - Tests needed: 2 (success + HTTPException for missing generator)

2. **`generate_image_route()`** - POST /generate_image
   - Line: 132-206
   - Tests needed: 5 (success + HTTPException passthrough + generic Exception + timing validation + missing dependency)

3. **`edit_image_route()`** - POST /edit_image
   - Line: 209-248
   - Tests needed: 5 (same as generate)

4. **`_build_success_response()`** - Response builder
   - Line: 28-75
   - Tests needed: 4 (image format + adaptive_card + markdown + metadata validation)

5. **`_error_response()`** - Error response builder
   - Line: 78-106
   - Tests needed: 2 (error response structure + metadata)

#### **Tier 2: Important (Backend)**
6. **`generate_response()` in `utils.py`**
   - Tests needed: 3 (image format + adaptive_card + markdown)
   - Dependencies: URL loading, image conversion

7. **`url_to_base64()` in `utils.py`**
   - Tests needed: 4 (HTTP URL + file path + data URL + error handling)

8. **`edit_image_impl()` in `image_service.py`**
   - Tests needed: 3 (success + failure state + logging)

9. **`generate_image_impl()` in `image_service.py`**
   - Tests needed: 4 (success + failure state + enhanced prompt + logging)

#### **Tier 3: Supporting (Generators)**
10. Image loader edge cases
11. Prompt enhancer edge cases
12. Image processor edge cases

---

## Part 3: Complete Test Plan

### 3.1 Test File Structure

```
tests/
├── server/
│   ├── test_api_routes.py          # NEW - REST API endpoints
│   ├── test_mcp_server.py          # EXISTING - needs expansion
│   └── backend/
│       ├── test_image_service.py   # EXISTING - needs expansion
│       ├── test_utils.py            # NEW - utility functions
│       ├── test_prompt_enhancer.py # EXISTING
│       ├── test_image_loaders.py   # EXISTING
│       ├── test_image_processor.py # NEW (if missing)
│       └── generators/
│           ├── test_openai_generator.py  # EXISTING - needs expansion
│           ├── test_google_generator.py  # EXISTING - needs expansion
│           └── test_base_generator.py    # NEW (if missing)
└── integration/
    └── test_openai_integration.py  # EXISTING
```

### 3.2 Test Fixtures (in `conftest.py`)

**Existing Fixtures:**
- ✅ `sample_image_bytes` - 1x1 PNG pixel
- ✅ `sample_base64_image` - Data URL
- ✅ `temp_image_file` - Temporary file path
- ✅ `mock_openai_client` - AsyncAzureOpenAI mock
- ✅ `mock_google_client` - Google genai mock
- ✅ `mock_backend_server` - Backend URL

**New Fixtures Needed:**
1. **`mock_openai_generator`** - OpenAIImageGenerator instance
2. **`mock_request`** - FastAPI Request with app state
3. **`sample_generation_input`** - GenerationInput instance
4. **`sample_edit_input`** - EditImageInput instance
5. **`sample_image_response`** - ImageGeneratorResponse
6. **`mock_image_service`** - image_service impl mocks
7. **`sample_mcp_image`** - fastmcp.utilities.types.Image

---

### 3.3 Detailed Test Cases

#### **Test File: `tests/server/test_api_routes.py`** (NEW)

```
✅ Test Suite: `TestGetGenerator`
  - test_get_generator_success: Generator exists in app.state
  - test_get_generator_missing: HTTPException 500 when not found

✅ Test Suite: `TestBuildSuccessResponse`
  - test_build_success_response_image_format: Format="image" wraps Image object
  - test_build_success_response_adaptive_card: Format="adaptive_card" parses JSON
  - test_build_success_response_markdown: Format="markdown" returns string
  - test_build_success_response_metadata: Metadata has correct fields & ISO timestamp

✅ Test Suite: `TestErrorResponse`
  - test_error_response_structure: Has correct error detail fields
  - test_error_response_metadata: Metadata includes prompt, size, format

✅ Test Suite: `TestGenerateImageRoute`
  - test_generate_image_success: Happy path with valid input
  - test_generate_image_http_exception: HTTPException passthrough
  - test_generate_image_unexpected_error: Generic Exception caught & returned as error
  - test_generate_image_timing: Processing time calculated correctly
  - test_generate_image_missing_generator: HTTPException 500 dependency injection

✅ Test Suite: `TestEditImageRoute`
  - test_edit_image_success: Happy path with valid input
  - test_edit_image_http_exception: HTTPException passthrough
  - test_edit_image_unexpected_error: Generic Exception caught
  - test_edit_image_timing: Processing time calculated correctly
  - test_edit_image_missing_generator: HTTPException 500 dependency injection

Total: ~18 tests
```

#### **Test File: `tests/server/backend/test_utils.py`** (NEW)

```
✅ Test Suite: `TestGenerateResponse`
  - test_generate_response_image_format: Returns Image object with base64
  - test_generate_response_adaptive_card: Returns JSON string
  - test_generate_response_markdown: Returns markdown with link
  - test_generate_response_invalid_format: ValueError for unknown format

✅ Test Suite: `TestUrlToBase64`
  - test_url_to_base64_http_url: Downloads and converts remote image
  - test_url_to_base64_file_path: Reads local file and converts
  - test_url_to_base64_data_url: Extracts base64 from data URL
  - test_url_to_base64_http_error: httpx.HTTPError propagates
  - test_url_to_base64_file_not_found: OSError for missing file

Total: ~8 tests
```

#### **Test File: `tests/server/backend/test_image_service.py`** (EXPAND)

```
EXISTING: Tests for edit_image_impl, generate_image_impl
NEW CASES:
  - test_generate_image_enhanced_prompt_returned: Enhanced prompt in tuple
  - test_edit_image_error_state: ImageResponseState.FAILED → ValueError
  - test_generate_image_error_state: ImageResponseState.FAILED → ValueError
  - test_edit_image_logging: Debug logs include image count & mask flag
  - test_generate_image_logging: Debug logs include size parameter

Total additions: ~5 tests
```

---

## Part 4: Code Fixes Required

### 4.1 Fix #1: Correct `_build_success_response` Signature

**Before:**
```python
def _build_success_response(
    response_obj: str | object,
    response_format: str,
    prompt: str,
    size: str,
    processing_time_ms: int,
    enhanced_prompt: str | None = None,
) -> ImageResponse:
```

**After:**
```python
def _build_success_response(
    response_obj: str | object,
    response_format: str,
    prompt: str,
    size: str,
    processing_time_ms: int,
    enhanced_prompt: str | None = None,
    model: str | None = None,
    quality: str | None = None,
    user: str | None = None,
) -> ImageResponse:
```

**Update docstring** to match actual parameters.

---

### 4.2 Fix #2: Extract & Define `_build_response_metadata`

**After `_build_success_response` (around line 75), add:**

```python
def _build_response_metadata(
    prompt: str,
    size: str,
    response_format: str,
    processing_time_ms: int = 0,
    enhanced_prompt: str | None = None,
    model: str | None = None,
    quality: str | None = None,
    user: str | None = None,
) -> ResponseMetadata:
    """Build response metadata object.
    
    Args:
        prompt: Original prompt
        size: Image size
        response_format: Response format type
        processing_time_ms: Processing time in milliseconds
        enhanced_prompt: Refined prompt if available
        model: Model used (optional)
        quality: Quality setting (optional)
        user: User identifier (optional)
    
    Returns:
        ResponseMetadata instance
    """
    return ResponseMetadata(
        prompt=prompt,
        size=size,
        response_format=response_format,
        timestamp=datetime.now(tz=timezone.utc).isoformat(),
        processing_time_ms=processing_time_ms,
        enhanced_prompt=enhanced_prompt,
    )
```

---

### 4.3 Fix #3: Correct `_build_success_response` Call in `generate_image_route`

**Line ~201, Before:**
```python
return _build_success_response(
    response_obj,
    request.response_format,
    enhanced_prompt,  # ❌ WRONG
    request.size,
    processing_time_ms,
    enhanced_prompt,
)
```

**After:**
```python
return _build_success_response(
    response_obj,
    request.response_format,
    request.prompt,  # ✅ Use original prompt
    request.size,
    processing_time_ms,
    enhanced_prompt,  # ✅ Enhanced prompt
)
```

---

### 4.4 Fix #4: Correct `_error_response` Calls

**Before (lines ~205, ~230):**
```python
return _error_response(
    request.prompt,
    request.size,
    request.response_format,
    "INTERNAL_ERROR",
    "Internal server error",
    str(e),
)
```

**After:**
```python
return _error_response(
    prompt=request.prompt,
    model="unknown",
    size=request.size,
    quality="unknown",
    user="unknown",
    response_format=request.response_format,
    code="INTERNAL_ERROR",
    message="Internal server error",
    details=str(e),
)
```

---

### 4.5 Fix #5: Update `_error_response` to Use New Helper

**Before:**
```python
def _error_response(
    prompt: str,
    model: str,
    size: str,
    quality: str,
    user: str,
    response_format: str,
    code: str,
    message: str,
    details: str = "",
) -> ImageResponse:
    metadata = _build_response_metadata(
        prompt, model, size, quality, user, response_format, 0
    )
```

**After:**
```python
def _error_response(
    prompt: str,
    model: str,
    size: str,
    quality: str,
    user: str,
    response_format: str,
    code: str,
    message: str,
    details: str = "",
) -> ImageResponse:
    metadata = _build_response_metadata(
        prompt=prompt,
        size=size,
        response_format=response_format,
        model=model,
        quality=quality,
        user=user,
    )
```

---

## Part 5: Implementation Roadmap

### Phase 1: Fix Code Issues (1-2 hours)
1. ✅ Create `_build_response_metadata()` helper
2. ✅ Fix `_build_success_response()` signature & docstring
3. ✅ Fix calls to `_build_success_response()` in routes
4. ✅ Fix calls to `_error_response()` in routes
5. ✅ Run linting: `make lint`, `make format`
6. ✅ Quick smoke test: `make test` (ensure nothing breaks)

### Phase 2: Write Tests (3-4 hours)
1. ✅ Create `tests/server/test_api_routes.py` with all test cases
2. ✅ Create `tests/server/backend/test_utils.py` 
3. ✅ Expand `tests/server/backend/test_image_service.py`
4. ✅ Add fixtures to `tests/conftest.py`
5. ✅ Run tests: `make test`
6. ✅ Check coverage: `uv run pytest --cov`

### Phase 3: Quality Gates (1 hour)
1. ✅ Achieve **≥80% code coverage** (focus on routes & utils)
2. ✅ All tests pass (green CI)
3. ✅ No lint violations: `make lint`
4. ✅ Code formatted: `make format --check`

### Phase 4: Documentation (30 min)
1. ✅ Update `TEST_AND_QUALITY_PLAN.md` with results
2. ✅ Add comments to complex test mocks
3. ✅ Document any test fixtures added to `conftest.py`

---

## Part 6: Mock Strategy & Fixture Plan

### 6.1 Mocking Hierarchy

```
┌─────────────────────────────────────────┐
│   FastAPI Request + app.state           │
│   - generators: dict[str, Generator]    │
└──────────────┬──────────────────────────┘
               │
         ┌─────┴─────┐
         │            │
    OpenAI Goog
    Gentr  Gentr
    ┌──────────────────┐
    │ ImageService     │
    │ - generate_impl  │
    │ - edit_impl      │
    └────────┬─────────┘
             │
    ┌────────┴──────────┐
    │                   │
  ImageProcessor   Utils
  - save_images  - url_to_base64
                 - generate_response
```

### 6.2 Fixture Definitions

**In `tests/conftest.py`, add:**

```python
@pytest.fixture
def mock_openai_generator(mock_openai_client: AsyncMock) -> OpenAIImageGenerator:
    """OpenAI image generator with mocked client."""
    gen = OpenAIImageGenerator(
        api_key="test-key",
        id="gpt-image-1",
        label="Test Generator",
        model="gpt-image-1",
        backend_server="http://localhost:8000",
        base_url="https://test.openai.azure.com",
    )
    gen.client = mock_openai_client
    return gen


@pytest.fixture
def mock_request(mock_openai_generator: OpenAIImageGenerator) -> MagicMock:
    """FastAPI Request with app state."""
    request = MagicMock(spec=Request)
    request.app.state.generators = {"gpt-image-1": mock_openai_generator}
    return request


@pytest.fixture
def sample_generation_input() -> GenerationInput:
    """Sample GenerationInput for testing."""
    return GenerationInput(
        prompt="A beautiful landscape",
        size="1024x1024",
        output_format="png",
        background="opaque",
        response_format="image",
        seed=42,
        enhance_prompt=True,
    )


@pytest.fixture
def sample_edit_input() -> EditImageInput:
    """Sample EditImageInput for testing."""
    return EditImageInput(
        prompt="Add a sunset",
        image_paths=["https://example.com/landscape.jpg"],
        size="1024x1024",
        output_format="png",
        response_format="image",
        mask_path=None,
    )


@pytest.fixture
def sample_image_response() -> ImageGeneratorResponse:
    """Sample successful image generation response."""
    return ImageGeneratorResponse(
        state=ImageResponseState.SUCCEEDED,
        images=["data:image/png;base64,iVBORw0KG..."],
        enhanced_prompt="Enhanced: A beautiful landscape",
    )
```

---

## Part 7: Success Criteria

### Testing Metrics
- ✅ **Coverage:** ≥80% for `server/api/routes.py` and `server/backend/utils.py`
- ✅ **Test Count:** Minimum 40 new tests (18 routes + 8 utils + 14 expansions)
- ✅ **All Tests Pass:** Zero failures, all green
- ✅ **No Flaky Tests:** Tests deterministic, run 3x consistently

### Code Quality
- ✅ **Linting:** `make lint` passes (ruff checks)
- ✅ **Formatting:** `make format --check` passes
- ✅ **Type Safety:** All functions annotated
- ✅ **Docstrings:** All functions have docstrings

### Functionality
- ✅ **Routes work end-to-end:** Both generate and edit endpoints
- ✅ **Error handling:** Exceptions caught and returned properly
- ✅ **Response metadata:** Accurate timing, format, prompt info
- ✅ **Dependency injection:** Generator dependency works

---

## Part 8: Time Estimates

| Phase | Task | Estimate | Owner |
|-------|------|----------|-------|
| **1** | Fix code issues | 1-2 hrs | Developer |
| **2.1** | Write test_api_routes.py | 1.5 hrs | Developer |
| **2.2** | Write test_utils.py | 1 hr | Developer |
| **2.3** | Expand existing tests | 1 hr | Developer |
| **2.4** | Add fixtures | 30 min | Developer |
| **3** | Quality gates & coverage | 1 hr | Developer |
| **4** | Documentation & review | 30 min | Developer |
| **Total** | | **6-7 hours** | |

---

## Part 9: Risk Assessment

### Low Risk
- ✅ Adding new test files (doesn't affect existing code)
- ✅ Fixing parameter mismatches (clearly wrong)

### Medium Risk
- ⚠️ Modifying `routes.py` signature (affects callers)
  - **Mitigation:** Update all call sites in same PR

### High Risk
- ❌ None identified

---

## Part 10: Next Steps

1. **Review this plan** with team
2. **Approve fixes** to be applied
3. **Execute Phase 1** (code fixes)
4. **Execute Phase 2** (test writing)
5. **Verify Phase 3** (quality gates)
6. **Document Phase 4** (complete this plan)

---

## Appendix: File-by-File Summary

### `server/api/routes.py`
- **Lines:** 248 total
- **Untested functions:** 5 (get_generator, _build_success_response, _error_response, generate_image_route, edit_image_route)
- **Bugs found:** 3 major
- **Tests needed:** ~18
- **Status:** 🔴 Critical

### `server/backend/image_service.py`
- **Lines:** ~60
- **Untested functions:** 2 partial (generate_image_impl, edit_image_impl)
- **Tests needed:** ~5 additions
- **Status:** 🟡 Partial

### `server/backend/utils.py`
- **Lines:** 108 total
- **Untested functions:** 2 (generate_response, url_to_base64)
- **Tests needed:** ~8
- **Status:** 🔴 Critical

### `server/backend/generators/openai.py`
- **Lines:** 202
- **Coverage:** Unknown
- **Tests needed:** Edge cases
- **Status:** 🟡 Partial

### `server/backend/generators/google.py`
- **Lines:** ~150
- **Coverage:** Unknown
- **Tests needed:** Edge cases
- **Status:** 🟡 Partial

---

**Plan Prepared By:** AI Assistant  
**Date:** November 10, 2025  
**Status:** Ready for Implementation ✅
