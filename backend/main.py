from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import pandas as pd
from jobspy import scrape_jobs
import uvicorn
from datetime import datetime
import re
import os
from dotenv import load_dotenv
import json
import asyncio
from openai import OpenAI

# Load environment variables
load_dotenv()

# Initialize OpenAI client
openai_client = None
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-nano")

if OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    print("✅ OpenAI client initialized for AI filtering")
else:
    print("⚠️ OpenAI API key not found. AI filtering will not be available.")

app = FastAPI(
    title="JobSpy API with AI Filtering",
    description="Job scraping API using JobSpy library with OpenAI-powered intelligent filtering",
    version="2.0.0"
)

# Add CORS middleware to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class JobSearchRequest(BaseModel):
    site_name: Optional[List[str]] = ["indeed"]  # Default to Indeed only
    search_term: str = "Product Manager"  # Job title/role only
    company_filter: Optional[str] = None  # Company to filter for (None = no filter)
    location: Optional[str] = "USA"  # Match your Jupyter example
    distance: Optional[int] = 50
    job_type: Optional[str] = None  # fulltime, parttime, internship, contract
    is_remote: Optional[bool] = None
    results_wanted: Optional[int] = 1000  # Match your Jupyter example
    hours_old: Optional[int] = 10000  # Match your Jupyter example
    country_indeed: Optional[str] = "USA"
    easy_apply: Optional[bool] = None
    description_format: Optional[str] = "markdown"
    offset: Optional[int] = 0
    verbose: Optional[int] = 2  # More verbose to help debug

class JobSearchResponse(BaseModel):
    success: bool
    message: str
    job_count: int
    jobs: List[dict]
    search_params: dict
    timestamp: str

# AI Filtering Models
class AIFilterRequest(BaseModel):
    jobs: List[Dict[str, Any]]  # The jobs to filter
    analysis_prompt: str  # What to analyze (e.g., "summarize years of experience required")
    filter_criteria: Optional[str] = None  # How to filter (e.g., "filter jobs requiring 5+ years")

class AIAnalysisResult(BaseModel):
    job_id: int
    job_title: str
    job_company: str
    analysis_result: str  # AI's analysis of this job
    meets_criteria: Optional[bool] = None  # Whether it meets filter criteria

class AIFilterResponse(BaseModel):
    success: bool
    message: str
    original_count: int
    analyzed_jobs: List[AIAnalysisResult]
    filtered_count: Optional[int] = None
    filtered_jobs: Optional[List[Dict[str, Any]]] = None
    timestamp: str

@app.get("/")
async def root():
    return {
        "message": "JobSpy API with AI Filtering is running!", 
        "endpoints": [
            "/docs - API documentation",
            "/search-jobs - Search for jobs",
            "/ai-filter-jobs - AI-powered job analysis and filtering",
            "/supported-sites - Get supported job sites",
            "/supported-countries - Get supported countries",
            "/health - Health check"
        ],
        "ai_features": {
            "available": openai_client is not None,
            "model": OPENAI_MODEL if openai_client else "Not configured"
        }
    }

@app.get("/supported-sites")
async def get_supported_sites():
    """Get list of supported job sites"""
    return {
        "supported_sites": [
            "linkedin",
            "indeed", 
            "glassdoor",
            "zip_recruiter", 
            "google",
            "bayt",
            "naukri"
        ],
        "notes": {
            "linkedin": "Global search, may require rate limiting",
            "indeed": "Best scraper with no rate limiting, supports many countries",
            "glassdoor": "Supports many countries, requires country_indeed parameter",
            "zip_recruiter": "US/Canada only",
            "google": "Requires very specific search syntax in google_search_term",
            "bayt": "International search, uses search_term only",
            "naukri": "India-focused job board"
        }
    }

