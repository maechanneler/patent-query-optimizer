# Patent Query Optimizer

A Python tool for optimizing patent search queries and achieving more efficient patent searches. Utilizes Google Patents API and OpenAI API to optimize search queries and evaluate search results.

## Features

- Automatic optimization of patent search queries
- Automatic evaluation of search results  
- Search history storage and management
- Caching of highly relevant patent information
- Priority search for Japanese patents
- Stepwise query improvement process

## Requirements

- Python 3.8+
- OpenAI API key
- SerpAPI key

## Installation

1. Clone the repository:
```bash
git clone https://github.com/maechanneler/patent-query-optimizer.git
cd patent-query-optimizer
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # For Unix-like systems
# or
venv\Scripts\activate  # For Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file with the following content:
```
OPENAI_API_KEY=your_openai_api_key
SERPAPI_KEY=your_serpapi_key
```

## Project Structure

```
.
├── config/         # Configuration files
├── results/        # Search results output directory
├── src/           # Source code
│   ├── run_patent_search.py        # Main execution script
│   └── simplified_patent_search.py  # Core patent search logic
├── tests/         # Test code
└── requirements.txt  # List of dependencies
```

## Usage

Basic search:
```bash
python src/run_patent_search.py --query "autonomous driving AND sensor"
```

Search with query optimization:
```bash
python src/run_patent_search.py --query "autonomous driving AND sensor" --optimize --iterations 3
```

### Command Line Options

- `--query`: Search query (required)
- `--optimize`: Enable query optimization
- `--results`: Number of search results to retrieve (default: 100)
- `--debug`: Enable debug logging
- `--iterations`: Number of optimization iterations (default: 3)
- `--show-cache`: Display cached patent information after execution

## Caching Feature

- The most relevant patent information from search results is automatically cached
- Cache is stored in `patent_cache.json`
- Use `--show-cache` option to view current cache contents

## Search History

- History of each search session is saved in the `search_history` directory
- History includes queries, result counts, and evaluation results

## Important Notes

- Be mindful of API usage limits
- Set appropriate waiting times when making multiple search requests
- Regular cache clearing is recommended

## Core Components

### run_patent_search.py
- Main script for executing patent searches
- Handles command-line arguments
- Manages search iterations and optimization
- Saves search history and results

### simplified_patent_search.py
- Implements core search functionality
- Handles API interactions
- Manages patent caching
- Performs query optimization and result evaluation

## API Integration

The tool integrates with two main APIs:
- Google Patents API (via SerpAPI) for patent searches
- OpenAI API for query optimization and result evaluation

## License

MIT License

## Contributing

Please feel free to submit bug reports or feature improvement suggestions through GitHub Issues.
