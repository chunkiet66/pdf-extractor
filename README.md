# PDF Amount Extractor

Extracts "Total Amount (USD)" or "Total Amount (CAD)" values from PDF files and exports them to CSV with automatic USD to CAD currency conversion using historical exchange rates.

## Installation

1. Clone the repository:
```bash
git clone https://github.com/chunkiet66/pdf-extractor.git
cd pdf-extractor
```

2. Install dependencies:
```bash
pip install pdfplumber requests
```

## Usage

Run the script with a folder path containing your PDF files:

```bash
python pdf_amount_extractor.py /path/to/pdf/folder
```

Or run from the current directory:

```bash
python pdf_amount_extractor.py
```

## PDF File Requirements

### Naming Convention
PDF files must follow one of these naming patterns:
- `YYYY-MM-DD.pdf` (e.g., `2025-01-15.pdf`)
- `YYYY-MM-DD (x).pdf` for multiple files on the same date (e.g., `2025-01-15 (2).pdf`)

### Content Format
The script searches for text matching:
- `Total Amount (USD)` followed by a dollar value
- `Total Amount (CAD)` followed by a dollar value

Supported value formats: `$1,234.56`, `1234.56`, `$1234`

## Output

The script generates `extracted_amounts.csv` in the target folder with the following columns:

| Column | Description |
|--------|-------------|
| date | Date from filename (YYYY-MM-DD) |
| occurrence | Occurrence number (1 for first/only file, 2+ for duplicates) |
| USD | Original USD amount (empty if originally CAD) |
| CAD | CAD amount (converted if USD, original if CAD) |
| amount | Final amount in CAD |
| rate | USD to CAD exchange rate used (empty if originally CAD) |

### Example Output

```csv
date,occurrence,USD,CAD,amount,rate
2025-01-15,1,100.00,143.25,143.25,1.4325
2025-01-16,1,,200.00,200.00,
2025-01-16,2,50.00,71.50,71.50,1.4300
```

## Currency Conversion

- USD amounts are automatically converted to CAD using historical exchange rates
- Exchange rates are fetched from the [Frankfurter API](https://www.frankfurter.app/) (free, no API key required)
- The rate used is based on the date in the PDF filename
- Rates are cached to avoid redundant API calls

## License

MIT
