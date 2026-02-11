import os
import google.generativeai as genai
import json

class AssessmentAI:
    def __init__(self):
        # Configure Gemini
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set.")
        
        genai.configure(api_key=api_key)
        
        # Using the user-requested efficient model
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Context Map for the AI to understand the pillars
        self.context_map = {
            "Sales Strategy & Planning": "The foundational blueprint. Includes ICP definition, differentiation, revenue stream focus, and execution planning.",
            "Team Competency & Execution": "The tactical ability of the humans. Includes objection handling, closing skills, negotiation, and consistency in hitting targets.",
            "Technology & Enablement": "The leverage layer. Includes CRM adoption, data hygiene, sales tools (outreach, recording), and tech roadmap integration."
        }

    def _call_gemini(self, prompt):
        try:
            # Set generation config for analytical precision
            config = genai.GenerationConfig(
                temperature=0.2,
                max_output_tokens=1024,
            )
            response = self.model.generate_content(prompt, generation_config=config)
            return response.text
        except Exception as e:
            return f"AI Processing Error: {str(e)}"

    def generate_insight(self, section_name, score, questions_data):
        """
        Analyzes the full question-level data to find specific root causes.
        """
        # 1. Prepare evidence
        evidence_list = []
        for q in questions_data:
            q_score = float(q['score'])
            status = "STRONG" if q_score >= 8 else "WEAK" if q_score < 5 else "AVERAGE"
            evidence_list.append(f"- [{status}] Score {q_score}: {q['text']}")
        
        evidence_block = "\n".join(evidence_list)
        section_context = self.context_map.get(section_name, "Sales performance pillar.")

        # 2. The "Consultant" Prompt
        prompt = f"""
        You are a Senior Revenue Operations Consultant for Arrowbow, analyzing a client's sales maturity.
        
        SECTION: {section_name}
        SCORE: {score:.1f}/10
        CONTEXT: {section_context}
        
        EVIDENCE:
        {evidence_block}
        
        TASK:
        Provide a forensic analysis in bullet points.
        
        FORMAT (Return HTML-ready text):
        <b>Diagnosis:</b> [One clear sentence identifying the root gap]<br>
        <b>Impact:</b> [Financial/Operational consequence]<br>
        <b>Action:</b> [One specific recommendation]
        
        Tone: Professional, direct, 'Arrowbow' style (High performance, no fluff).
        """
        
        return self._call_gemini(prompt)

    def generate_executive_summary(self, company_name, overall_score, lowest_section):
        """
        Generates the CEO-level summary for the cover page.
        """
        prompt = f"""
        Write an Executive Summary for the 'Arrowbow Sales Performance Accelerator' report for client '{company_name}'.
        
        DATA:
        - Overall Maturity: {overall_score:.1f}/10
        - Critical Bottleneck: {lowest_section}
        
        INSTRUCTIONS:
        Write exactly 2 paragraphs.
        1. Assess their current maturity level (Foundational, Emerging, or High-Performance).
        2. Focus on the critical bottleneck ({lowest_section}) and why fixing it is the key to unlocking revenue.
        
        Tone: Executive, sober, motivating.
        """
        return self._call_gemini(prompt)