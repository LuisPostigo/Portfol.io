import os
import json
import re
import pika
from llama_cpp import Llama

from backend.config import MODEL_DIR, REPO_ANALYSIS_DIR, FOUNDATION_MODEL
from backend.services.matches_db import save_match_result
from backend.services.github_analyzer.main import PortfolioAnalyzer
from backend.services.github_analyzer.analizes_a_repo import AnalyzeRepoForGivenUser

from backend.services.AgentBase import AgentBase

class SecondPortfolioAgent(AgentBase):
    def __init__(self, model_path=os.path.join(MODEL_DIR, FOUNDATION_MODEL),
                 queue_in='resume_queue_portfolio', queue_out='agent_response_queue'):
        super().__init__(expected_agent_name="PortfolioAnalyzerAgent")

        self.queue_in = queue_in
        self.queue_out = queue_out

        self.llm = Llama(
            model_path=model_path,
            n_ctx=4096,
            n_threads=8,
            n_gpu_layers=35,
            use_mlock=True,
            use_mmap=True,
            verbose=False
        )

        self._setup_rabbitmq()

    def _setup_rabbitmq(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=self.queue_in)
        self.channel.queue_declare(queue=self.queue_out)

    def _generate_prompt(self, job_posting, applicant_info, portfolio_summary):
        return f"""
You are a technical recruiter evaluating the portfolio of a candidate against a specific job posting. If a question does not apply, answer with "N/A".

--- Job Posting ---
Title: {job_posting.get("title")}
Description: {job_posting.get("description")}
Requirements: {job_posting.get("requirements")}

--- Applicant Skills ---
Skills: {applicant_info.get("skills")}

--- Portfolio Analysis ---
{portfolio_summary}

Your task:
- Evaluate whether the candidate's claimed skills under the "Skills" section match the ones shown on the portfolio analysis.
- Evaluate whether the skills shown in the portfolio match the requirements for this job.
- Comment on technical depth and breadth.
- Provide a Fit Score from 0 to 10.
- Finish with: Final recommendation: **Yes** or **No**

Example 1:

1. **Real Skills Fit**: The candidate lists Python, Machine Learning, and Data Analysis, all of which are strongly reflected in the portfolio. Their repositories show practical implementation of supervised models using scikit-learn and advanced usage of pandas and NumPy.
2. **Can those skills be worked on**: While deep learning frameworks like TensorFlow are not present, the candidate demonstrates a solid foundation, and expanding into these areas would be a natural progression.
5. **Technical Skill Score**: 9/10

Final recommendation: **Yes**

---

Example 2:

1. **Real Skills Fit**: The candidate claims knowledge of distributed systems and backend APIs, but none of the repositories demonstrate this. Most of the code revolves around basic scripting and simple class definitions.
2. **Can those skills be worked on**: The candidate shows basic Python usage but lacks evidence of backend experience or scalable system design, indicating a large skill gap.
5. **Technical Skill Score**: 4/10

Final recommendation: **No**

Now, write your evaluation below (do not repeat an example):

"""

    def _evaluate(self, github_url, job_posting, applicant_info, applicant_id, job_id):
        print(f"\n{print("=======================================================")}\n[STARTED] Starting portfolio and skill analysis...")

        username = github_url.rstrip('/').split('/')[-1]
        user_dir_path = os.path.join(REPO_ANALYSIS_DIR, "analized_files", username)

        if os.path.exists(user_dir_path):
            print(f"(!) Found existing analysis for {username}, skipping PortfolioAnalyzer.")
        else:
            print(f"[NEW] No existing analysis for {username}, running PortfolioAnalyzer...")
            analyzer = PortfolioAnalyzer(github_url, applicant_info.get("skills", []))
            error = analyzer.analyze()

            if error:
                print(f"(X) Portfolio analysis failed due to bad GitHub URL: {error}")
                save_match_result(
                    applicant_id=applicant_id,
                    job_id=job_id,
                    agent_name="portfolio_agent",
                    agent_opinion="Applicant has no valid GitHub URL"
                )
                print(f"[SAVED] Failure reason saved for applicant {applicant_id}")
                return

        analyzer = AnalyzeRepoForGivenUser(github_url, llm_model=self.llm)
        result = analyzer.get_summary_text()

        if not result.get("success"):
            error_msg = result.get("error", "")
            print(f"(X) Portfolio analysis failed: {error_msg}")

            if "403" in error_msg and "rate limit" in error_msg.lower():
                fallback_message = "Portfolio analysis could not be completed due to GitHub API rate limits. Please try again later."
            else:
                fallback_message = "Portfolio analysis failed due to a GitHub fetch error."

            save_match_result(
                applicant_id=applicant_id,
                job_id=job_id,
                agent_name="portfolio_agent",
                agent_opinion=fallback_message
            )
            print(f"[SAVED] Fallback message saved for applicant {applicant_id}")
            return

        portfolio_summary = (
            f"GitHub Username: {result['username']}\n"
            f"Skill Scores:\n" +
            "\n".join(
                f"- {skill.title()}: Avg Depth = {details['avg_depth']}, Coverage = {details['coverage']}"
                for skill, details in result["skill_scores"].items()
            ) +
            "\n\nSummary:\n" +
            result["final_summary"]
        )

        prompt = self._generate_prompt(job_posting, applicant_info, portfolio_summary)

        print("[LLM] Prompt sent to Llama:")
        response = self.llm.create_completion(prompt=prompt, max_tokens=512, temperature=0.4)
        raw_output = response['choices'][0]['text'].strip()
        raw_output = raw_output.encode('utf-8', errors='ignore').decode('utf-8')
        raw_output = re.sub(r'-{3,}', '', raw_output).lstrip()

        print("\n(!) Cleaned Evaluation:\n", raw_output)

        match = re.search(r'Final recommendation:\s*\*\*(Yes|No)\*\*', raw_output, re.IGNORECASE)
        if match:
            flag = match.group(1)
        else:
            print("⚠️ Could not find final recommendation. Appending default.")
            raw_output += "\n\nFinal recommendation: **No**"
            flag = "No"

        print("(!) Final Decision:", flag)

        save_match_result(
            applicant_id=applicant_id,
            job_id=job_id,
            agent_name="portfolio_agent",
            agent_opinion=raw_output
        )
        print(f"[SAVED] Portfolio Agent opinion saved for applicant {applicant_id} (job_id: {job_id})")
        
        self.publish_final_decision(
            applicant_id,
            flag,
            raw_output,
            job_id,
            applicant_info,
            job_posting
        )

    def _handle_message(self, ch, method, properties, body):
        try:
            message = self.parse_message(body)
            if not message or not self.should_process_message(message):
                return

            context = message.get("context")
            applicant_info = context["input"]
            job_posting = context["job"]
            github_url = applicant_info.get("github")
            applicant_id = message.get("applicant_id", "unknown")
            job_id = message.get("job_id", "unknown")

            if github_url:
                self._evaluate(github_url, job_posting, applicant_info, applicant_id, job_id)
            else:
                print("(!) No GitHub URL found in applicant info.")
        except Exception as e:
            print(f"(X) Error processing portfolio message: {e}")

    def publish_final_decision(self, applicant_id, flag, message, job_id, applicant_info, job_posting):
        response_msg = {
            "type": "agent_response",
            "source": "PortfolioAgent",
            "target_agent": "DecisionAgent",
            "applicant_id": applicant_id,
            "flag": flag,
            "message": message
        }

        self.channel.basic_publish(
            exchange='',
            routing_key=self.queue_out,
            body=json.dumps(response_msg)
        )
        print(f"(!) Final decision published to {self.queue_out} for applicant {applicant_id}")

        hiring_manager_msg = {
            "type": "mcp_context",
            "target_agent": "HiringManagerAgent",
            "context": {
                "input": applicant_info,
                "job": job_posting
            },
            "applicant_id": applicant_id,
            "job_id": job_id
        }

        self.channel.queue_declare(queue='resume_queue_hiring_manager')
        self.channel.basic_publish(
            exchange='',
            routing_key='resume_queue_hiring_manager',
            body=json.dumps(hiring_manager_msg)
        )
        print(f"[FORWARD] Sent context to HiringManagerAgent for applicant {applicant_id}")

        technical_lead_msg = {
            "type": "agent_response",
            "source": "PortfolioAgent",       
            "target_agent": "DecisionAgent",
            "applicant_id": applicant_id,
            "job_id": job_id,
            "flag": flag,
            "message": message,
        }

        self.channel.queue_declare(queue='agent_response_queue')
        self.channel.basic_publish(
            exchange='',
            routing_key='agent_response_queue',
            body=json.dumps(technical_lead_msg)
        )
        print(f"(second_portfolio_agent)[FORWARD] Sent to FourthTechnicalLeadAgent: applicant {applicant_id}")

    def start(self):
        print(f"[LLM] SecondPortfolioAgent listening on queue {self.queue_in}")
        self.channel.basic_consume(
            queue=self.queue_in,
            on_message_callback=self._handle_message,
            auto_ack=True
        )
        self.channel.start_consuming()

if __name__ == "__main__":
    agent = SecondPortfolioAgent()
    agent.start()
