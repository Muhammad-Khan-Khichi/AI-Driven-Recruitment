
"""
Resume Optimizer: Compare resume to a job description and suggest improvements.
Uses Mistral AI to analyze ATS compatibility, missing keywords, weak bullets.
"""
import json
import re
from typing import Dict, List, Optional

from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate


from config.settings import settings


class ResumeOptimizer:
    """Analyze resume vs job description and return actionable suggestions."""
    
    def __init__(self):
        self.llm = ChatMistralAI(
            model="mistral-small-latest",
            api_key=settings.MISTRAL_API_KEY,
            temperature=0.3
        )
    
    def optimize(
        self,
        resume_text: str,
        job_description: str,
        job_title: Optional[str] = None
    ) -> Dict:
        """
        Optimize resume for a specific job.
        """
        # 1. Extract keywords from job description (rule-based)
        job_keywords = self._extract_keywords(job_description)
        resume_keywords = set(self._extract_keywords(resume_text).keys())
        
        missing = []
        for kw, _ in job_keywords.items():
            if isinstance(kw, str) and kw.lower() not in resume_keywords:
                missing.append(kw)
        
        # 2. Get AI-powered suggestions
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert resume coach and ATS specialist.
            Analyze the resume against the job description and provide actionable feedback.
            Be specific, honest, and constructive. Focus on improvements that increase interview chances.
            Always return valid JSON only, no other text."""),
            ("user", """Resume:
            {resume}
            
            Job Title: {job_title}
            Job Description:
            {job_description}
            
            Provide your analysis as JSON with this EXACT structure:
            {{
                "ats_score": <integer 0-100>,
                "missing_keywords": ["keyword1", "keyword2"],
                "weak_bullets": ["weak bullet text - reason why it's weak"],
                "suggested_bullets": ["improved bullet point 1", "improved bullet point 2"],
                "strengths": ["strong point 1", "strong point 2"],
                "gaps": ["gap to address 1"],
                "summary": "2-3 sentence overall assessment"
            }}
            
            Return ONLY valid JSON, no markdown, no explanation.""")
        ])
        
        try:
            chain = prompt | self.llm
            response = chain.invoke({
                "resume": resume_text[:3000],
                "job_title": job_title or "Not specified",
                "job_description": job_description[:3000]
            })
            
            # Extract JSON from response
            result = self._extract_json(response.content)
            
            # Merge with our keyword analysis
            for kw in missing[:10]:
                if kw not in result.get("missing_keywords", []):
                    result.setdefault("missing_keywords", []).append(kw)
            
            # Ensure all fields exist with defaults
            return {
                "ats_score": int(result.get("ats_score", 0)),
                "missing_keywords": result.get("missing_keywords", []),
                "weak_bullets": result.get("weak_bullets", []),
                "suggested_bullets": result.get("suggested_bullets", []),
                "strengths": result.get("strengths", []),
                "gaps": result.get("gaps", []),
                "summary": result.get("summary", "")
            }
            
        except Exception as e:
            print(f"AI optimization error: {e}")
            return self._fallback_analysis(resume_text, job_description, missing)
    
    def _extract_json(self, text: str) -> Dict:
        """Extract JSON from AI response (handles markdown wrapping)."""
        # Try direct parse first
        try:
            return json.loads(text)
        except:
            pass
        
        # Try extracting from markdown code block
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except:
                pass
        
        # Try finding raw JSON object
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except:
                pass
        
        # Return empty dict if all fails
        return {}
    
    def _extract_keywords(self, text: str) -> Dict[str, int]:
        """Extract keywords with frequency. Filters common words."""
        stop_words = {
            "the", "a", "an", "and", "or", "but", "is", "are", "was", "were",
            "be", "been", "being", "have", "has", "had", "do", "does", "did",
            "will", "would", "could", "should", "may", "might", "must", "shall",
            "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
            "this", "that", "these", "those", "i", "you", "he", "she", "it",
            "we", "they", "what", "which", "who", "when", "where", "why", "how",
            "all", "any", "both", "each", "few", "more", "most", "other",
            "some", "such", "no", "nor", "not", "only", "own", "same", "so",
            "than", "too", "very", "can", "will", "just", "should", "now",
            "about", "into", "through", "during", "before", "after", "above",
            "below", "between", "out", "off", "over", "under", "again", "further",
            "then", "once", "here", "there", "also", "our", "your", "their",
            "work", "working", "experience", "experienced", "knowledge", "familiar",
            "required", "must", "plus", "etc"
        }
        
        words = re.findall(r"\b[A-Za-z][A-Za-z0-9+#.]*\b", text.lower())
        
        freq = {}
        for w in words:
            if len(w) >= 3 and w not in stop_words:
                freq[w] = freq.get(w, 0) + 1
        
        sorted_kw = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_kw[:30])
    
    def _fallback_analysis(
        self,
        resume_text: str,
        job_description: str,
        missing_keywords: List[str]
    ) -> Dict:
        """Rule-based fallback when AI fails."""
        job_kw = self._extract_keywords(job_description)
        resume_kw = set(self._extract_keywords(resume_text).keys())
        
        job_top = set(list(job_kw.keys())[:15])
        overlap = len(job_top & resume_kw)
        ats_score = int((overlap / max(len(job_top), 1)) * 100)
        
        return {
            "ats_score": ats_score,
            "missing_keywords": missing_keywords[:10],
            "weak_bullets": [
                "AI analysis unavailable - using rule-based scoring",
                "Common issue: bullet points lack quantifiable metrics"
            ],
            "suggested_bullets": [
                "Add quantifiable achievements (e.g., 'Improved X by Y%')",
                "Use action verbs (Led, Built, Optimized, Architected)",
                "Include specific technologies and outcomes"
            ],
            "strengths": [f"Matches {overlap} of top 15 job keywords"],
            "gaps": missing_keywords[:5],
            "summary": f"Rule-based analysis (AI unavailable). Score: {ats_score}/100. Add missing keywords to improve match."
        }


def quick_ats_score(resume_text: str, job_description: str) -> int:
    """Quick ATS score (0-100) without AI."""
    optimizer = ResumeOptimizer()
    job_kw = set(optimizer._extract_keywords(job_description).keys())
    resume_kw = set(optimizer._extract_keywords(resume_text).keys())
    
    if not job_kw:
        return 0
    
    overlap = len(job_kw & resume_kw)
    return int((overlap / len(job_kw)) * 100)
