# Analysis Summary: image.serv Test & Quality Plan

## 📊 Project Snapshot

**Project:** Image Generation MCP Service
**Technology Stack:** Python 3.12 · FastAPI · FastMCP · OpenAI · Google Genai
**Current Status:** 🔴 Critical issues in REST API layer
**Test Coverage:** ~60% (MCP) | 0% (REST API) | Partial (Backend)

---

## 🚨 Critical Findings

### Three Major Bugs in `server/api/routes.py`

| Bug | Severity | Impact | Line |
|-----|----------|--------|------|
| **Parameter mismatch in `_build_success_response`** | 🔴 Critical | Incorrect response metadata (prompt gets enhanced prompt) | 28-75 |
| **Undefined function `_build_response_metadata()`** | 🔴 Critical | Runtime error when exception occurs (all error paths fail) | 99 |
| **Wrong argument in `generate_image_route` call** | 🔴 Critical | Response loses original prompt, duplicates enhanced prompt | ~201 |
| **Signature mismatch for `_error_response` calls** | 🟡 High | Runtime error: missing 3 required keyword args | ~205, ~230 |

**All bugs must be fixed before testing.**

---

## 📋 Test Coverage Plan

### By the Numbers

- **New Tests:** 40+ test cases
- **New Test Files:** 2 (`test_api_routes.py`, `test_utils.py`)
- **Expanded Tests:** 1 (`test_image_service.py`)
- **New Fixtures:** 6 in `conftest.py`
- **Target Coverage:** ≥80% for `routes.py` and `utils.py`
- **Estimated Time:** 6-7 hours

### Test Distribution

```
Tests Needed by Module
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

REST API Routes (routes.py)         [████████████████░] 18 tests
├─ get_generator                    [██] 2
├─ _build_success_response          [████] 4
├─ _error_response                  [██] 2
├─ generate_image_route             [█████] 5
└─ edit_image_route                 [█████] 5

Backend Utils (utils.py)            [████████░] 8 tests
├─ generate_response                [████] 4
└─ url_to_base64                    [█████] 5 (with error cases)

Image Service (image_service.py)    [██░] 5 additions
├─ error state handling             [██] 2
├─ logging validation               [██] 2
└─ return value validation          [░] 1

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL ESTIMATE                      ~31 tests
```

---

## 🔧 Required Code Fixes

### Fix #1: Add Helper Function

```python
# Location: After _build_success_response (line ~75)
def _build_response_metadata(
    prompt: str,
    size: str,
    response_format: str,
    processing_time_ms: int = 0,
    enhanced_prompt: str | None = None,
) -> ResponseMetadata:
    """Build response metadata object."""
```

**Lines:** ~20 lines of new code
**Risk:** Low (new function, no side effects)

---

### Fix #2: Update Function Signature

```python
# Change from:
def _build_success_response(
    response_obj, response_format, prompt, size, processing_time_ms, enhanced_prompt

# Change to:
def _build_success_response(
    response_obj, response_format, prompt, size, processing_time_ms,
    enhanced_prompt, model=None, quality=None, user=None
```

**Lines:** 1 line change + docstring
**Risk:** Low (backwards compatible with default args)

---

### Fix #3: Fix generate_image_route Call

```python
# Line ~201, change from:
return _build_success_response(
    response_obj,
    request.response_format,
    enhanced_prompt,  # ❌ WRONG
    request.size,
    processing_time_ms,
    enhanced_prompt,

# Change to:
return _build_success_response(
    response_obj,
    request.response_format,
    request.prompt,  # ✅ CORRECT
    request.size,
    processing_time_ms,
    enhanced_prompt,
```

**Lines:** 1 line change
**Risk:** Low (fixes obvious error)

---

### Fix #4: Fix _error_response Calls

```python
# Change from: (6 args)
return _error_response(
    request.prompt,
    request.size,
    request.response_format,
    "INTERNAL_ERROR",
    "Internal server error",
    str(e),
)

# Change to: (9 named args)
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

**Lines:** 2 call sites, ~6 lines each
**Risk:** Low (fixes signature mismatch)

---

## 🧪 Testing Strategy

### Test File Architecture

```
tests/server/
├── test_api_routes.py              [NEW] 18 tests
│   ├── TestGetGenerator            (2 tests)
│   ├── TestBuildSuccessResponse    (4 tests)
│   ├── TestErrorResponse           (2 tests)
│   ├── TestGenerateImageRoute      (5 tests)
│   └── TestEditImageRoute          (5 tests)
│
├── backend/
│   ├── test_utils.py               [NEW] 8 tests
│   │   ├── TestGenerateResponse    (4 tests)
│   │   └── TestUrlToBase64         (5 tests)
│   │
│   └── test_image_service.py       [EXPAND] +5 tests
│       └── Error handling cases
│
└── conftest.py                     [EXPAND] +6 fixtures
    ├── mock_openai_generator
    ├── mock_request
    ├── sample_generation_input
    ├── sample_edit_input
    ├── sample_image_response
    └── sample_mcp_image