@app.get("/supported-countries")
async def get_supported_countries():
    """Get list of supported countries for Indeed/Glassdoor"""
    countries = [
        "Argentina", "Australia", "Austria", "Bahrain", "Belgium", "Brazil", 
        "Canada", "Chile", "China", "Colombia", "Costa Rica", "Czech Republic",
        "Denmark", "Ecuador", "Egypt", "Finland", "France", "Germany", "Greece", 
        "Hong Kong", "Hungary", "India", "Indonesia", "Ireland", "Israel", "Italy",
        "Japan", "Kuwait", "Luxembourg", "Malaysia", "Mexico", "Morocco", 
        "Netherlands", "New Zealand", "Nigeria", "Norway", "Oman", "Pakistan",
        "Panama", "Peru", "Philippines", "Poland", "Portugal", "Qatar", "Romania",
        "Saudi Arabia", "Singapore", "South Africa", "South Korea", "Spain", 
        "Sweden", "Switzerland", "Taiwan", "Thailand", "Turkey", "Ukraine",
        "United Arab Emirates", "UK", "USA", "Uruguay", "Venezuela", "Vietnam"
    ]
    return {
        "supported_countries": countries,
        "note": "These countries are supported for Indeed and Glassdoor. LinkedIn searches globally, ZipRecruiter supports US/Canada only."
    }

def filter_jobs_by_company(jobs_df, company_filter):
    """A simplified, stricter filter for companies."""
    if not company_filter or jobs_df is None or jobs_df.empty:
        return jobs_df

    company_filter_clean = company_filter.lower().strip()
    
    print("--- Simplified Company Filtering ---")
    print(f"🎯 Filtering for companies that start with: '{company_filter_clean}'")

    # This prevents errors if the 'company' column contains non-string data
    jobs_df['company'] = jobs_df['company'].astype(str)

    mask = jobs_df['company'].str.lower().str.strip().str.startswith(company_filter_clean, na=False)
    
    filtered_df = jobs_df[mask].copy()
    
    print(f"📊 Before: {len(jobs_df)} jobs. After: {len(filtered_df)} jobs.")
    print("---------------------------------")
    return filtered_df

@app.post("/search-jobs", response_model=JobSearchResponse)
async def search_jobs(request: JobSearchRequest):
    """Search for jobs using JobSpy"""
    try:
        # Prepare search term - append company for better search results ONLY if company filter is provided
        actual_search_term = request.search_term
        if request.company_filter and request.company_filter.strip():
            actual_search_term = f"{request.search_term} {request.company_filter}".strip()
            print(f"🔍 Company filter provided: '{request.company_filter}' - will filter results")
        else:
            print("🔍 No company filter - will show all companies")
        
        # Prepare parameters for JobSpy
        search_params = {
            "site_name": request.site_name,
            "search_term": actual_search_term,  # Use combined search term
            "location": request.location,
            "distance": request.distance,
            "job_type": request.job_type,
            "is_remote": request.is_remote,
            "results_wanted": request.results_wanted,
            "hours_old": request.hours_old,
            "country_indeed": request.country_indeed,
            "easy_apply": request.easy_apply,
            "description_format": request.description_format,
            "offset": request.offset,
            "verbose": request.verbose
        }
        
        # Remove None values
        search_params = {k: v for k, v in search_params.items() if v is not None}
        
        # Debug: Print exact parameters being sent to JobSpy
        print(f"🔍 Original search term: '{request.search_term}'")
        print(f"🏢 Company filter: '{request.company_filter}'")
        print(f"🔍 Actual search term sent to JobSpy: '{actual_search_term}'")
        print(f"📋 JobSpy Parameters: {search_params}")
        
        # Call JobSpy
        jobs_df = scrape_jobs(**search_params)
        
        # Debug: Print initial result info
        if jobs_df is not None and not jobs_df.empty:
            print(f"✅ JobSpy returned {len(jobs_df)} jobs initially")
            
            # Apply company filter if specified
            if request.company_filter and request.company_filter.strip():
                jobs_df = filter_jobs_by_company(jobs_df, request.company_filter)
            
            print(f"📊 Final job count after filtering: {len(jobs_df)}")
            print(f"📊 Columns: {list(jobs_df.columns)}")
        else:
            print("❌ JobSpy returned no results")
        
        # Convert DataFrame to list of dictionaries
        if jobs_df is not None and not jobs_df.empty:
            jobs_list = jobs_df.to_dict('records')
            
            # Clean up any NaN values
            for job in jobs_list:
                for key, value in job.items():
                    if pd.isna(value):
                        job[key] = None
            
            # Add search info to response
            filter_info = ""
            if request.company_filter:
                filter_info = f" (filtered for company: {request.company_filter})"
            
            return JobSearchResponse(
                success=True,
                message=f"Successfully found {len(jobs_list)} jobs{filter_info}",
                job_count=len(jobs_list),
                jobs=jobs_list,
                search_params={**search_params, "company_filter": request.company_filter},
                timestamp=datetime.now().isoformat()
            )
        else:
            filter_info = ""
            if request.company_filter:
                filter_info = f" for company '{request.company_filter}'"
            
            return JobSearchResponse(
                success=True,
                message=f"No jobs found matching your criteria{filter_info}",
                job_count=0,
                jobs=[],
                search_params={**search_params, "company_filter": request.company_filter},
                timestamp=datetime.now().isoformat()
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error scraping jobs: {str(e)}"
        )

