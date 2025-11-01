#!/usr/bin/env python3
"""
Generate JSON data and Vue.js HTML summary of price lists from the cenniky folder.
Parses PDF content to extract manufacturer, model, base prices, and validity dates.
"""

import re
import json
from datetime import datetime
from pathlib import Path
from collections import defaultdict

try:
    import pypdf
    PDF_PARSING_AVAILABLE = True
except ImportError:
    PDF_PARSING_AVAILABLE = False
    print("Warning: pypdf not installed. Run: pip install pypdf")


def extract_pdf_text(pdf_path, max_pages=5):
    """Extract text from first few pages of PDF."""
    if not PDF_PARSING_AVAILABLE:
        return ""
    
    try:
        reader = pypdf.PdfReader(pdf_path)
        text = ""
        for i in range(min(max_pages, len(reader.pages))):
            text += reader.pages[i].extract_text() + "\n"
        return text
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
        return ""


def extract_prices_from_text(text):
    """
    Extract base prices from PDF text.
    Looks for patterns like "25 600 €", "47 900 €", etc.
    """
    prices = []
    
    # Pattern for prices: numbers with optional spaces/periods, followed by €
    # Common formats: "25 600 €", "47.900 €", "25600€", etc.
    price_patterns = [
        r'(\d[\d\s.]*\d)\s*€\s*bez\s*DPH',  # "25 600 € bez DPH"
        r'(\d[\d\s.]*\d)\s*€(?!\s*s\s*DPH)',  # "25 600 €" but not "€ s DPH"
    ]
    
    for pattern in price_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            price_str = match.group(1)
            # Remove spaces and dots used as thousand separators
            price_str = price_str.replace(' ', '').replace('.', '')
            try:
                price = int(price_str)
                # Only consider reasonable prices (between 10k and 150k euros)
                if 10000 <= price <= 150000:
                    prices.append(price)
            except ValueError:
                continue
    
    # Remove duplicates and sort
    prices = sorted(set(prices))
    return prices


def extract_variants_from_text(text):
    """Extract model variants from PDF text."""
    variants = []
    
    # Common variant keywords
    variant_patterns = [
        r'\b(Active|Comfort|Premium|Luxury|Sport|Base)\b',
        r'\b(Beach|Coast|Ocean|Edition)\b',
        r'\b(Van|Combi|Kombi|Furgon|Traveller|Crew\s*Van|Crew\s*Cab)\b',
        r'\b(Short|Long|Extra\s*Long|L[123]H[123])\b',
    ]
    
    for pattern in variant_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            variant = match.group(1)
            if variant not in variants:
                variants.append(variant)
    
    return variants[:5]  # Limit to first 5 unique variants


def parse_pdf_content(pdf_path):
    """
    Parse PDF content to extract pricing and variant information.
    Returns dict with extracted data.
    """
    text = extract_pdf_text(pdf_path, max_pages=5)
    
    prices = extract_prices_from_text(text)
    variants = extract_variants_from_text(text)
    
    return {
        'prices': prices,
        'variants': variants,
        'base_price': prices[0] if prices else None,
        'price_range': f"{prices[0]:,} - {prices[-1]:,} €" if len(prices) > 1 else (f"{prices[0]:,} €" if prices else None)
    }


