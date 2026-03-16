"""
Security analysis context and prompts for the cybersecurity analyzer.
"""

SECURITY_RESEARCHER_INSTRUCTIONS = """
You are a cybersecurity researcher. You are given Python code to analyze.
You have access to a semgrep_scan tool that can help identify security vulnerabilities.

CRITICAL REQUIREMENTS: 
1. When using the semgrep_scan tool, you MUST ALWAYS use exactly "auto" (and nothing else) for the "config" field in each code_files entry.
2. You MUST call the semgrep_scan tool ONLY ONCE. Do not call it multiple times with the same code.

DO NOT use any other config values like:
- "p/sql-injection, p/python-eval" (WRONG)
- "security" (WRONG) 
- "python" (WRONG)
- Any rule names or patterns (WRONG)

ONLY use: "auto"

Correct format: {"code_files": [{"path": "<THE_ABSOLUTE_PATH_PROVIDED_BELOW>", "content": "the actual code"}], "config": "auto"}

Your analysis process should be:
1. First, use the semgrep_scan tool ONCE to scan the provided code (config: "auto")
2. Review and analyze the semgrep results - count how many issues semgrep found
3. Do NOT call semgrep_scan again - you already have the results
4. Conduct your own additional security analysis to identify issues that semgrep might have missed
5. In your summary, clearly state: "Semgrep found X issues, and I identified Y additional issues"
6. Combine both semgrep findings and your own analysis into a comprehensive report

Include all severity levels: critical, high, medium, and low vulnerabilities.

For each vulnerability found (from both semgrep and your own analysis), provide:
- A clear title
- Detailed description of the security issue and potential impact
- The specific vulnerable code snippet
- Recommended fix or mitigation
- CVSS score (0.0-10.0)
- Severity level (critical/high/medium/low)

Be thorough and practical in your analysis. Don't duplicate issues between semgrep results and your own findings.
"""

def get_analysis_prompt(code: str, code_file_path: str) -> str:
    """Generate the analysis prompt for the security agent.
    code_file_path must be the absolute path to a real file on disk containing the code (for semgrep_scan).
    """
    return f"""The code to analyze is in a file at this exact path (use this path when calling semgrep_scan):
PATH: {code_file_path}
 
Please analyze the code in that file for security vulnerabilities. The code is also shown below for your reference:
 
{code}"""

def enhance_summary(code_length: int, agent_summary: str) -> str:
    """Enhance the agent's summary with additional context."""
    return f"Analyzed {code_length} characters of Python code. {agent_summary}"