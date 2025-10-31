# Van Price Lists Summary

This folder contains the HTML summary page and JSON data for all price lists in the `cenniky` folder.

## Files

- `index.html` - JavaScript-based summary page that loads data from JSON
- `data.json` - JSON file containing all parsed price list data (prices, models, dates, etc.)
- `index-static.html` - Static HTML version (legacy, for comparison)

## Regenerating the Summary

To regenerate the summary page after adding or updating PDF files in the `cenniky` folder:

```bash
pip install pypdf  # Install PDF parsing library if needed
python3 generate_summary.py
```

This will:
1. Scan all PDF files in the `cenniky` folder
2. Parse PDF content to extract prices and variants
3. Parse filenames to extract metadata (make, model, year, validity dates)
4. Generate `data.json` with all parsed information
5. Generate `index.html` (JavaScript-based page)
6. Generate `index-static.html` (server-rendered HTML)

## Viewing the Summary

Open `index.html` in any web browser. The page loads data from `data.json` client-side using vanilla JavaScript.

**Note:** Due to browser security restrictions, you may need to serve the files over HTTP (not file://) for the JSON to load properly:

```bash
cd docs
python3 -m http.server 8000
# Then open http://localhost:8000 in your browser
```

The links in the summary page point to `../cenniky/` (relative paths), so the page will work correctly when the folder structure is maintained.

## Data Format

The `data.json` file contains structured data including:
- Manufacturers and their models
- Base prices extracted from PDF content
- Price ranges for models with multiple variants
- Model years, variants, and validity dates
- Statistics (total manufacturers, models, price lists)
