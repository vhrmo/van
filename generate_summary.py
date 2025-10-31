#!/usr/bin/env python3
"""
Generate HTML summary of price lists from the cenniky folder.
Groups by manufacturer, model, and validity start date.
"""

import re
from datetime import datetime
from pathlib import Path
from collections import defaultdict


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
        
        if 'ZAFIRA' in basename.upper():
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


def group_price_lists(pdf_files):
    """
    Group price lists by make and then by model.
    """
    grouped = defaultdict(lambda: defaultdict(list))
    
    for pdf_file in pdf_files:
        metadata = parse_filename(pdf_file)
        make = metadata['make']
        model = metadata['model']
        grouped[make][model].append(metadata)
    
    return grouped


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
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        h1 {
            color: #2c3e50;
            margin-bottom: 10px;
            font-size: 2.5em;
            border-bottom: 3px solid #3498db;
            padding-bottom: 15px;
        }
        
        .subtitle {
            color: #7f8c8d;
            margin-bottom: 30px;
            font-size: 1.1em;
        }
        
        .make-section {
            margin-bottom: 40px;
        }
        
        .make-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 20px;
            border-radius: 6px;
            margin-bottom: 20px;
            font-size: 1.8em;
            font-weight: bold;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        }
        
        .model-group {
            margin-bottom: 25px;
            background: #fafafa;
            border-left: 4px solid #3498db;
            padding: 20px;
            border-radius: 4px;
        }
        
        .model-title {
            font-size: 1.5em;
            color: #2c3e50;
            margin-bottom: 15px;
            font-weight: 600;
        }
        
        .price-list {
            list-style: none;
        }
        
        .price-list-item {
            background: white;
            padding: 15px 20px;
            margin-bottom: 10px;
            border-radius: 4px;
            border: 1px solid #e0e0e0;
            transition: all 0.3s ease;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .price-list-item:hover {
            border-color: #3498db;
            box-shadow: 0 2px 8px rgba(52, 152, 219, 0.2);
            transform: translateY(-2px);
        }
        
        .price-list-link {
            color: #3498db;
            text-decoration: none;
            font-weight: 500;
            flex-grow: 1;
        }
        
        .price-list-link:hover {
            color: #2980b9;
            text-decoration: underline;
        }
        
        .metadata {
            display: flex;
            gap: 15px;
            color: #7f8c8d;
            font-size: 0.9em;
        }
        
        .metadata-item {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        
        .badge {
            background: #ecf0f1;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 500;
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
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #ecf0f1;
            text-align: center;
            color: #7f8c8d;
            font-size: 0.9em;
        }
        
        .stats {
            background: #ecf0f1;
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 30px;
            display: flex;
            justify-content: space-around;
            text-align: center;
        }
        
        .stat-item {
            flex: 1;
        }
        
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #3498db;
        }
        
        .stat-label {
            color: #7f8c8d;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
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
    
    # Parse and group files
    pdf_filenames = [str(pdf.relative_to(repo_root)) for pdf in pdf_files]
    grouped_data = group_price_lists(pdf_filenames)
    
    # Create docs folder
    docs_path = repo_root / 'docs'
    docs_path.mkdir(exist_ok=True)
    
    # Generate HTML
    output_file = docs_path / 'index.html'
    generate_html(grouped_data, output_file)
    
    print(f"\nSummary:")
    print(f"  Total manufacturers: {len(grouped_data)}")
    print(f"  Total models: {sum(len(models) for models in grouped_data.values())}")
    print(f"  Output file: {output_file}")


if __name__ == '__main__':
    main()
