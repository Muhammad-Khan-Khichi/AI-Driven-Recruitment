SKILL_EXTRACTION_PROMPT = """
Analyze this resume and extract:
1. Top 5 job titles the candidate is qualified for
2. Top 10 technical skills (hard skills only)
3. Years of relevant experience
4. Career level: junior / mid / senior

Resume:
{resume_text}

Return ONLY valid JSON (no markdown, no explanation):
{{
    "job_titles": ["title1", "title2", "title3", "title4", "title5"],
    "skills": ["skill1", "skill2"],
    "experience_years": 3,
    "level": "mid"
}}
"""


JOB_RANKING_PROMPT = """
You are a career advisor matching candidates to jobs in Lahore, Pakistan.

Candidate Profile:
- Skills: {skills}
- Best matching roles: {job_titles}
- Experience level: {level}

Below are {num_jobs} jobs found on Indeed and LinkedIn via Pakistan job boards.
Rank the TOP 10 jobs from BEST to WORST match based on skill overlap.

For each job provide:
1. Match score (0-100)
2. Why it's a good fit (1 sentence)
3. Missing skills or requirements (1 sentence)

Format each entry like this:

1. [Job Title] at [Company]
   Match Score: XX/100
   Why: ...
   Missing: ...
   Apply: [URL]

Jobs:
{jobs_text}
"""


COVER_LETTER_PROMPT = """
Write a professional cover letter for this job application.

Candidate Skills: {skills}
Experience Level: {level}
Years of Experience: {years}

Job Details:
- Title: {job_title}
- Company: {company}
- Location: {location}
- Description: {description}

Requirements:
- 3 paragraphs maximum
- Opening: express interest + mention specific role
- Middle: match candidate's skills to job needs with 2-3 concrete examples
- Closing: call to action + sign off
- Professional but enthusiastic tone
- Avoid generic phrases like "I am writing to apply"
- Show knowledge of the company/role
- No placeholder text like [Your Name]

Write the cover letter now:
"""


JOB_ALERT_FILTER_PROMPT = """
You are a job relevance filter. Given candidate skills and a job description,
determine if this job is relevant (score >= 60) or not.

Candidate Skills: {skills}
Target Roles: {job_titles}

Job:
Title: {job_title}
Company: {company}
Description: {description}

Return ONLY valid JSON:
{{
    "match_score": 75,
    "reason": "short reason"
}}
"""