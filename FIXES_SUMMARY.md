# Document History Action Buttons - Fix Summary

## Changes Made

### 1. Updated `templates/history.html`
**Issue:** Buttons were using anchor links (#ocr, #llm, #json) instead of proper API endpoints.

**Changes:**
- `OCR Text` button: Changed from `#ocr` to `/history/{document_id}/ocr`
- `Raw LLM` button: Changed from `#llm` to `/history/{document_id}/raw-llm`
- `JSON` button: Changed from `#json` to `/history/{document_id}/json`
- `Excel` button: Changed from `/api/documents/{document_id}/download/xlsx` to `/history/{document_id}/excel`
- Added `target="_blank"` to view buttons (OCR, Raw LLM, JSON) to open in new tab
- Excel button downloads directly (no new tab)

### 2. Updated `routers/pages.py`
**Added four new backend routes with proper error handling:**

#### `GET /history/{document_id}/ocr`
- Displays stored OCR text from database
- Falls back to extraction's raw_text if ocr_text is empty
- Shows formatted HTML response with "Back to History" button
- Returns 404 if document doesn't exist

#### `GET /history/{document_id}/raw-llm`
- Displays stored raw_llm_response from database
- Shows formatted HTML response with "Back to History" button
- Returns 404 if document doesn't exist

#### `GET /history/{document_id}/json`
- Displays formatted extracted_json (or json_output as fallback)
- Automatically formats JSON with proper indentation for readability
- Shows formatted HTML response with "Back to History" button
- Returns 404 if document doesn't exist

#### `GET /history/{document_id}/excel`
- Downloads the generated Excel file
- **Error handling:**
  - Returns 404 if document doesn't exist
  - Returns 404 if no excel_file_path stored in database
  - Returns 404 if file doesn't exist on disk with message: "Excel file not found."
  - Never returns 500 (Internal Server Error)

## Requirements Met

✅ 1. Every history record passes its document_id to the buttons
✅ 2. Buttons use proper URLs: `/history/{document_id}/ocr|raw-llm|json|excel`
✅ 3. All four backend routes implemented
✅ 4. OCR route displays stored OCR text
✅ 5. Raw LLM route displays raw_llm_response
✅ 6. JSON route displays formatted extracted_json
✅ 7. Excel route downloads file or shows 404 (never 500)
✅ 8. Proper error handling with 404 for missing documents
✅ 9. History template updated with document-specific URLs
✅ 10. Replaced anchor-based URLs with real API endpoints

## Testing Checklist

- [ ] Navigate to /history
- [ ] Click "OCR Text" button - should open OCR content in new tab with proper formatting
- [ ] Click "Raw LLM" button - should open LLM response in new tab with proper formatting
- [ ] Click "JSON" button - should open formatted JSON in new tab
- [ ] Click "Excel" button - should download the Excel file
- [ ] Test with non-existent document ID (e.g., /history/99999/ocr) - should show 404
- [ ] Test Excel button when file is missing - should show "Excel file not found." (404)

## Files Modified

1. `templates/history.html` - Updated button URLs
2. `routers/pages.py` - Added 4 new routes with full error handling
