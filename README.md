# JobSpy Web Application (Indeed-Focused)

A powerful web application that uses the JobSpy library to scrape job postings from Indeed and other job boards. Optimized for Indeed searches with exact parameter matching for Jupyter notebook compatibility.

## 🚀 Features

- **Indeed-Optimized Scraping**: Focused on Indeed with best performance and no rate limiting
- **Jupyter Notebook Compatible**: Exact parameter matching with your existing Jupyter workflows
- **Modern Web Interface**: Beautiful, responsive frontend with real-time search
- **RESTful API**: FastAPI backend with comprehensive API documentation
- **Advanced Filtering**: Filter by location, job type, salary, remote work, and more
- **Real-time Results**: Live job search with detailed job information
- **Debug Mode**: Built-in debugging to compare results with direct JobSpy calls
- **Export Capabilities**: Backend supports CSV and Excel export (via API)

## 📁 Project Structure

```
Job6.0/
├── backend/
│   └── main.py              # FastAPI backend application
├── frontend/
│   └── index.html           # Web interface
├── requirements.txt         # Python dependencies
├── test_jobspy_comparison.py # Test script to compare results
├── run.py                  # Easy application launcher
├── .env.example            # Configuration template
└── README.md               # This file
```

## 🛠️ Setup & Installation

### Prerequisites

- Python 3.10 or higher
- pip (Python package installer)

### 1. Clone or Download the Project

```bash
# If you have git
git clone <your-repo-url>
cd Job6.0

# Or just navigate to your project directory
cd Job6.0
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Start the Backend Server

```bash
cd backend
python main.py
```

The API server will start on `http://localhost:8000`

### 4. Open the Frontend

Open `frontend/index.html` in your web browser, or serve it with a simple HTTP server:

```bash
# Option 1: Direct file access
open frontend/index.html

# Option 2: Simple HTTP server (recommended)
cd frontend
python -m http.server 3000
# Then visit http://localhost:3000
```

## 🎯 Usage

### Quick Test (Compare with Jupyter)

```bash
# Test if your parameters work the same way
python test_jobspy_comparison.py
```

This will run the exact same parameters as your Jupyter notebook and compare results with the web API.

### Web Interface

1. Open the frontend in your browser
2. The form is pre-filled with your Jupyter parameters:
   - **Search Term**: "Product Manager Uber" 
   - **Location**: "USA"
   - **Results**: 1000
   - **Hours Old**: 10000
   - **Site**: Indeed only (pre-selected)
3. Click "🚀 Search Jobs"
4. Browse results with detailed job information

### API Usage

The backend provides a REST API that you can use programmatically:

#### Search Jobs

```bash
curl -X POST "http://localhost:8000/search-jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "search_term": "python developer",
    "location": "New York, NY",
    "site_name": ["indeed", "linkedin"],
    "results_wanted": 10,
    "job_type": "fulltime"
  }'
```

#### API Endpoints

- `GET /` - API information and available endpoints
- `POST /search-jobs` - Search for jobs (main functionality)
- `GET /supported-sites` - Get list of supported job sites
- `GET /supported-countries` - Get list of supported countries
- `GET /health` - Health check endpoint
- `GET /docs` - Interactive API documentation (Swagger UI)

## 🔧 Configuration Options

### Search Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `search_term` | string | Job title or keywords | "software engineer" |
| `site_name` | array | Job sites to search | ["indeed", "linkedin", "zip_recruiter"] |
| `location` | string | Geographic location | "San Francisco, CA" |
| `results_wanted` | integer | Number of jobs to retrieve | 20 |
| `distance` | integer | Search radius in miles | 50 |
| `job_type` | string | Employment type | null |
| `is_remote` | boolean | Remote jobs only | null |
| `hours_old` | integer | Max hours since job posted | null |
| `country_indeed` | string | Country for Indeed/Glassdoor | "USA" |
| `easy_apply` | boolean | Easy apply jobs only | null |

### Supported Job Sites

- **indeed** - Best performance, no rate limiting
- **linkedin** - Global search, may require rate limiting
- **glassdoor** - Many countries supported
- **zip_recruiter** - US/Canada only
- **google** - Requires specific search syntax
- **bayt** - International search
- **naukri** - India-focused

### Supported Countries

The application supports 50+ countries for Indeed and Glassdoor, including:
USA, Canada, UK, Australia, Germany, France, India, and many more.

## 📊 Response Format

Job search results include:

```json
{
  "success": true,
  "message": "Successfully found 15 jobs",
  "job_count": 15,
  "jobs": [
    {
      "title": "Senior Software Engineer",
      "company": "Tech Corp",
      "location": "San Francisco, CA",
      "site": "indeed",
      "job_type": "fulltime",
      "job_url": "https://...",
      "description": "...",
      "date_posted": "2025-01-01",
      "min_amount": 120000,
      "max_amount": 180000,
      "interval": "yearly"
    }
  ],
  "search_params": {...},
  "timestamp": "2025-01-14T..."
}
```

## ⚠️ Important Notes

### Rate Limiting

- **LinkedIn**: Most restrictive, usually rate limits around 10th page. Use proxies for heavy usage.
- **Indeed**: Best performance with no rate limiting
- **Others**: Moderate rate limiting, wait between requests if needed

### Best Practices

1. **Start Small**: Begin with fewer results (10-20) to test
2. **Use Specific Terms**: More specific search terms yield better results
3. **Monitor Rate Limits**: If you get 429 errors, wait before retrying
4. **Country Settings**: Set correct country for Indeed/Glassdoor searches

### Troubleshooting

#### "Backend Not Available" Error
- Ensure the backend server is running: `cd backend && python main.py`
- Check that port 8000 is not being used by another application

#### No Results Found
- Try broader search terms
- Check if the selected job sites support your location
- Verify country settings for Indeed/Glassdoor

#### Rate Limiting (429 Errors)
- Reduce the number of results requested
- Add delays between searches
- Try different job sites (Indeed is most reliable)

## 🔒 Security Considerations

- The current setup allows all CORS origins for development
- In production, configure specific allowed origins in `backend/main.py`
- Consider adding authentication for production deployments
- Be mindful of rate limiting and respect job board terms of service

## 📈 Extending the Application

### Adding New Features

1. **Database Storage**: Add SQLite/PostgreSQL to store search results
2. **User Accounts**: Implement user registration and saved searches
3. **Email Alerts**: Send notifications for new matching jobs
4. **Advanced Filters**: Add more sophisticated filtering options
5. **Export Features**: Add CSV/Excel download functionality to frontend

### Custom Development

The backend is built with FastAPI, making it easy to:
- Add new endpoints
- Integrate with databases
- Add authentication
- Deploy to cloud platforms

## 📚 Dependencies

- **FastAPI**: Modern, fast web framework for building APIs
- **JobSpy**: Job scraping library for multiple job boards
- **Uvicorn**: ASGI server for FastAPI
- **Pandas**: Data manipulation and analysis
- **Pydantic**: Data validation using Python type annotations

## 📄 License

This project is for educational and personal use. Please respect the terms of service of the job boards being scraped.

## 🤝 Contributing

Feel free to fork this project and submit pull requests for improvements!

---

**Happy Job Hunting! 🎯** 