# AI Filtering Functions
async def analyze_job_with_ai(job: Dict[str, Any], analysis_prompt: str, job_id: int, client) -> AIAnalysisResult:
    """Analyze a single job using OpenAI"""
    
    # Prepare job information for analysis
    job_info = {
        "title": job.get("title", "N/A"),
        "company": job.get("company", "N/A"),
        "location": job.get("location", "N/A"),
        "description": job.get("description", "N/A")[:2000],  # Limit description length
        "job_type": job.get("job_type", "N/A"),
        "salary_min": job.get("min_amount", "N/A"),
        "salary_max": job.get("max_amount", "N/A"),
        "date_posted": job.get("date_posted", "N/A")
    }
    
    prompt = f"""
    Analyze this job posting based on the following request: "{analysis_prompt}"
    
    Job Information:
    - Title: {job_info['title']}
    - Company: {job_info['company']}
    - Location: {job_info['location']}
    - Type: {job_info['job_type']}
    - Salary: ${job_info['salary_min']} - ${job_info['salary_max']}
    - Posted: {job_info['date_posted']}
    - Description: {job_info['description']}
    
    Please provide a concise analysis (max 100 words) that directly answers the request.
    If asking about years of experience, extract the specific number or range.
    If asking about skills, list the key technical skills mentioned.
    If asking about salary, provide the compensation details.
    
    Response format: Provide only the direct answer to the analysis request.
    """
    
    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.1
        )
        
        analysis_result = response.choices[0].message.content.strip()
        
        return AIAnalysisResult(
            job_id=job_id,
            job_title=job_info['title'],
            job_company=job_info['company'],
            analysis_result=analysis_result
        )
    except Exception as e:
        return AIAnalysisResult(
            job_id=job_id,
            job_title=job_info['title'],
            job_company=job_info['company'],
            analysis_result=f"Analysis failed: {str(e)}"
        )

async def filter_jobs_with_ai(analyzed_jobs: List[AIAnalysisResult], filter_criteria: str, client) -> List[AIAnalysisResult]:
    """Apply AI filtering to analyzed jobs"""
    if not filter_criteria:
        # If no filtering criteria, return all jobs
        for job in analyzed_jobs:
            job.meets_criteria = True
        return analyzed_jobs
    
    # Prepare all analysis results for batch filtering
    analyses_text = "\n".join([
        f"Job {job.job_id}: {job.job_title} at {job.job_company} - Analysis: {job.analysis_result}"
        for job in analyzed_jobs
    ])
    
    prompt = f"""
    Based on the following job analyses, determine which jobs meet this criteria: "{filter_criteria}"
    
    Job Analyses:
    {analyses_text}
    
    For each job, respond with ONLY the job ID followed by either "YES" or "NO".
    Format: "Job 1: YES" or "Job 1: NO"
    
    Example response:
    Job 1: YES
    Job 2: NO
    Job 3: YES
    """
    
    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.1
        )
        
        filter_result = response.choices[0].message.content.strip()
        
        # Parse the filtering results
        filter_decisions = {}
        for line in filter_result.split('\n'):
            if ':' in line and ('YES' in line or 'NO' in line):
                try:
                    job_part, decision = line.split(':', 1)
                    job_id = int(job_part.strip().replace('Job', '').strip())
                    meets_criteria = 'YES' in decision.upper()
                    filter_decisions[job_id] = meets_criteria
                except:
                    continue
        
        # Apply filtering decisions
        for job in analyzed_jobs:
            job.meets_criteria = filter_decisions.get(job.job_id, False)
        
        return analyzed_jobs
        
    except Exception as e:
        # If filtering fails, mark all as not meeting criteria
        for job in analyzed_jobs:
            job.meets_criteria = False
        return analyzed_jobs