def parse_filename(filename):
    """
    Parse PDF filename to extract make, model, validity date and other info.
    Returns dict with metadata.
    """
    basename = Path(filename).stem
    
    # Remove duplicate markers like (1), (2)
    basename = re.sub(r'\s*\(\d+\)\s*$', '', basename)
    
    metadata = {
        'filename': filename,
        'basename': basename,
        'make': 'Unknown',
        'model': basename,
        'validity_date': None,
        'model_year': None,
        'variant': None
    }
    
    # VW models (Volkswagen)
    if any(model in basename.upper() for model in ['CALIFORNIA', 'CARAVELLE', 'MULTIVAN', 'TRANSPORTER', 'MT7', 'CT7']):
        metadata['make'] = 'Volkswagen'
        
        # Extract model
        if 'CALIFORNIA' in basename.upper() or 'CT7' in basename.upper():
            metadata['model'] = 'California'
        elif 'CARAVELLE' in basename.upper():
            metadata['model'] = 'Caravelle'
        elif 'MULTIVAN' in basename.upper() or 'MT7' in basename.upper():
            metadata['model'] = 'Multivan'
        elif 'TRANSPORTER' in basename.upper():
            metadata['model'] = 'Transporter'
        
        # Extract T7 variant
        if 'T7' in basename.upper():
            metadata['variant'] = 'T7'
        
        # Extract model year (MJ2025, MJ2026)
        mj_match = re.search(r'MJ(\d{4})', basename, re.IGNORECASE)
        if mj_match:
            metadata['model_year'] = mj_match.group(1)
        
        # Extract validity date (various formats)
        # Format: D.M.YYYY or DD.MM.YYYY (try this first as it's more specific with the dots)
        date_match2 = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', basename)
        if date_match2:
            day, month, year = date_match2.groups()
            metadata['validity_date'] = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        else:
            # Format: DDMMYYYY (only if no dotted date found)
            date_match = re.search(r'(\d{2})(\d{2})(\d{4})', basename)
            if date_match:
                day, month, year = date_match.groups()
                metadata['validity_date'] = f"{year}-{month}-{day}"
    
    # Ford models
    elif 'FORD' in basename.upper() or 'TRANSIT' in basename.upper():
        metadata['make'] = 'Ford'
        metadata['model'] = 'Transit Custom'
    
    # Opel/Vauxhall models
    elif 'VIVARO' in basename.upper() or 'ZAFIRA' in basename.upper():
        metadata['make'] = 'Opel'
        
        if 'VIVARO' in basename.upper():
            if 'VAN' in basename.upper():
                metadata['model'] = 'Vivaro Van'
            elif 'COMBI' in basename.upper():
                metadata['model'] = 'Vivaro Combi'
            else:
                metadata['model'] = 'Vivaro'
        elif 'ZAFIRA' in basename.upper():
            metadata['model'] = 'Zafira Life'
    
    # Peugeot Expert
    elif 'EXPERT' in basename.upper():
        metadata['make'] = 'Peugeot'
        
        if 'COMBI' in basename.upper() or 'TRAVELLER' in basename.upper():
            metadata['model'] = 'Expert Combi/Traveller'
        elif 'FURGON' in basename.upper():
            metadata['model'] = 'Expert Furgon'
        else:
            metadata['model'] = 'Expert'
    
    # Toyota ProAce
    elif 'PROACE' in basename.upper():
        metadata['make'] = 'Toyota'
        
        if 'VERSO' in basename.upper():
            if 'EV' in basename.upper():
                metadata['model'] = 'ProAce Verso EV'
            else:
                metadata['model'] = 'ProAce Verso'
        else:
            metadata['model'] = 'ProAce'
    
    # Citroën SpaceTourer
    elif 'SPACE' in basename.upper() and 'TOURER' in basename.upper():
        metadata['make'] = 'Citroën'
        metadata['model'] = 'SpaceTourer'
    
    # Citroën (cennik prefix)
    elif basename.lower().startswith('citroen'):
        metadata['make'] = 'Citroën'
        metadata['model'] = 'SpaceTourer'
    
    return metadata


