
"""
LinkedIn Profile Optimizer: Rewrite LinkedIn profile sections for better visibility.
Uses Mistral AI to optimize headline, about, and skills sections.
"""
import json
import re
from typing import Dict, List, Optional

from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate


from config.settings import settings


class LinkedInOptimizer:
    """Optimize LinkedIn profile for recruiter searches."""
    
    def __init__(self):
        self.llm = ChatMistralAI(
            model="mistral-small-latest",
            api_key=settings.MISTRAL_API_KEY,
            temperature=0.5  # Slightly creative for headlines
        )
    
    def optimize_profile(
        self,
        current_headline: Optional[str] = None,
        current_about: Optional[str] = None,
        current_skills: Optional[List[str]] = None,
        target_role: Optional[str] = None,
        years_experience: Optional[int] = None,
        industry: Optional[str] = None
    ) -> Dict:
        """
        Optimize LinkedIn profile sections.
        
        Returns optimized headline, about, skills with explanations.
        """
        # Build context
        context = self._build_context(
            current_headline, current_about, current_skills,
            target_role, years_experience, industry
        )
        
        # Generate optimized profile
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a LinkedIn profile optimization expert and career coach.
            You help professionals rewrite their LinkedIn profiles to:
            1. Be discoverable by recruiters (keyword-rich)
            2. Show personality and stand out
            3. Communicate value clearly
            4. Use proven copywriting formulas
            
            Return ONLY valid JSON, no markdown, no explanation."""),
            ("user", """Optimize this LinkedIn profile:

{context}

Return JSON with EXACT structure:
{{
    "headline": "<120 char max LinkedIn headline with emojis>",
    "headline_alternatives": ["alt headline 1", "alt headline 2"],
    "about": "<2600 char max About section in first person>",
    "about_tips": ["tip about About section"],
    "skills": ["skill1", "skill2", "skill3"],
    "skills_rationale": "why these skills",
    "experience_bullets": ["suggested bullet for experience section"],
    "keywords_to_add": ["keyword1", "keyword2"],
    "profile_strength_tips": ["tip 1", "tip 2"]
}}""")
        ])
        
        try:
            chain = prompt | self.llm
            response = chain.invoke({"context": context})
            result = self._parse_json(response.content)
            
            return {
                "headline": result.get("headline", current_headline or ""),
                "headline_alternatives": result.get("headline_alternatives", []),
                "about": result.get("about", current_about or ""),
                "about_tips": result.get("about_tips", []),
                "skills": result.get("skills", current_skills or []),
                "skills_rationale": result.get("skills_rationale", ""),
                "experience_bullets": result.get("experience_bullets", []),
                "keywords_to_add": result.get("keywords_to_add", []),
                "profile_strength_tips": result.get("profile_strength_tips", [])
            }
            
        except Exception as e:
            print(f"LinkedIn optimization error: {e}")
            return self._fallback_profile(current_headline, current_about, current_skills)
    
    def optimize_headline_only(
        self,
        current_headline: str,
        target_role: str
    ) -> Dict:
        """Quick headline-only optimization."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You write magnetic LinkedIn headlines. Return ONLY valid JSON."),
            ("user", """Current headline: {current}
Target role: {target}

Return JSON:
{{
    "headline": "<optimized 120 char headline>",
    "alternatives": ["alt 1", "alt 2", "alt 3"],
    "why_it_works": "<1 sentence explanation>"
}}""")
        ])
        
        try:
            chain = prompt | self.llm
            response = chain.invoke({
                "current": current_headline,
                "target": target_role
            })
            return self._parse_json(response.content)
        except Exception as e:
            return {
                "headline": current_headline,
                "alternatives": [],
                "why_it_works": "AI unavailable - keep current"
            }
    
    def _build_context(
        self,
        headline, about, skills, target_role, years, industry
    ) -> str:
        """Build context string for AI."""
        parts = []
        
        if headline:
            parts.append(f"Current Headline: {headline}")
        if about:
            parts.append(f"Current About: {about}")
        if skills:
            parts.append(f"Current Skills: {', '.join(skills)}")
        if target_role:
            parts.append(f"Target Role: {target_role}")
        if years:
            parts.append(f"Years of Experience: {years}")
        if industry:
            parts.append(f"Industry: {industry}")
        
        return "\n".join(parts) if parts else "No profile provided. Generate from scratch."
    
    def _parse_json(self, text: str) -> Dict:
        """Extract JSON from AI response."""
        try:
            return json.loads(text)
        except:
            pass
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except:
                pass
        return {}
    
    def _fallback_profile(self, headline, about, skills) -> Dict:
        """Fallback when AI fails."""
        return {
            "headline": headline or "Professional | Open to Opportunities",
            "headline_alternatives": [
                "Passionate Professional | Seeking New Challenges",
                "Results-Driven Expert | Available for Hire"
            ],
            "about": about or "Add a compelling About section to attract recruiters.",
            "about_tips": [
                "Start with a hook",
                "Quantify achievements",
                "End with a call-to-action"
            ],
            "skills": skills or [],
            "skills_rationale": "AI unavailable - keep current skills",
            "experience_bullets": [],
            "keywords_to_add": [],
            "profile_strength_tips": [
                "Add a professional photo",
                "Request recommendations",
                "Post regularly"
            ]
        }