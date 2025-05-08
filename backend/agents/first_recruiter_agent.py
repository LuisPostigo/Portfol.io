import os
import json
import re
import pika
from llama_cpp import Llama

from backend.config import MODEL_DIR, FOUNDATION_MODEL
from backend.services.matches_db import save_match_result
from backend.services.AgentBase import AgentBase
from backend.services.DebateManager import DebateManager

class FirstRecruiterAgent(AgentBase):
    def __init__(self, model_path=os.path.join(MODEL_DIR, FOUNDATION_MODEL),
                 queue_in='resume_queue_recruiter', queue_out='agent_response_queue'):
        super().__init__(expected_agent_name="RecruiterAgent")
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

        # Create DebateManager instance for Recruiter
        self.debate_manager = DebateManager(
            llama_model=self.llm,
            channel=self.channel,
            first_agent="RecruiterAgent",
            second_agent="HiringManagerAgent",
            first_queue="resume_queue_recruiter",
            second_queue="resume_queue_hiring_manager"
        )

    def _setup_rabbitmq(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=self.queue_in)
        self.channel.queue_declare(queue=self.queue_out)

    def _generate_prompt(self, job_posting, applicant_info):
        return f"""
You are a recruiter evaluating a candidate for the following job:

--- Job Posting ---
Title: {job_posting.get("title")}
Description: {job_posting.get("description")}
Requirements: {job_posting.get("requirements")}

--- Applicant Resume ---
Skills: {applicant_info.get("skills")}
Experience: {applicant_info.get("experience")}
Projects: {applicant_info.get("projects")}
Summary: {applicant_info.get("summary")}

Your task:
- Evaluate the candidate **briefly**, focusing on skill match, experience relevance, project quality, and overall fit.
- Follow the exact format shown below: 5 numbered points plus a final explicit recommendation.
- Item 5 must be a "Fit Score" from 0 to 10, where 0 = poor fit, 10 = ideal fit.
- Always conclude with "Final recommendation: **Yes**" or "**No**".

Example 1:

1. **Skills Match**: Candidate meets core skills (Python, SQL), strong React experience.
2. **Experience Match**: Solid backend and API development background.
3. **Projects Quality**: Delivered several high-impact internal tools.
4. **Overall Assessment**: Candidate is a strong backend prospect.
5. **Fit Score**: 8/10

Final recommendation: **Yes**

---

Example 2:

1. **Skills Match**: Basic familiarity with JavaScript, lacks SQL or backend frameworks.
2. **Experience Match**: Mainly academic; no real-world production experience.
3. **Projects Quality**: Limited scope; only class projects, no major impact demonstrated.
4. **Overall Assessment**: Candidate is underqualified for this role currently.
5. **Fit Score**: 3/10

Final recommendation: **No**

---

Now, following the same style and brevity, write your evaluation below:
"""

    def _evaluate(self, job_posting, applicant_info):
        prompt = self._generate_prompt(job_posting, applicant_info)
        print("(first_recruiter_agent)[LLM] Prompt sent to Llama:\n", prompt)

        response = self.llm.create_completion(prompt=prompt, max_tokens=400, temperature=0.4)
        raw_output = response['choices'][0]['text'].strip()
        raw_output = raw_output.encode('utf-8', errors='ignore').decode('utf-8')

        final_recommendation_match = re.search(r"(Final recommendation:\s*\*\*(?:Yes|No)\*\*)", raw_output, re.IGNORECASE)
        if final_recommendation_match:
            end_idx = final_recommendation_match.end()
            raw_output = raw_output[:end_idx]

        raw_output = re.sub(r'-{3,}', '', raw_output)
        raw_output = raw_output.lstrip()

        print("\n(first_recruiter_agent)[LLM] Cleaned Evaluation:\n", raw_output)

        match = re.search(r'Final recommendation:\s*\*\*(Yes|No)\*\*', raw_output, re.IGNORECASE)
        flag = match.group(1) if match else "Unknown"
        print("(first_recruiter_agent)[CHECK] Final Decision:", flag)

        return {"evaluation": raw_output, "flag": flag}

    def _handle_message(self, ch, method, properties, body):
        try:
            message = self.parse_message(body)
            print("(first_recruiter_agent)[DEBATE] [RecruiterAgent] Received message:", message)
            if not message:
                return

            if not self.should_process_message(message):
                return

            msg_type = message.get("type")

            if msg_type == "mcp_context":
                self._handle_resume(message)
            elif msg_type == "debate_context":
                self.debate_manager.handle_debate_turn(message, agent_name="RecruiterAgent")
            else:
                print(f"(first_recruiter_agent)[!] Ignored unknown message type: {msg_type}")

        except Exception as e:
            print(f"(first_recruiter_agent)[ERROR] Error processing message: {e}")

    def _handle_resume(self, message):
        context = message["context"]
        applicant_info = context["input"]
        job_posting = context["job"]
        applicant_id = message.get("applicant_id", "unknown")
        job_id = message.get("job_id", "unknown")

        result = self._evaluate(job_posting, applicant_info)
        cleaned_evaluation = result["evaluation"]

        response_msg = {
            "type": "agent_response",
            "source": "RecruiterAgent",
            "applicant_id": applicant_id,
            "flag": result["flag"],
            "message": cleaned_evaluation
        }

        self.channel.basic_publish(
            exchange='',
            routing_key=self.queue_out,
            body=json.dumps(response_msg)
        )
        print(f"(first_recruiter_agent)[MESSAGE] Response sent for applicant {applicant_id}")

        if job_id != "unknown":
            try:
                save_match_result(
                    applicant_id=applicant_id,
                    job_id=job_id,
                    agent_name="recruiter_agent",
                    agent_opinion=cleaned_evaluation
                )
            except Exception as db_error:
                print(f"(first_recruiter_agent)[X] Error saving to matches.db: {db_error}")

        portfolio_msg = {
            "type": "mcp_context",
            "target_agent": "PortfolioAnalyzerAgent",
            "context": {
                "input": applicant_info,
                "job": job_posting
            },
            "applicant_id": applicant_id,
            "job_id": job_id
        }

        self.channel.queue_declare(queue='resume_queue_portfolio')
        self.channel.basic_publish(
            exchange='',
            routing_key='resume_queue_portfolio',
            body=json.dumps(portfolio_msg)
        )
        print(f"(first_recruiter_agent)[MESSAGE] PortfolioAnalyzerAgent notified for applicant {applicant_id}")

        technical_lead_msg = {
            "type": "agent_response",
            "source": "RecruiterAgent",       
            "target_agent": "DecisionAgent",
            "applicant_id": applicant_id,
            "job_id": job_id,
            "flag": result["flag"],
            "message": cleaned_evaluation
        }

        self.channel.queue_declare(queue='agent_response_queue')
        self.channel.basic_publish(
            exchange='',
            routing_key='agent_response_queue',
            body=json.dumps(technical_lead_msg)
        )
        print(f"(first_recruiter_agent)[FORWARD] Sent to FourthTechnicalLeadAgent: applicant {applicant_id}")

    def start(self):
        print(f"🤖 FirstRecruiterAgent (Local) is listening on queue: {self.queue_in}")
        self.channel.basic_consume(
            queue=self.queue_in,
            on_message_callback=self._handle_message,
            auto_ack=True
        )
        self.channel.start_consuming()

if __name__ == "__main__":
    agent = FirstRecruiterAgent()
    agent.start()
