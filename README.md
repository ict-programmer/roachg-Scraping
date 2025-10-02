# RoachAg Blog Scraper

A Python web scraper that extracts blog posts from [RoachAg.com Resources](https://roachag.com/Resources) and formats them for WordPress import using All-in-One WP Migration.

## 🎯 Project Overview

This tool scrapes agricultural blog posts from RoachAg's Resources section and converts them into WordPress-compatible format. It successfully extracts **79+ posts** with images, metadata, and content in the exact format required for WordPress migration.

## ✨ Features

- **Automated Scraping**: Scrapes multiple pages (1-8) of RoachAg Resources
- **Content Extraction**: Extracts titles, dates, categories, tags, and full HTML content
- **Image Handling**: Captures featured images and processes image URLs
- **WordPress Ready**: Outputs in All-in-One WP Migration format
- **Deduplication**: Prevents duplicate posts across pages
- **Error Handling**: Robust retry logic and graceful error handling
- **Multiple Formats**: Exports to both Excel (.xlsx) and CSV formats

## 🚀 Quick Start

### Prerequisites

- Python 3.12+ (tested on 3.12/3.13)
- Windows (Git Bash/CMD/PowerShell)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/roachag-scraper.git
   cd roachag-scraper
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

### Usage

**Run the scraper:**
```bash
python posts_scraper.py
```

**Output files:**
- `roachag_blog_posts_YYYYMMDD_HHMMSS.xlsx` - Excel format
- `roachag_blog_posts_YYYYMMDD_HHMMSS.csv` - CSV format

## 📊 Data Structure

The scraper extracts the following fields for each post:

| Field | Description |
|-------|-------------|
| `source_url` | Original RoachAg post URL |
| `post_title` | Blog post title |
| `post_slug` | URL-friendly slug |
| `post_status` | WordPress status (draft) |
| `post_author` | Author (admin) |
| `post_date` | Publication date (ISO format) |
| `categories` | Post category |
| `tags` | Comma-separated tags |
| `content_html` | Full HTML content |
| `featured_image_url` | Featured image URL |
| `meta__source` | Source identifier |

## 🔧 Configuration

### Customizing Pages to Scrape

Edit the `LISTING_PAGES` list in `posts_scraper.py`:

```python
LISTING_PAGES = [
    "https://roachag.com/Resources/BlogPage/1",
    "https://roachag.com/Resources/BlogPage/2", 
    # Add more pages as needed
]
```

### Adjusting Scraping Behavior

- **Delay between requests**: Modify `DELAY = 0.7` (seconds)
- **Retry attempts**: Adjust retry settings in `make_session()`
- **Content filtering**: Update `BAD_SLUGS` to exclude unwanted sections

## 📁 Project Structure

```
roachag-scraper/
├── posts_scraper.py          # Main scraper script
├── requirements.txt          # Python dependencies
├── .gitignore               # Git ignore rules
├── README.md               # This file
└── venv/                   # Virtual environment (excluded)
```

## 🛠️ Technical Details

### Dependencies

- `requests` - HTTP requests with retry logic
- `beautifulsoup4` - HTML parsing
- `pandas` - Data manipulation and export
- `lxml` - Fast XML/HTML parser
- `openpyxl` - Excel file generation

### Scraping Strategy

1. **Page Discovery**: Scrapes listing pages to find post URLs
2. **Content Extraction**: Parses individual posts for metadata and content
3. **Data Cleaning**: Normalizes dates, URLs, and text content
4. **Deduplication**: Prevents duplicate posts across pages
5. **Export**: Generates WordPress-compatible output files

### Error Handling

- **Network Issues**: Automatic retries with exponential backoff
- **Parsing Errors**: Graceful handling of malformed HTML
- **Missing Data**: Fallback values for optional fields
- **Rate Limiting**: Built-in delays between requests

## 📈 Results

- **Total Posts**: 79+ agricultural blog posts
- **Content Types**: Market analysis, crop reports, weather updates
- **Images**: Featured images and inline content images
- **Categories**: USDA Supply/Demand, market analysis, crop updates
- **Success Rate**: High reliability with robust error handling

## 🔄 WordPress Migration

1. **Export Data**: Run the scraper to generate Excel/CSV files
2. **All-in-One WP Migration**: Use the generated files with the plugin
3. **Import to WordPress**: Follow the plugin's import process
4. **Review Content**: Verify posts, images, and metadata

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For issues and questions:
- Create an issue in this repository
- Check the troubleshooting section below

## 🔍 Troubleshooting

### Common Issues

**Permission Denied on Output Files**
- Close Excel/CSV files before running the scraper
- Files are timestamped to avoid conflicts

**Network Timeouts**
- Increase timeout values in `get_html()` function
- Check internet connection

**Missing Posts**
- Verify the target website structure hasn't changed
- Check if pages are accessible in browser

**Empty Content**
- Some posts may be filtered out if they lack body content or dates
- Check the `BAD_SLUGS` list for excluded sections

---

**Client**: USA Agricultural Client  
**Source**: [RoachAg.com Resources](https://roachag.com/Resources)  
**Target**: WordPress via All-in-One WP Migration  
**Status**: ✅ Production Ready