@app.post("/ai-filter-jobs", response_model=AIFilterResponse)
async def ai_filter_jobs(request: AIFilterRequest, http_request: Request):
    """Apply AI-powered analysis and filtering to job search results"""
    try:
        # Get API key from request header or fallback to environment
        api_key = http_request.headers.get("X-OpenAI-API-Key") or OPENAI_API_KEY
        
        if not api_key:
            raise HTTPException(
                status_code=400, 
                detail="OpenAI API key is required. Please provide it in the X-OpenAI-API-Key header or configure OPENAI_API_KEY in your environment."
            )
        
        # Initialize OpenAI client with the provided API key
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        start_time = datetime.now()
        original_count = len(request.jobs)
        
        if original_count == 0:
            return AIFilterResponse(
                success=True,
                message="No jobs provided for analysis",
                original_count=0,
                analyzed_jobs=[],
                timestamp=start_time.isoformat()
            )
        
        print(f"🤖 Starting AI analysis of {original_count} jobs...")
        print(f"📝 Analysis prompt: {request.analysis_prompt}")
        if request.filter_criteria:
            print(f"🔍 Filter criteria: {request.filter_criteria}")
        
        # Step 1: Analyze each job with AI
        analysis_tasks = [
            analyze_job_with_ai(job, request.analysis_prompt, i, client)
            for i, job in enumerate(request.jobs)
        ]
        
        # Process in batches to avoid rate limits (adjust batch size as needed)
        batch_size = 5
        analyzed_jobs = []
        
        for i in range(0, len(analysis_tasks), batch_size):
            batch = analysis_tasks[i:i + batch_size]
            batch_results = await asyncio.gather(*batch)
            analyzed_jobs.extend(batch_results)
            
            # Small delay between batches to respect rate limits
            if i + batch_size < len(analysis_tasks):
                await asyncio.sleep(1)
        
        print(f"✅ Completed analysis of {len(analyzed_jobs)} jobs")
        
        # Step 2: Apply filtering if criteria provided
        filtered_jobs = None
        filtered_count = None
        
        if request.filter_criteria:
            print("🔍 Applying AI filtering...")
            analyzed_jobs = await filter_jobs_with_ai(analyzed_jobs, request.filter_criteria, client)
            
            # Extract jobs that meet criteria
            jobs_meeting_criteria = [
                job for job in analyzed_jobs if job.meets_criteria
            ]
            
            if jobs_meeting_criteria:
                filtered_jobs = [
                    request.jobs[job.job_id] for job in jobs_meeting_criteria
                ]
                filtered_count = len(filtered_jobs)
            else:
                filtered_jobs = []
                filtered_count = 0
            
            print(f"🎯 Filtered to {filtered_count} jobs meeting criteria")
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        message = f"Successfully analyzed {original_count} jobs in {duration:.1f} seconds"
        if filtered_count is not None:
            message += f" and filtered to {filtered_count} jobs"
        
        return AIFilterResponse(
            success=True,
            message=message,
            original_count=original_count,
            analyzed_jobs=analyzed_jobs,
            filtered_count=filtered_count,
            filtered_jobs=filtered_jobs,
            timestamp=end_time.isoformat()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error in AI filtering: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 