def generate_html(grouped_data, output_path):
    """
    Generate HTML summary page with embedded CSS.
    """
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Van Price Lists Summary</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.4;
            color: #333;
            background: #f5f5f5;
            padding: 10px;
            font-size: 14px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 4px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.1);
        }
        
        h1 {
            color: #2c3e50;
            margin-bottom: 5px;
            font-size: 1.8em;
            border-bottom: 2px solid #3498db;
            padding-bottom: 8px;
        }
        
        .subtitle {
            color: #7f8c8d;
            margin-bottom: 15px;
            font-size: 0.9em;
        }
        
        .make-section {
            margin-bottom: 20px;
        }
        
        .make-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 8px 12px;
            border-radius: 3px;
            margin-bottom: 10px;
            font-size: 1.2em;
            font-weight: bold;
            box-shadow: 0 1px 4px rgba(0,0,0,0.15);
        }
        
        .model-group {
            margin-bottom: 12px;
            background: #fafafa;
            border-left: 3px solid #3498db;
            padding: 10px;
            border-radius: 2px;
        }
        
        .model-title {
            font-size: 1.1em;
            color: #2c3e50;
            margin-bottom: 8px;
            font-weight: 600;
        }
        
        .price-list {
            list-style: none;
        }
        
        .price-list-item {
            background: white;
            padding: 6px 10px;
            margin-bottom: 4px;
            border-radius: 2px;
            border: 1px solid #e0e0e0;
            transition: all 0.2s ease;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 10px;
        }
        
        .price-list-item:hover {
            border-color: #3498db;
            box-shadow: 0 1px 4px rgba(52, 152, 219, 0.2);
            transform: translateY(-1px);
        }
        
        .price-list-link {
            color: #3498db;
            text-decoration: none;
            font-weight: 500;
            flex-grow: 1;
            font-size: 0.9em;
        }
        
        .price-list-link:hover {
            color: #2980b9;
            text-decoration: underline;
        }
        
        .metadata {
            display: flex;
            gap: 8px;
            color: #7f8c8d;
            font-size: 0.85em;
            flex-wrap: wrap;
        }
        
        .metadata-item {
            display: flex;
            align-items: center;
            gap: 4px;
        }
        
        .badge {
            background: #ecf0f1;
            padding: 2px 6px;
            border-radius: 8px;
            font-size: 0.8em;
            font-weight: 500;
            white-space: nowrap;
        }
        
        .badge.year {
            background: #e8f5e9;
            color: #2e7d32;
        }
        
        .badge.variant {
            background: #e3f2fd;
            color: #1565c0;
        }
        
        .badge.date {
            background: #fff3e0;
            color: #e65100;
        }
        
        .badge.price {
            background: #f3e5f5;
            color: #6a1b9a;
            font-weight: 600;
        }
        
        .footer {
            margin-top: 20px;
            padding-top: 10px;
            border-top: 1px solid #ecf0f1;
            text-align: center;
            color: #7f8c8d;
            font-size: 0.8em;
        }
        
        .stats {
            background: #ecf0f1;
            padding: 8px;
            border-radius: 3px;
            margin-bottom: 15px;
            display: flex;
            justify-content: space-around;
            text-align: center;
        }
        
        .stat-item {
            flex: 1;
        }
        
        .stat-number {
            font-size: 1.4em;
            font-weight: bold;
            color: #3498db;
        }
        
        .stat-label {
            color: #7f8c8d;
            font-size: 0.75em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Van Price Lists Summary</h1>
        <p class="subtitle">Complete overview of all available price lists organized by manufacturer and model</p>
        
"""
    
    # Calculate statistics
    total_files = sum(len(price_lists) for models_dict in grouped_data.values() for price_lists in models_dict.values())
    total_makes = len(grouped_data)
    total_models = sum(len(models_dict) for models_dict in grouped_data.values())
    
    # Add stats section
    html += f"""        <div class="stats">
            <div class="stat-item">
                <div class="stat-number">{total_makes}</div>
                <div class="stat-label">Manufacturers</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{total_models}</div>
                <div class="stat-label">Models</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{total_files}</div>
                <div class="stat-label">Price Lists</div>
            </div>
        </div>
        
"""
    
    # Sort makes alphabetically
    for make in sorted(grouped_data.keys()):
        html += f'        <div class="make-section">\n'
        html += f'            <div class="make-header">{make}</div>\n'
        
        # Sort models alphabetically
        for model in sorted(grouped_data[make].keys()):
            price_lists = grouped_data[make][model]
            
            # Sort by validity date (newest first), then by model year
            price_lists.sort(key=lambda x: (
                x['validity_date'] or '0000-00-00',
                x['model_year'] or '0000'
            ), reverse=True)
            
            html += f'            <div class="model-group">\n'
            html += f'                <div class="model-title">{model}</div>\n'
            html += f'                <ul class="price-list">\n'
            
            for pl in price_lists:
                html += f'                    <li class="price-list-item">\n'
                html += f'                        <a href="../cenniky/{Path(pl["filename"]).name}" class="price-list-link" target="_blank">{pl["basename"]}</a>\n'
                html += f'                        <div class="metadata">\n'
                
                # Display base price if available
                if pl.get('base_price'):
                    html += f'                            <span class="badge price">From {pl["base_price"]:,} €</span>\n'
                elif pl.get('price_range'):
                    html += f'                            <span class="badge price">{pl["price_range"]}</span>\n'
                
                if pl['model_year']:
                    html += f'                            <span class="badge year">MY {pl["model_year"]}</span>\n'
                
                if pl['variant']:
                    html += f'                            <span class="badge variant">{pl["variant"]}</span>\n'
                
                if pl['validity_date']:
                    # Format date nicely
                    try:
                        date_obj = datetime.strptime(pl['validity_date'], '%Y-%m-%d')
                        formatted_date = date_obj.strftime('%d.%m.%Y')
                        html += f'                            <span class="badge date">Valid from {formatted_date}</span>\n'
                    except ValueError:
                        html += f'                            <span class="badge date">{pl["validity_date"]}</span>\n'
                
                html += f'                        </div>\n'
                html += f'                    </li>\n'
            
            html += f'                </ul>\n'
            html += f'            </div>\n'
        
        html += f'        </div>\n'
    
    # Add footer
    current_date = datetime.now().strftime('%B %d, %Y')
    html += f"""        
        <div class="footer">
            <p>Generated on {current_date}</p>
            <p>This page lists all available van price lists from the cenniky folder.</p>
        </div>
    </div>
</body>
</html>
"""
    
    # Write HTML file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"HTML summary generated: {output_path}")


def generate_json_data(grouped_data, output_path):
    """
    Generate JSON data file for use with Vue.js.
    """
    # Convert defaultdict to regular dict for JSON serialization
    json_data = {
        'manufacturers': []
    }
    
    # Sort makes alphabetically
    for make in sorted(grouped_data.keys()):
        make_data = {
            'name': make,
            'models': []
        }
        
        # Sort models alphabetically
        for model in sorted(grouped_data[make].keys()):
            price_lists = grouped_data[make][model]
            
            # Sort by validity date (newest first), then by model year
            price_lists.sort(key=lambda x: (
                x['validity_date'] or '0000-00-00',
                x['model_year'] or '0000'
            ), reverse=True)
            
            model_data = {
                'name': model,
                'priceLists': []
            }
            
            for pl in price_lists:
                price_list_data = {
                    'filename': Path(pl['filename']).name,
                    'basename': pl['basename'],
                    'basePrice': pl.get('base_price'),
                    'priceRange': pl.get('price_range'),
                    'modelYear': pl.get('model_year'),
                    'variant': pl.get('variant'),
                    'validityDate': pl.get('validity_date'),
                    'prices': pl.get('prices', []),
                    'variants': pl.get('variants', [])
                }
                model_data['priceLists'].append(price_list_data)
            
            make_data['models'].append(model_data)
        
        json_data['manufacturers'].append(make_data)
    
    # Add statistics
    json_data['stats'] = {
        'totalManufacturers': len(grouped_data),
        'totalModels': sum(len(models) for models in grouped_data.values()),
        'totalPriceLists': sum(len(price_lists) for models_dict in grouped_data.values() for price_lists in models_dict.values())
    }
    
    # Write JSON file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    print(f"JSON data generated: {output_path}")


def generate_vue_html(output_path):
    """
    Generate JavaScript-based HTML page that loads data from JSON.
    Uses vanilla JavaScript instead of Vue.js to avoid CDN dependency issues.
    """
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Van Price Lists Summary</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.4;
            color: #333;
            background: #f5f5f5;
            padding: 10px;
            font-size: 14px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 4px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.1);
        }
        
        h1 {
            color: #2c3e50;
            margin-bottom: 5px;
            font-size: 1.8em;
            border-bottom: 2px solid #3498db;
            padding-bottom: 8px;
        }
        
        .subtitle {
            color: #7f8c8d;
            margin-bottom: 15px;
            font-size: 0.9em;
        }
        
        .loading {
            text-align: center;
            padding: 20px;
            color: #7f8c8d;
            font-size: 1em;
        }
        
        .error {
            text-align: center;
            padding: 20px;
            color: #e74c3c;
            font-size: 1em;
        }
        
        .stats {
            background: #ecf0f1;
            padding: 8px;
            border-radius: 3px;
            margin-bottom: 15px;
            display: flex;
            justify-content: space-around;
            text-align: center;
        }
        
        .stat-item {
            flex: 1;
        }
        
        .stat-number {
            font-size: 1.4em;
            font-weight: bold;
            color: #3498db;
        }
        
        .stat-label {
            color: #7f8c8d;
            font-size: 0.75em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .make-section {
            margin-bottom: 20px;
        }
        
        .make-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 8px 12px;
            border-radius: 3px;
            margin-bottom: 10px;
            font-size: 1.2em;
            font-weight: bold;
            box-shadow: 0 1px 4px rgba(0,0,0,0.15);
        }
        
        .model-group {
            margin-bottom: 12px;
            background: #fafafa;
            border-left: 3px solid #3498db;
            padding: 10px;
            border-radius: 2px;
        }
        
        .model-title {
            font-size: 1.1em;
            color: #2c3e50;
            margin-bottom: 8px;
            font-weight: 600;
        }
        
        .price-list {
            list-style: none;
        }
        
        .price-list-item {
            background: white;
            padding: 6px 10px;
            margin-bottom: 4px;
            border-radius: 2px;
            border: 1px solid #e0e0e0;
            transition: all 0.2s ease;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 10px;
        }
        
        .price-list-item:hover {
            border-color: #3498db;
            box-shadow: 0 1px 4px rgba(52, 152, 219, 0.2);
            transform: translateY(-1px);
        }
        
        .price-list-link {
            color: #3498db;
            text-decoration: none;
            font-weight: 500;
            flex-grow: 1;
            font-size: 0.9em;
        }
        
        .price-list-link:hover {
            color: #2980b9;
            text-decoration: underline;
        }
        
        .metadata {
            display: flex;
            gap: 8px;
            color: #7f8c8d;
            font-size: 0.85em;
            flex-wrap: wrap;
        }
        
        .badge {
            background: #ecf0f1;
            padding: 2px 6px;
            border-radius: 8px;
            font-size: 0.8em;
            font-weight: 500;
            white-space: nowrap;
        }
        
        .badge.price {
            background: #f3e5f5;
            color: #6a1b9a;
            font-weight: 600;
        }
        
        .badge.year {
            background: #e8f5e9;
            color: #2e7d32;
        }
        
        .badge.variant {
            background: #e3f2fd;
            color: #1565c0;
        }
        
        .badge.date {
            background: #fff3e0;
            color: #e65100;
        }
        
        .footer {
            margin-top: 20px;
            padding-top: 10px;
            border-top: 1px solid #ecf0f1;
            text-align: center;
            color: #7f8c8d;
            font-size: 0.8em;
        }
        
        .hidden {
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Van Price Lists Summary</h1>
        <p class="subtitle">Complete overview of all available price lists organized by manufacturer and model</p>
        
        <div id="loading" class="loading">
            Loading price lists...
        </div>
        
        <div id="error" class="error hidden">
        </div>
        
        <div id="content" class="hidden">
            <div class="stats">
                <div class="stat-item">
                    <div class="stat-number" id="stat-manufacturers">0</div>
                    <div class="stat-label">Manufacturers</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number" id="stat-models">0</div>
                    <div class="stat-label">Models</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number" id="stat-pricelists">0</div>
                    <div class="stat-label">Price Lists</div>
                </div>
            </div>
            
            <div id="manufacturers-container"></div>
            
            <div class="footer">
                <p>Generated on <span id="generation-date"></span></p>
                <p>This page lists all available van price lists from the cenniky folder.</p>
            </div>
        </div>
    </div>

    <script>
        // Format price with thousand separators
        function formatPrice(price) {
            return price.toLocaleString('en-US');
        }
        
        // Format date from YYYY-MM-DD to DD.MM.YYYY
        function formatDate(dateStr) {
            if (!dateStr) return '';
            try {
                const [year, month, day] = dateStr.split('-');
                return `${day}.${month}.${year}`;
            } catch {
                return dateStr;
            }
        }
        
        // Create badge HTML
        function createBadge(className, text) {
            return `<span class="badge ${className}">${text}</span>`;
        }
        
        // Render the price lists
        function renderPriceLists(data) {
            const container = document.getElementById('manufacturers-container');
            let html = '';
            
            data.manufacturers.forEach(manufacturer => {
                html += `<div class="make-section">`;
                html += `<div class="make-header">${manufacturer.name}</div>`;
                
                manufacturer.models.forEach(model => {
                    html += `<div class="model-group">`;
                    html += `<div class="model-title">${model.name}</div>`;
                    html += `<ul class="price-list">`;
                    
                    model.priceLists.forEach(priceList => {
                        html += `<li class="price-list-item">`;
                        html += `<a href="../cenniky/${priceList.filename}" class="price-list-link" target="_blank">${priceList.basename}</a>`;
                        html += `<div class="metadata">`;
                        
                        if (priceList.basePrice) {
                            html += createBadge('price', `From ${formatPrice(priceList.basePrice)} €`);
                        } else if (priceList.priceRange) {
                            html += createBadge('price', priceList.priceRange);
                        }
                        
                        if (priceList.modelYear) {
                            html += createBadge('year', `MY ${priceList.modelYear}`);
                        }
                        
                        if (priceList.variant) {
                            html += createBadge('variant', priceList.variant);
                        }
                        
                        if (priceList.validityDate) {
                            html += createBadge('date', `Valid from ${formatDate(priceList.validityDate)}`);
                        }
                        
                        html += `</div>`;
                        html += `</li>`;
                    });
                    
                    html += `</ul>`;
                    html += `</div>`;
                });
                
                html += `</div>`;
            });
            
            container.innerHTML = html;
        }
        
        // Load data from JSON file
        async function loadData() {
            try {
                const response = await fetch('data.json');
                if (!response.ok) {
                    throw new Error('Failed to load data');
                }
                const data = await response.json();
                
                // Update statistics
                document.getElementById('stat-manufacturers').textContent = data.stats.totalManufacturers;
                document.getElementById('stat-models').textContent = data.stats.totalModels;
                document.getElementById('stat-pricelists').textContent = data.stats.totalPriceLists;
                
                // Update generation date
                const now = new Date();
                document.getElementById('generation-date').textContent = now.toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric'
                });
                
                // Render price lists
                renderPriceLists(data);
                
                // Show content, hide loading
                document.getElementById('loading').classList.add('hidden');
                document.getElementById('content').classList.remove('hidden');
                
            } catch (err) {
                document.getElementById('loading').classList.add('hidden');
                const errorDiv = document.getElementById('error');
                errorDiv.textContent = 'Error loading price list data: ' + err.message;
                errorDiv.classList.remove('hidden');
            }
        }
        
        // Load data when page is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', loadData);
        } else {
            loadData();
        }
    </script>
</body>
</html>
"""
    
    # Write HTML file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"JavaScript HTML generated: {output_path}")


def main():
    """Main function to generate the summary."""
    # Get repository root
    repo_root = Path(__file__).parent
    
    # Get all PDF files from cenniky folder
    cenniky_path = repo_root / 'cenniky'
    pdf_files = sorted(cenniky_path.glob('*.pdf'))
    
    if not pdf_files:
        print("No PDF files found in cenniky folder!")
        return
    
    print(f"Found {len(pdf_files)} PDF files")
    
    if not PDF_PARSING_AVAILABLE:
        print("Warning: PDF parsing not available. Install pypdf: pip install pypdf")
        print("Generating summary with filename-based information only...")
    
    # Parse files (both filename and content)
    all_metadata = []
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"Processing ({i}/{len(pdf_files)}): {pdf_file.name}")
        
        # Parse filename
        relative_path = str(pdf_file.relative_to(repo_root))
        metadata = parse_filename(relative_path)
        
        # Parse PDF content for prices and variants
        if PDF_PARSING_AVAILABLE:
            try:
                pdf_content = parse_pdf_content(pdf_file)
                metadata.update(pdf_content)
            except Exception as e:
                print(f"  Warning: Could not parse PDF content: {e}")
        
        all_metadata.append(metadata)
    
    # Group by make and model
    grouped_data = defaultdict(lambda: defaultdict(list))
    for metadata in all_metadata:
        make = metadata['make']
        model = metadata['model']
        grouped_data[make][model].append(metadata)
    
    # Create docs folder
    docs_path = repo_root / 'docs'
    docs_path.mkdir(exist_ok=True)
    
    # Generate JSON data file
    json_output_file = docs_path / 'data.json'
    generate_json_data(grouped_data, json_output_file)
    
    # Generate JavaScript-based HTML page
    js_output_file = docs_path / 'index.html'
    generate_vue_html(js_output_file)
    
    # Also keep the old server-rendered HTML for comparison
    old_html_file = docs_path / 'index-static.html'
    generate_html(grouped_data, old_html_file)
    
    print(f"\nSummary:")
    print(f"  Total manufacturers: {len(grouped_data)}")
    print(f"  Total models: {sum(len(models) for models in grouped_data.values())}")
    print(f"  JSON data: {json_output_file}")
    print(f"  JavaScript HTML: {js_output_file}")
    print(f"  Static HTML: {old_html_file}")


if __name__ == '__main__':
    main()
