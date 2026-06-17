# Fix Summary: RankingEngine Scoring Issue

## Problem Identified

The MVP test failed in `RankingEngine.score()` with the following errors:

1. **Primary Error**: `ScoredSourceItem() got multiple values for keyword argument 'relevance_explanation'`
2. **Fallback Error**: `KeyError: 'relevance_explanation'` when fallback handling tried to create scored items

## Root Cause

In `ria/ranking.py` lines 157-172, when creating `ScoredSourceItem` instances:

```python
# BEFORE (broken)
scored_item = ScoredSourceItem(
    **item.model_dump(),  # This includes relevance_explanation from RawSourceItem
    relevance_score=relevance.score,
    relevance_explanation=relevance.reasoning,  # Duplicate!
)
```

The `**item.model_dump()` spread operator already included `relevance_explanation` from the `RawSourceItem` parent class, and then it was being passed again as a keyword argument, causing the "multiple values" error.

## Solution Applied

Modified `ria/ranking.py` to exclude `relevance_explanation` from the model dump before passing it:

```python
# AFTER (fixed)
scored_item = ScoredSourceItem(
    **item.model_dump(exclude={'relevance_explanation'}),
    relevance_score=relevance.score,
    relevance_explanation=relevance.reasoning,
)
```

This change was applied to both:
- The successful scoring path (line 158)
- The error fallback path (line 168)

## Changes Made

### 1. Fixed `ria/ranking.py`
- **Line 158**: Added `exclude={'relevance_explanation'}` to success path
- **Line 168**: Added `exclude={'relevance_explanation'}` to fallback path
- **Impact**: Minimal - only 2 lines changed in production code

### 2. Added comprehensive unit tests `tests/unit/test_ranking.py`
- Test deduplication (by title, DOI, patent number)
- Test successful scoring
- **Test scoring with LLM failure** (specifically tests the fallback robustness requirement)
- Test that original fields are preserved (ensures no field loss)
- Test top selection logic

All 8 unit tests pass.

## Verification

### Unit Tests
```bash
python -m pytest tests/unit/test_ranking.py -v
# Result: 8 passed in 0.65s
```

### End-to-End MVP Test
```bash
./RUN_TEST.sh
# Result: All pipeline stages completed successfully ✓
```

The test now:
- Successfully scores 9 patent items
- Handles scoring failures gracefully with 0.0 default score
- Preserves all required fields including `relevance_score` and `relevance_explanation`
- Generates metrics and completes the full pipeline

## Requirements Met

✅ 1. Identified why ScoredSourceItem receives relevance_explanation twice  
✅ 2. Fixed the smallest possible amount of code (2 lines)  
✅ 3. Made RankingEngine.score() robust when scoring fails  
✅ 4. Ensured fallback scored items include relevance_score and relevance_explanation  
✅ 5. Added comprehensive unit tests for this case  
✅ 6. Re-ran ./RUN_TEST.sh successfully  
✅ 7. Did not change search adapters, metrics generation, or report generation  

## Files Modified

1. `/home/coder/research-intelligence-assistant/ria/ranking.py` (2 lines changed)
2. `/home/coder/research-intelligence-assistant/tests/unit/test_ranking.py` (new file, 253 lines)

No changes to:
- `ria/models.py` (no changes needed)
- Search adapters
- Metrics generation
- Report generation
