
"""
Interview Prep: Generate interview questions for a job and provide AI feedback.
Uses Mistral AI to generate relevant questions and evaluate answers.
"""
import json
import re
from typing import Dict, List, Optional

from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate


from config.settings import settings


class InterviewPrep:
    """Generate interview questions and evaluate answers."""
    
    QUESTION_TYPES = [
        "behavioral",
        "technical",
        "system-design",
        "coding",
        "culture-fit"
    ]
    
    def __init__(self):
        self.llm = ChatMistralAI(
            model="mistral-small-latest",
            api_key=settings.MISTRAL_API_KEY,
            temperature=0.4
        )
    
    def generate_questions(
        self,
        job_title: str,
        job_description: str,
        num_questions: int = 10,
        question_types: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Generate interview questions for a job.
        
        Returns list of questions with type, difficulty, and what they're testing.
        """
        if question_types is None:
            question_types = ["behavioral", "technical", "system-design"]
        
        types_str = ", ".join(question_types)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an experienced engineering manager and interview coach.
            You create realistic, challenging interview questions that test real-world skills.
            Return ONLY valid JSON, no markdown, no explanation."""),
            ("user", """Generate {num} interview questions for:

Job Title: {job_title}
Job Description: {job_desc}

Question types to include: {types}

Return JSON array:
[
    {{
        "question": "<the question>",
        "type": "behavioral|technical|system-design|coding|culture-fit",
        "difficulty": "easy|medium|hard",
        "what_it_tests": "<skill or trait being evaluated>",
        "tips": "<how to approach answering>",
        "sample_answer": "<brief 2-3 sentence example answer>"
    }}
]""")
        ])
        
        try:
            chain = prompt | self.llm
            response = chain.invoke({
                "num": num_questions,
                "job_title": job_title,
                "job_desc": job_description[:2000],
                "types": types_str
            })
            
            result = self._parse_json(response.content)
            
            # Handle if AI returns object instead of array
            if isinstance(result, dict):
                result = result.get("questions", [])
            
            if not isinstance(result, list):
                return self._fallback_questions(job_title, num_questions)
            
            # Ensure each question has required fields
            questions = []
            for q in result[:num_questions]:
                if isinstance(q, dict) and q.get("question"):
                    questions.append({
                        "question": q.get("question", ""),
                        "type": q.get("type", "behavioral"),
                        "difficulty": q.get("difficulty", "medium"),
                        "what_it_tests": q.get("what_it_tests", ""),
                        "tips": q.get("tips", ""),
                        "sample_answer": q.get("sample_answer", "")
                    })
            
            return questions if questions else self._fallback_questions(job_title, num_questions)
            
        except Exception as e:
            print(f"Question generation error: {e}")
            return self._fallback_questions(job_title, num_questions)
    
    def evaluate_answer(
        self,
        question: str,
        answer: str,
        question_type: str = "behavioral"
    ) -> Dict:
        """
        Evaluate a candidate's answer to an interview question.
        
        Returns score, feedback, strengths, and improvements.
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an experienced interviewer providing constructive feedback.
            Be specific, fair, and actionable. Return ONLY valid JSON."""),
            ("user", """Evaluate this interview answer:

Question: {question}
Question Type: {q_type}
Candidate's Answer: {answer}

Return JSON:
{{
    "score": <0-100>,
    "score_breakdown": {{
        "relevance": <0-100>,
        "depth": <0-100>,
        "clarity": <0-100>,
        "structure": <0-100>
    }},
    "strengths": ["specific strength 1", "specific strength 2"],
    "improvements": ["specific actionable improvement 1", "improvement 2"],
    "better_answer": "<a stronger version of their answer>",
    "verdict": "<hire|lean-hire|no-hire|lean-no-hire>"
}}""")
        ])
        
        try:
            chain = prompt | self.llm
            response = chain.invoke({
                "question": question,
                "q_type": question_type,
                "answer": answer[:2000]
            })
            
            result = self._parse_json(response.content)
            
            return {
                "score": int(result.get("score", 0)),
                "score_breakdown": result.get("score_breakdown", {}),
                "strengths": result.get("strengths", []),
                "improvements": result.get("improvements", []),
                "better_answer": result.get("better_answer", ""),
                "verdict": result.get("verdict", "unknown")
            }
            
        except Exception as e:
            print(f"Answer evaluation error: {e}")
            return {
                "score": 50,
                "score_breakdown": {"relevance": 50, "depth": 50, "clarity": 50, "structure": 50},
                "strengths": ["AI unavailable - unable to assess"],
                "improvements": ["Try again later"],
                "better_answer": "AI service unavailable",
                "verdict": "unknown"
            }
    
    def generate_study_plan(
        self,
        job_title: str,
        job_description: str,
        days_until_interview: int = 7
    ) -> Dict:
        """
        Generate a study plan for interview prep.
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a career coach. Create realistic study plans. Return ONLY valid JSON."),
            ("user", """Create a {days}-day interview prep study plan for:

