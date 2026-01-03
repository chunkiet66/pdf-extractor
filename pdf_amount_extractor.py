#!/usr/bin/env python3
"""
PDF Amount Extractor
Reads PDF files named YYYY-MM-DD.pdf from a folder and extracts
'Total Amount (USD)' or 'Total Amount (CAD)' values.
"""

import os
import re
import csv
import requests
import pdfplumber
from pathlib import Path
from typing import Dict, Optional, Tuple
from functools import lru_cache


@lru_cache(maxsize=365)
def get_usd_to_cad_rate(date_str: str) -> Optional[float]:
    """
    Fetch the USD to CAD exchange rate for a specific date.
    Uses the Frankfurter API (free, no API key required).

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        Exchange rate (USD to CAD) or None if not available
    """
    try:
        url = f"https://api.frankfurter.app/{date_str}?from=USD&to=CAD"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data['rates']['CAD']
        else:
            print(f"  Warning: Could not fetch rate for {date_str}")
            return None
    except Exception as e:
        print(f"  Warning: Error fetching rate for {date_str}: {e}")
        return None


def extract_amount_from_pdf(pdf_path: str) -> Optional[Tuple[float, str]]:
    """
    Extract the total amount and currency from a PDF file.
    
    Returns:
        Tuple of (amount, currency) or None if not found
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            full_text = ""
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
            
            # Pattern to match "Total Amount (USD)" or "Total Amount (CAD)" followed by a dollar value
            # Handles formats like: $1,234.56 or 1234.56 or $1234
            patterns = [
                # Pattern: Total Amount (USD): $1,234.56 or Total Amount (USD) $1,234.56
                r'Total\s+Amount\s*\((USD|CAD)\)\s*[:\s]*\$?\s*([\d,]+\.?\d*)',
                # Pattern: Total Amount (USD) ... $1,234.56 (on same or nearby line)
                r'Total\s+Amount\s*\((USD|CAD)\)[^\d$]*\$?\s*([\d,]+\.?\d*)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    currency = match.group(1).upper()
                    amount_str = match.group(2).replace(',', '')
                    amount = float(amount_str)
                    return (amount, currency)
            
            return None
            
    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")
        return None


def process_pdf_folder(folder_path: str) -> Dict[str, dict]:
    """
    Process all PDF files in a folder that match the YYYY-MM-DD.pdf or YYYY-MM-DD (x).pdf naming pattern.
    
    Args:
        folder_path: Path to the folder containing PDF files
        
    Returns:
        Dictionary with date (and optional occurrence) as key and {'amount': float, 'currency': str} as value
        Keys are formatted as:
          - "2025-01-01" for single occurrence or first occurrence
          - "2025-01-01 (2)" for second occurrence on same day, etc.
    """
    results = {}
    folder = Path(folder_path)
    
    # Pattern for YYYY-MM-DD.pdf or YYYY-MM-DD (x).pdf filename
    # Matches: 2025-01-01.pdf, 2025-01-01 (2).pdf, 2025-01-01 (10).pdf
    date_pattern = re.compile(r'^(\d{4}-\d{2}-\d{2})(?:\s*\((\d+)\))?\.pdf$', re.IGNORECASE)
    
    if not folder.exists():
        print(f"Folder not found: {folder_path}")
        return results
    
    pdf_files = list(folder.glob('*.pdf'))
    
    if not pdf_files:
        print(f"No PDF files found in: {folder_path}")
        return results
    
    for pdf_path in sorted(pdf_files):
        filename = pdf_path.name
        match = date_pattern.match(filename)
        
        if match:
            date_str = match.group(1)
            occurrence = match.group(2)  # None if no (x) in filename
            
            # Create the key: "2025-01-01" or "2025-01-01 (2)"
            if occurrence:
                key = f"{date_str} ({occurrence})"
            else:
                key = date_str
            
            print(f"Processing: {filename}")
            
            result = extract_amount_from_pdf(str(pdf_path))
            
            if result:
                amount, currency = result
                results[key] = {
                    'amount': amount,
                    'currency': currency,
                    'date': date_str,  # Store the base date for easier grouping
                    'occurrence': int(occurrence) if occurrence else 1
                }
                print(f"  → Found: ${amount:,.2f} {currency}")
            else:
                print(f"  → No 'Total Amount' found")
        else:
            print(f"Skipping (doesn't match YYYY-MM-DD.pdf or YYYY-MM-DD (x).pdf): {filename}")
    
    return results


def convert_results_to_cad(results: Dict[str, dict]) -> Dict[str, dict]:
    """
    Convert all USD amounts to CAD using historical exchange rates.

    Args:
        results: Dictionary of extraction results

    Returns:
        Dictionary with converted results including USD and CAD columns
    """
    converted = {}

    for key, data in results.items():
        date_str = data['date']
        amount = data['amount']
        currency = data['currency']

        if currency == 'USD':
            print(f"  Fetching exchange rate for {date_str}...")
            rate = get_usd_to_cad_rate(date_str)
            if rate:
                cad_amount = amount * rate
                converted[key] = {
                    'date': date_str,
                    'occurrence': data['occurrence'],
                    'USD': amount,
                    'CAD': cad_amount,
                    'amount': cad_amount,
                    'rate': rate
                }
                print(f"    {amount:.2f} USD × {rate:.4f} = {cad_amount:.2f} CAD")
            else:
                # If rate not available, keep USD amount as-is
                converted[key] = {
                    'date': date_str,
                    'occurrence': data['occurrence'],
                    'USD': amount,
                    'CAD': None,
                    'amount': None,
                    'rate': None
                }
        else:  # CAD
            converted[key] = {
                'date': date_str,
                'occurrence': data['occurrence'],
                'USD': None,
                'CAD': amount,
                'amount': amount,
                'rate': None
            }

    return converted


def save_results_to_csv(results: Dict[str, dict], output_path: str) -> None:
    """
    Save extraction results to a CSV file.

    Args:
        results: Dictionary of extraction results (already converted)
        output_path: Path to the output CSV file
    """
    with open(output_path, 'w', newline='') as csvfile:
        fieldnames = ['date', 'occurrence', 'USD', 'CAD', 'amount', 'rate']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for key, data in sorted(results.items()):
            writer.writerow({
                'date': data['date'],
                'occurrence': data['occurrence'],
                'USD': f"{data['USD']:.2f}" if data['USD'] is not None else '',
                'CAD': f"{data['CAD']:.2f}" if data['CAD'] is not None else '',
                'amount': f"{data['amount']:.2f}" if data['amount'] is not None else '',
                'rate': f"{data['rate']:.4f}" if data['rate'] is not None else ''
            })

    print(f"Results saved to: {output_path}")


def main():
    """Main entry point."""
    import sys
    
    # Default folder path (current directory)
    folder_path = sys.argv[1] if len(sys.argv) > 1 else "."
    
    print(f"=" * 50)
    print("PDF Amount Extractor")
    print(f"=" * 50)
    print(f"Scanning folder: {os.path.abspath(folder_path)}")
    print()
    
    # Process PDFs
    results = process_pdf_folder(folder_path)
    
    # Display results
    print()
    print(f"=" * 50)
    print("Results Summary")
    print(f"=" * 50)
    
    if results:
        print(f"\nFound {len(results)} file(s) with amounts:\n")
        for key, data in sorted(results.items()):
            print(f"  {key}: ${data['amount']:,.2f} {data['currency']}")
        
        # Calculate totals by currency
        totals = {}
        for data in results.values():
            currency = data['currency']
            totals[currency] = totals.get(currency, 0) + data['amount']
        
        print(f"\nTotals by currency:")
        for currency, total in sorted(totals.items()):
            print(f"  {currency}: ${total:,.2f}")
        
        # Group by date summary
        date_totals = {}
        for data in results.values():
            date = data['date']
            currency = data['currency']
            key = (date, currency)
            date_totals[key] = date_totals.get(key, 0) + data['amount']
        
        print(f"\nDaily totals:")
        for (date, currency), total in sorted(date_totals.items()):
            print(f"  {date}: ${total:,.2f} {currency}")

        # Convert USD to CAD
        print(f"\n" + "=" * 50)
        print("Converting USD to CAD...")
        print("=" * 50)
        converted_results = convert_results_to_cad(results)

        # Save to CSV
        csv_output = os.path.join(folder_path, "extracted_amounts.csv")
        save_results_to_csv(converted_results, csv_output)
    else:
        print("\nNo amounts extracted.")

    print()
    return results


if __name__ == "__main__":
    main()
