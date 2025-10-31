# Van Price Lists Summary

This folder contains the HTML summary page for all price lists in the `cenniky` folder.

## Files

- `index.html` - The main summary page with embedded CSS

## Regenerating the Summary

To regenerate the summary page after adding or updating PDF files in the `cenniky` folder:

```bash
python3 generate_summary.py
```

This will:
1. Scan all PDF files in the `cenniky` folder
2. Parse filenames to extract metadata (make, model, year, validity dates)
3. Generate a new `docs/index.html` file

## Viewing the Summary

Open `index.html` in any web browser. The page is fully self-contained with no external dependencies.

The links in the summary page point to `../cenniky/` (relative paths), so the page will work correctly when the folder structure is maintained.
