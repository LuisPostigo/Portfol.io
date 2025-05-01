import os
import json
import re
import pika
from llama_cpp import Llama

from backend.config import MODEL_DIR
from backend.services.matches_db import save_match_result, load_recruiter_opinion
from backend.services.AgentBase import AgentBase
from backend.services.DebateManager import DebateManager

class ThirdHiringManagerAgent(AgentBase):
    def __init__(self, model_path=os.path.join(MODEL_DIR, "mistral-7b-instruct-v0.1-q4_k_m.gguf"),
                 queue_in='resume_queue_hiring_manager', queue_out='agent_response_queue'):
        super().__init__(expected_agent_name="HiringManagerAgent")

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

        # 🆕 Initialize DebateManager
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
You are a Hiring Manager evaluating a candidate.

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
- Evaluate the candidate carefully based on the provided resume and job requirements.
- Follow the format below strictly: 5 numbered points + a final explicit recommendation (Yes or No).
- Item 5 must be a "Fit Score" from 0 to 10, where 0 is a very poor fit and 10 is an ideal fit.
- You must always include a final "Final recommendation: **Yes**" or "**No**" at the end.

Example 1:

1. **Career Progression**: Steady growth from junior to mid-level roles across internships and full-time positions.
2. **Job Level Fit**: Matches mid-level software engineer role based on skills and experience.
3. **Soft Skills**: Demonstrated leadership, collaboration, and initiative in team projects.
4. **Overall Assessment**: Candidate shows a strong background, technical depth, and good culture fit.
5. **Fit Score**: 9/10

Final recommendation: **Yes**

---

Example 2:

1. **Career Progression**: Limited progression; mainly academic projects, no professional experience.
2. **Job Level Fit**: Partial match; candidate lacks experience in distributed systems and APIs.
3. **Soft Skills**: Limited evidence of leadership or communication skills.
4. **Overall Assessment**: Candidate has potential but lacks practical experience for the position.
5. **Fit Score**: 4/10

Final recommendation: **No**

---

Now, following the same style and level of detail, write your evaluation below:
"""

    def _evaluate(self, job_posting, applicant_info):
        prompt = self._generate_prompt(job_posting, applicant_info)
        print("🧠 Prompt sent to Llama:\n", prompt)

        response = self.llm.create_completion(prompt=prompt, max_tokens=400, temperature=0.4)
        raw_output = response['choices'][0]['text'].strip()
        raw_output = raw_output.encode('utf-8', errors='ignore').decode('utf-8')
        raw_output = re.sub(r'-{3,}', '', raw_output).lstrip()

        print("\n🧹 Cleaned Evaluation:\n", raw_output)

        match = re.search(r'Final recommendation:\s*\*\*(Yes|No)\*\*', raw_output, re.IGNORECASE)
        flag = match.group(1) if match else "Unknown"
        print("✅ Final Decision:", flag)

        return {"evaluation": raw_output, "flag": flag}

    def _handle_message(self, ch, method, properties, body):
        try:
            message = self.parse_message(body)
            if not message or not self.should_process_message(message):
                return

            msg_type = message.get("type")

            if msg_type == "mcp_context":
                self._handle_resume(message)
            elif msg_type == "debate_context":
                self._handle_debate(message)
            else:
                print(f"⚠️ Ignored unknown message type: {msg_type}")

        except Exception as e:
            print(f"❌ Error processing message: {e}")

    def _handle_resume(self, message):
        context = message["context"]
        applicant_info = context["input"]
        job_posting = context["job"]
        applicant_id = message.get("applicant_id", "unknown")
        job_id = message.get("job_id", "unknown")

        manager_result = self._evaluate(job_posting, applicant_info)
        recruiter_result = load_recruiter_opinion(applicant_id)

        # Save Hiring Manager's opinion immediately
        try:
            save_match_result(
                applicant_id=applicant_id,
                job_id=job_id,
                agent_name="hiring_manager_agent",
                agent_opinion=manager_result["evaluation"]
            )
            print(f"💾 Hiring Manager initial opinion saved for applicant {applicant_id}")
        except Exception as e:
            print(f"❌ Error saving hiring manager opinion: {e}")

        if recruiter_result is None:
            print("⚠️ Recruiter opinion not found. Skipping debate.")
            return

        recruiter_flag = recruiter_result["flag"]
        manager_flag = manager_result["flag"]

        if recruiter_flag != manager_flag:
            print("⚔️ Disagreement detected. Launching debate...")
            self.debate_manager.start_debate(applicant_id, job_id, recruiter_result, manager_result)
        else:
            print("✅ Agreement detected. No debate needed.")
            self.publish_final_decision(applicant_id, manager_flag, manager_result["evaluation"], job_id)

    def _handle_debate(self, message):
        self.debate_manager.handle_debate_turn(message, agent_name="HiringManagerAgent")

    def publish_final_decision(self, applicant_id, flag, message, job_id):
        response_msg = {
            "type": "agent_response",
            "source": "HiringManagerAgent",
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
        print(f"📤 Final decision published for applicant {applicant_id}")

    def start(self):
        print(f"🤖 ThirdHiringManagerAgent listening on queue {self.queue_in}")
        self.channel.basic_consume(
            queue=self.queue_in,
            on_message_callback=self._handle_message,
            auto_ack=True
        )
        self.channel.start_consuming()

if __name__ == "__main__":
    agent = ThirdHiringManagerAgent()
    agent.start()
