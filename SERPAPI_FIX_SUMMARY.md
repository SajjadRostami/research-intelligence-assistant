# SerpAPI HTTP 400 Error - Root Cause Analysis and Fix

## Issue Summary

The live test was failing with:
```
HTTP 400 Bad Request
Error: "`num` parameter must be an integer between 10 and 100."
```

## Root Cause

**SerpAPI's `google_patents` engine enforces a constraint that was not documented in our implementation**: the `num` parameter must be between **10 and 100**.

The test script was requesting `num=5`, which violated the minimum constraint.

## Investigation Results

### 1. Verified Engine Validity
✅ **"google_patents" is a valid engine** - confirmed via SerpAPI documentation at https://serpapi.com/google-patents-api

### 2. Correct Endpoint
✅ **Endpoint is correct**: `https://serpapi.com/search`

### 3. Parameter Constraints
The issue was with the `num` parameter:
- **Minimum**: 10 (not documented in our code)
- **Maximum**: 100 (was documented)

### 4. Why HTTP 400 Occurred

The request sent:
```
GET https://serpapi.com/search?engine=google_patents&q=XPBD+soft+body+simulation+algorithm&num=5&api_key=...
                                                                                         ^^^^^^
```

SerpAPI server-side validation rejected `num=5` because it's below the minimum of 10.

### 5. Corrected Request Format

```
GET https://serpapi.com/search?engine=google_patents&q=XPBD+soft+body+simulation+algorithm&num=10&api_key=...
```

### 6. Changes Made

#### a) Fixed `_build_search_params()` in `ria/adapters/serpapi_patents.py`
**Before:**
```python
"num": min(num_results, 100),  # Only enforced maximum
```

**After:**
```python
num_clamped = max(10, min(num_results, 100))  # Enforce both min and max
return {
    ...
    "num": num_clamped,
    ...
}
```

#### b) Updated live test in `test_serpapi_patents_live.py`
**Before:**
```python
max_results = 5
```

**After:**
```python
max_results = 10  # SerpAPI requires minimum of 10 for google_patents
```

#### c) Updated unit tests in `tests/unit/test_serpapi_patents.py`
- Modified `test_build_search_params()` to use valid value (50 instead of 5)
- Added new test `test_build_search_params_min_limit()` to verify minimum clamping
- Existing `test_build_search_params_max_limit()` already tested maximum

#### d) Updated documentation in `SERPAPI_SETUP.md`
- Changed "Max Results per Query: Up to 100" to "Results per Query: Must be between 10 and 100"
- Added note about automatic clamping behavior

### 7. Minimal curl Example

```bash
#!/bin/bash
# Test SerpAPI Google Patents endpoint

API_KEY="${SERPAPI_API_KEY}"
QUERY="XPBD soft body simulation algorithm"
NUM=10  # Must be between 10 and 100

curl -G "https://serpapi.com/search" \
  --data-urlencode "engine=google_patents" \
  --data-urlencode "q=${QUERY}" \
  --data-urlencode "num=${NUM}" \
  --data-urlencode "api_key=${API_KEY}" \
  -s | jq '.organic_results[0] // .error // .'
```

Save this as `test_serpapi_curl.sh` and run it with your API key set in the environment.

## Verification

All unit tests now pass:
```bash
$ python -m pytest tests/unit/test_serpapi_patents.py -v
============================== 14 passed in 0.18s ==============================
```

The adapter now:
1. ✅ Clamps `num` to minimum of 10 if requested value is lower
2. ✅ Clamps `num` to maximum of 100 if requested value is higher
3. ✅ Uses valid values in the range [10, 100]

## Testing the Fix

To verify the fix works with a real API key:

```bash
python test_serpapi_patents_live.py
```

Expected behavior:
- Even if you modify the code to request fewer than 10 results, it will automatically request 10
- The API will return 10+ results, and the adapter will truncate to your requested amount

## SerpAPI Documentation Reference

- **Official Docs**: https://serpapi.com/google-patents-api
- **Parameter Constraints**: `num` must be integer between 10 and 100
- **Engine**: `google_patents` (valid)
- **Required Params**: `engine`, `api_key`
- **Optional Params**: `q`, `num`, `page`, `sort`, `before`, `after`, `inventor`, `assignee`, etc.

## Lessons Learned

1. **Always validate API parameter constraints** - don't assume minimum is 1 or 0
2. **Check API documentation** - third-party APIs have specific constraints that must be honored
3. **Add tests for boundary conditions** - test both minimum and maximum constraints
4. **Document constraints clearly** - make limits visible to users of the adapter
