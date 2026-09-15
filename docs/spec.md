# JobRadar — Project Specification

## 1. Project Overview

**JobRadar** is a personal job-post aggregation application.

The initial version focuses exclusively on **Telegram job channels**.

The application will allow the user to configure a list of Telegram channels. The backend will fetch job-related messages posted on selected channels for a particular date, extract the initial "Apply Now" URL, follow intermediate application pages when necessary, identify the final application/career URL, and present the resulting jobs in a React dashboard.

The project is intentionally designed as a personal application rather than a public SaaS product.

---

# 2. V1 Objective

The core objective is:

> Collect job postings from selected Telegram channels for a requested date and provide the final application URL for each job.

Example:

```text
Telegram message
       ↓
Extract Apply Now URL
       ↓
Open intermediate website
       ↓
Find next Apply link
       ↓
Follow it
       ↓
Identify final application/career URL
       ↓
Store job
       ↓
Display job
```

---

# 3. V1 Scope

## Included

- Telegram channel management
- Telegram authentication using Telethon
- Reading messages from selected Telegram channels
- Fetching messages for a specific date
- Job-post detection
- Extraction of job information
- Extraction of initial application URL
- URL redirection handling
- Intermediate webpage parsing
- Apply-link discovery
- JavaScript-heavy page handling through Playwright when required
- Final application URL extraction
- Job storage in Supabase
- React dashboard
- Manual "Fetch Now" functionality
- Fetch status/history
- Basic error handling

## Deferred for Later

- Job deduplication
- Automatic scheduling
- LinkedIn
- WhatsApp
- Naukri
- Indeed
- Other job boards
- Automatic job application submission
- Resume generation
- AI-based resume customization
- Public user registration
- Multi-user SaaS functionality
- Microservices
- Redis
- Celery
- Kubernetes
- Elasticsearch
- Payment systems

---

# 4. Technology Stack

## Frontend

- React
- Vite
- Tailwind CSS

## Backend

- Python
- FastAPI

## Telegram

- Telethon
- Telegram API

## Web Retrieval

- httpx
- BeautifulSoup

## Browser Automation

- Playwright

Playwright should only be used when normal HTTP requests and HTML parsing are insufficient.

## Database

- Supabase
- Supabase PostgreSQL

The application should access Supabase through the backend.

The React frontend must not contain Telegram credentials or other sensitive backend credentials.

---

# 5. High-Level Architecture

```text
                    React + Vite
                         │
                         │ HTTP/REST
                         ▼
                    FastAPI Backend
                         │
          ┌──────────────┼───────────────┐
          │              │               │
          ▼              ▼               ▼
     Telegram       Job Processing    Supabase
     Service             │
          │              │
      Telethon          │
          │              │
          │       ┌──────┴──────┐
          │       │             │
          │      httpx       Playwright
          │       │
          │   BeautifulSoup
          │
          └──────────────────────────────┐
                                         │
                                         ▼
                                    Job Results
```

---

# 6. Backend Responsibilities

FastAPI is the central application layer.

It is responsible for:

- Telegram operations
- Job extraction
- URL resolution
- Supabase operations
- Validation
- Error handling
- Exposing REST APIs

The backend should be organized into services rather than putting all logic into route handlers.

---

# 7. Telegram Service

Telethon is responsible only for Telegram communication.

Responsibilities:

- Authenticate the Telegram user
- Maintain the Telegram session
- Resolve configured channels
- Read channel messages
- Fetch messages for a specified date
- Handle Telegram API errors
- Return raw/normalized Telegram messages to the application

The Telegram service must not contain website scraping logic.

---

# 8. Channel Configuration

The user should be able to configure channels through the application.

Each channel should contain at minimum:

```text
id
channel_username
channel_name
enabled
created_at
updated_at
```

Example:

```text
@fresheroffcampus
@offcampus_jobs
@tech_jobs
```

Only channels marked as enabled should be processed.

The channel list must not be hard-coded throughout the application.

---

# 9. Message Fetching

The application should support:

```text
Fetch messages for a selected date
```

It should support both today's date and a specific historical date for testing.

Example:

```text
GET /api/jobs?date=2026-09-15
```

The fetcher should:

1. Retrieve enabled channels.
2. Fetch messages from each channel.
3. Restrict processing to the requested date.
4. Preserve message metadata.
5. Pass messages to the job-processing pipeline.

Important Telegram message information:

```text
message_id
channel_id
channel_username
message_text
message_date
message_url
```

---

# 10. Job Detection

Not every Telegram message is necessarily a job posting.

The first version should use deterministic/rule-based detection.

Potential signals:

```text
job
hiring
vacancy
developer
engineer
intern
fresher
off campus
walk-in
apply
recruitment
```

The detection system should be designed so that it can later be replaced or supplemented with an AI/LLM classifier.

Do not introduce an LLM in the initial implementation unless required.

---

# 11. Job Information Extraction

For a detected job post, attempt to extract:

```text
title
company
location
experience
qualification
batch
salary/CTC
skills
employment_type
original_apply_url
telegram_channel
telegram_message_id
posted_at
```

Extraction should be tolerant of missing information.

Missing fields should not cause the entire job to fail.

---

# 12. Application URL Extraction

The first application URL is usually present in the Telegram message.

Example:

```text
🔗 Apply Now:
https://www.fresheroffcampus.com/clarivate-off-campus/
```

The system should identify URLs from the message.

Where possible, the application URL should be selected based on surrounding text such as:

```text
Apply
Apply Now
Apply Here
Register
Click Here
Official Link
```

The system should avoid incorrectly selecting unrelated links such as:

```text
WhatsApp Channel
Telegram Channel
Instagram
YouTube
Website homepage
```

---

# 13. URL Resolution

This is a core feature of JobRadar.

Given:

```text
https://www.fresheroffcampus.com/clarivate-off-campus/
```

the resolver should attempt to reach:

```text
https://careers.clarivate.com/...
```

The resolution process should support multiple levels.

## Level 1 — HTTP redirects

Handle:

```text
301
302
303
307
308
```

using normal HTTP requests.

## Level 2 — HTML links

Fetch the webpage and inspect HTML.

Look for links containing text such as:

```text
Apply
Apply Now
Apply Here
Official Apply
Click Here
Register
```

Also inspect common HTML structures such as:

```html
<a href="...">
<button>Apply</button>
```

## Level 3 — JavaScript

If the application link cannot be obtained through normal HTML retrieval, use Playwright.

Playwright should load the page as a browser would and inspect:

- anchors
- buttons
- visible text
- relevant navigation
- resulting URLs

---

# 14. URL Resolver Safety Rules

The resolver must not blindly follow arbitrary links forever.

Requirements:

- Maximum number of resolution steps
- Detect URL cycles
- Detect repeated URLs
- Validate URLs
- Ignore obvious social-media links
- Ignore unrelated navigation links
- Record every URL visited during resolution
- Stop when a likely final application/career URL is reached

Example:

```text
URL A
 ↓
URL B
 ↓
URL C
 ↓
URL C again

STOP — cycle detected
```

A configurable maximum depth should be used, for example:

```text
MAX_RESOLUTION_DEPTH = 5
```

The value should be easy to change.

---

# 15. Final URL Detection

The application should determine whether a URL is likely to be the final application page.

Strong signals include:

- Known employer domain
- Careers domain
- Recruiting platform
- Application form
- Job-detail URL
- Absence of another obvious Apply link

Examples of likely final destinations:

```text
careers.company.com
jobs.company.com
boards.greenhouse.io
jobs.lever.co
workday-based career pages
official company career domains
```

This should be heuristic rather than hard-coded to a small number of companies.

The resolver should preserve uncertainty rather than pretending every URL is guaranteed to be final.

---

# 16. Supabase Data Model

Initial tables:

## channels

```text
id
channel_username
channel_name
enabled
created_at
updated_at
```

## jobs

```text
id
company
title
location
experience
qualification
batch
salary
skills
employment_type
telegram_message_id
telegram_channel
telegram_message_url
original_apply_url
final_apply_url
posted_at
discovered_at
created_at
updated_at
content_hash
```

## fetch_runs

```text
id
started_at
completed_at
requested_date
status
channels_processed
messages_processed
jobs_detected
jobs_saved
errors
```

---

# 17. REST API

Initial API design:

## Channels

```text
GET    /api/channels
POST   /api/channels
PUT    /api/channels/{id}
DELETE /api/channels/{id}
```

## Jobs

```text
GET /api/jobs
GET /api/jobs/{id}
```

Filters should eventually support:

```text
date
channel
company
location
```

## Fetching

```text
POST /api/fetch
GET  /api/fetch/status
GET  /api/fetch/history
```

The API should return clear success/error responses.

---

# 18. React Dashboard

The initial dashboard should contain:

## Header

```text
JobRadar
[Fetch Now]
```

## Summary

```text
Today's Jobs: 27
New Jobs: 19
Channels Processed: 8
```

## Job List

Each job card should display:

```text
Company
Job Title
Location
Experience
Posted Time
Source Channel

[Apply]
```

The Apply button should open the final application URL.

---

# 19. Channel Management UI

Provide a simple page/section:

```text
Telegram Channels

☑ @fresheroffcampus
☑ @offcampus_jobs
☐ @tech_jobs

[+ Add Channel]
```

The user should be able to:

- Add channel
- Remove channel
- Enable/disable channel

---

# 20. Fetch Workflow

When the user clicks:

```text
Fetch Now
```

the backend should:

```text
1. Load enabled channels
2. Fetch requested day's Telegram messages
3. Detect job messages
4. Extract job information
5. Extract initial Apply URL
6. Resolve URL
7. Save jobs to Supabase
8. Return fetch statistics
```

Example response:

```text
Fetch completed

Channels processed: 8
Messages scanned: 347
Job posts detected: 51
Jobs saved: 38
Failed URL resolutions: 4
```

---

# 21. Error Handling

Failures from one channel or website should not terminate the entire fetch operation.

Example:

```text
Channel A → SUCCESS
Channel B → SUCCESS
Channel C → FAILED
Channel D → SUCCESS
```

The system should continue processing A, B, and D.

Similarly:

```text
Job 1 → URL resolved
Job 2 → URL resolved
Job 3 → resolver failed
Job 4 → URL resolved
```

Job 3 should be recorded as a failed resolution rather than crashing the complete process.

---

# 22. Logging

Backend logs should make debugging possible.

Important events:

```text
Fetch started
Channel processing started
Channel processing completed
Messages fetched
Job detected
URL extraction started
URL resolution step
Final URL detected
Job saved
Fetch completed
Error
```

Avoid logging sensitive credentials or Telegram session information.

---

# 23. Security

Sensitive values must be stored in environment variables.

Examples:

```text
TELEGRAM_API_ID
TELEGRAM_API_HASH
SUPABASE_URL
SUPABASE_KEY
```

Do not commit:

```text
.env
Telegram session files
API credentials
Supabase secrets
```

to Git.

The application should use `.gitignore` appropriately.

---

# 24. Future Extensibility

The architecture should make future sources possible.

Current:

```text
Telegram
   ↓
Job Processing Pipeline
```

Future:

```text
Telegram ────────┐
LinkedIn ────────┤
Company Careers ─┤
Job Boards ──────┤
                  ↓
          Common Job Pipeline
                  ↓
              Supabase
                  ↓
               React
```

Therefore Telegram-specific code should be isolated behind a service boundary.

The job-processing pipeline should not depend directly on Telethon.

---

# 25. Development Rules

Every implementation section must:

1. Modify only files necessary for that section.
2. Preserve existing functionality.
3. Avoid introducing libraries unless justified.
4. Use the technologies defined in this specification.
5. Keep the application runnable after each section.
6. Prefer simple implementations over premature abstraction.
7. Avoid unnecessary design patterns.
8. Never expose credentials.
9. Handle partial failures gracefully.
10. Provide clear setup instructions for newly introduced dependencies.

---

# 26. Development Sequence

```text
Section 0
Project Specification
        ↓
Section 1
Project Setup
        ↓
Section 2
Supabase Setup
        ↓
Section 3
Telegram Authentication
        ↓
Section 4
Telegram Channel Management
        ↓
Section 5
Telegram Message Fetching
        ↓
Section 6
Job Detection & Information Extraction
        ↓
Section 7
Application URL Resolver
        ↓
Section 8
Job Storage
        ↓
Section 9
React Dashboard
        ↓
Section 10
Fetch Controls & Status
        ↓
Section 11
Testing, Error Handling & Polish
```

---

# 27. Definition of Success

V1 is successful when the following workflow works end-to-end:

```text
User opens JobRadar
        ↓
Configured Telegram channels exist
        ↓
User clicks "Fetch Now"
        ↓
Telethon reads messages for selected date
        ↓
Job posts are identified
        ↓
Apply URLs are extracted
        ↓
Intermediate Apply pages are followed
        ↓
Final career/application URLs are identified
        ↓
Jobs are saved to Supabase
        ↓
React displays the jobs
        ↓
User clicks Apply
        ↓
Actual application/career page opens
```

The application does not need to automatically apply to jobs.

The user's workflow is reduced from:

```text
Open multiple Telegram channels
→ find relevant posts
→ click Apply
→ click Apply again
→ repeat
```

to:

```text
Open JobRadar
→ see collected jobs
→ click Apply
```

This is the primary purpose of JobRadar V1.

---

# Deferred Features

The following will be designed only after the core V1 works:

### Deduplication

Same job appearing across multiple Telegram channels will eventually be detected and merged.

### Scheduling

Automatic morning/night fetching will eventually be added through APScheduler or another appropriate scheduling mechanism.

### Additional Sources

LinkedIn and other job sources will be added only after the Telegram pipeline is stable.