```

### Mocking Approach

**Dependency Injection Pattern:**

```
FastAPI Request
  └─ app.state.generators
      └─ "gpt-image-1": OpenAIImageGenerator (mocked)
          ├─ client: AsyncAzureOpenAI (mocked)
          ├─ prompt_enhancer: PromptEnhancer (mocked)
          └─ image_processor: ImageProcessor (mocked)
```

**External Dependencies:**

- ✅ Mock `OpenAIImageGenerator.generate()` → `ImageGeneratorResponse`
- ✅ Mock `OpenAIImageGenerator.edit()` → `ImageGeneratorResponse`
- ✅ Mock `edit_image_impl()` → image URL string
- ✅ Mock `generate_image_impl()` → (image URL, enhanced prompt) tuple
- ✅ Mock `generate_response()` → Image | str | dict
- ✅ Mock `httpx.AsyncClient` for URL downloads

---

## ⏱️ Implementation Timeline

### Phase 1: Fix Code Issues (1-2 hours)

- [ ] Add `_build_response_metadata()` helper
- [ ] Update `_build_success_response()` signature
- [ ] Fix `generate_image_route()` call
- [ ] Fix `edit_image_route()` call
- [ ] Update `_error_response()` calls
- [ ] Run linting: `make lint`, `make format`
- [ ] Smoke test: `make test`

### Phase 2: Write Tests (3-4 hours)

- [ ] Create `tests/server/test_api_routes.py` (18 tests)
- [ ] Create `tests/server/backend/test_utils.py` (8 tests)
- [ ] Expand `tests/server/backend/test_image_service.py` (+5 tests)
- [ ] Add 6 new fixtures to `conftest.py`
- [ ] Run tests: `make test`
- [ ] Check coverage: `uv run pytest --cov`

### Phase 3: Quality Gates (1 hour)

- [ ] Achieve ≥80% coverage for `routes.py` and `utils.py`
- [ ] All tests pass (green)
- [ ] No lint violations: `make lint`
- [ ] Code formatted: `make format --check`

### Phase 4: Documentation (30 minutes)

- [ ] Update `TEST_AND_QUALITY_PLAN.md` with results
- [ ] Document test fixtures in code comments
- [ ] Create PR with all changes

**Total Estimated Time:** 6-7 hours

---

## 📊 Success Criteria

### Code Quality Gates

- ✅ All syntax and type errors fixed
- ✅ Linting passes: `make lint`
- ✅ Formatting passes: `make format --check`
- ✅ All functions have proper docstrings

### Test Coverage

- ✅ Coverage ≥80% for `server/api/routes.py`
- ✅ Coverage ≥80% for `server/backend/utils.py`
- ✅ All 40+ new tests pass
- ✅ No test flakiness (run 3x, consistent results)

### Functionality

- ✅ Both REST endpoints work end-to-end
- ✅ Error handling works correctly
- ✅ Response metadata accurate
- ✅ Dependency injection works
- ✅ Processing time calculation correct

---

## 🎯 Quick Reference: Untested Functions

| Function | File | Lines | Priority | Tests |
|----------|------|-------|----------|-------|
| `get_generator()` | routes.py | 118-130 | 🔴 Critical | 2 |
| `generate_image_route()` | routes.py | 132-206 | 🔴 Critical | 5 |
| `edit_image_route()` | routes.py | 209-248 | 🔴 Critical | 5 |
| `_build_success_response()` | routes.py | 28-75 | 🔴 Critical | 4 |
| `_error_response()` | routes.py | 78-106 | 🔴 Critical | 2 |
| `generate_response()` | utils.py | 18-48 | 🟡 High | 4 |
| `url_to_base64()` | utils.py | 51-108 | 🟡 High | 5 |
| `edit_image_impl()` | image_service.py | 8-27 | 🟡 High | +2 |
| `generate_image_impl()` | image_service.py | 30-59 | 🟡 High | +3 |

---

## 🔍 Key Test Cases by Category

### Happy Path (Success Cases)

- ✅ Generate image with default parameters
- ✅ Generate image with custom size/format
- ✅ Edit image with mask
- ✅ Response metadata accurate
- ✅ Processing time calculated

### Error Handling

- ✅ HTTPException passthrough (dependency missing)
- ✅ Generic Exception caught and returned as error
- ✅ Invalid response format
- ✅ URL download failure
- ✅ File not found

### Edge Cases

- ✅ Multiple image editing
- ✅ Data URL image input
- ✅ File path image input
- ✅ Empty enhanced prompt
- ✅ Very long processing time

---

## 📝 Notes for Implementation

1. **Don't start with implementation yet** - This plan is the thinking phase
2. **Code fixes first, then tests** - Fixes must be applied before writing tests
3. **Use async/await for all route tests** - Mark with `@pytest.mark.asyncio`
4. **Mock at the boundary** - Mock injected generator, not internal methods
5. **Test what matters** - Focus on request/response contracts, not implementation details
6. **Use fixtures heavily** - Reduce test boilerplate with reusable fixtures

---

## ✅ Analysis Complete

**Status:** Ready for implementation phase
**Next Step:** Review this plan with team, approve fixes, begin Phase 1
**Questions:** Reference the full `TEST_AND_QUALITY_PLAN.md` for detailed specifications

---

**Generated:** November 10, 2025
**Confidence Level:** 🟢 High (thorough code review + test coverage analysis)