Job: {job_title}
Description: {job_desc}

Return JSON:
{{
    "overview": "<1-2 sentence overview>",
    "days": [
        {{
            "day": 1,
            "topic": "<day's focus>",
            "tasks": ["task 1", "task 2", "task 3"],
            "resources": ["resource 1", "resource 2"],
            "time_estimate": "<e.g., 2-3 hours>"
        }}
    ],
    "final_tips": ["tip 1", "tip 2"]
}}""")
        ])
        
        try:
            chain = prompt | self.llm
            response = chain.invoke({
                "days": days_until_interview,
                "job_title": job_title,
                "job_desc": job_description[:1500]
            })
            
            result = self._parse_json(response.content)
            return result if result else self._fallback_study_plan(days_until_interview)
            
        except Exception as e:
            return self._fallback_study_plan(days_until_interview)
    
    def _parse_json(self, text: str) -> any:
        """Extract JSON from AI response."""
        try:
            return json.loads(text)
        except:
            pass
        
        # Try array
        m = re.search(r"\[.*\]", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except:
                pass
        
        # Try object
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except:
                pass
        
        return None
    
    def _fallback_questions(self, job_title: str, num: int) -> List[Dict]:
        """Generic fallback questions."""
        generic = [
            {
                "question": f"Tell me about your experience relevant to the {job_title} role.",
                "type": "behavioral",
                "difficulty": "easy",
                "what_it_tests": "Communication, self-awareness",
                "tips": "Use STAR format (Situation, Task, Action, Result)",
                "sample_answer": "I've spent 5 years building..."
            },
            {
                "question": "Describe a challenging technical problem you solved.",
                "type": "behavioral",
                "difficulty": "medium",
                "what_it_tests": "Problem-solving, technical depth",
                "tips": "Be specific about the problem and your approach",
                "sample_answer": "At my previous role, we had a performance issue..."
            },
            {
                "question": "How do you stay current with new technologies?",
                "type": "behavioral",
                "difficulty": "easy",
                "what_it_tests": "Learning agility, passion",
                "tips": "Mention specific blogs, courses, projects",
                "sample_answer": "I follow tech blogs and contribute to open source..."
            }
        ]
        
        # Repeat if needed
        questions = []
        for i in range(num):
            questions.append(generic[i % len(generic)])
        
        return questions
    
    def _fallback_study_plan(self, days: int) -> Dict:
        """Fallback study plan."""
        return {
            "overview": f"{days}-day general interview prep plan",
            "days": [
                {
                    "day": 1,
                    "topic": "Review job description and requirements",
                    "tasks": ["Read JD carefully", "Identify key skills", "Research company"],
                    "resources": ["Company website", "LinkedIn"],
                    "time_estimate": "1-2 hours"
                },
                {
                    "day": 2,
                    "topic": "Practice behavioral questions",
                    "tasks": ["List 5 STAR stories", "Practice out loud"],
                    "resources": ["STAR format guide"],
                    "time_estimate": "2 hours"
                }
            ],
            "final_tips": ["Get good sleep", "Test your setup", "Prepare questions to ask"]
        }