import os
import json
import re
import pika
from llama_cpp import Llama
from backend.config import MODEL_DIR, FOUNDATION_MODEL
from backend.services.matches_db import save_match_result
from backend.services.AgentBase import AgentBase
from backend.services.DebateManager import DebateManager

class FourthTechnicalLeadAgent(AgentBase):
    def __init__(self, model_path=os.path.join(MODEL_DIR, FOUNDATION_MODEL),
                 queue_in='agent_response_queue', queue_out='final_decision_queue'):
        super().__init__(expected_agent_name="TechnicalLeadAgent")

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
        self.debate_manager = DebateManager(
            llama_model=self.llm,
            channel=self.channel,
            first_agent="TechnicalLeadAgent",
            second_agent=None,
            first_queue="resume_queue_technical_lead",
            second_queue=None 
        )
        self.buffer = {}

    def _setup_rabbitmq(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=self.queue_in)
        self.channel.queue_declare(queue=self.queue_out)

    def _buffer_message(self, message):
        aid = message["applicant_id"]
        if aid not in self.buffer:
            self.buffer[aid] = {}
        self.buffer[aid][message["source"]] = message

    def _has_all_responses(self, applicant_id):
        sources = self.buffer.get(applicant_id, {})
        return all(key in sources for key in ["RecruiterAgent", "PortfolioAgent", "HiringManagerAgent"])

    def _evaluate_consensus(self, applicant_id):
        responses = self.buffer[applicant_id]
        job_id = next((v.get("job_id") for v in responses.values() if v.get("job_id")), "unknown")

        evaluations = {
            k: v["message"] for k, v in responses.items()
        }
        flags = {
            k: v["flag"] for k, v in responses.items()
        }

        prompt = f"""
You are a Technical Lead reviewing all prior agent evaluations.
Your task is to read through the three inputs and decide:
- Whether you agree or disagree with each
- If disagreements exist, launch a debate with that agent
- Give a final Fit Score (0-10) and a Final recommendation: **Yes** or **No**

--- RecruiterAgent ---\n{evaluations['RecruiterAgent']}\n
--- PortfolioAgent ---\n{evaluations['PortfolioAgent']}\n
--- HiringManagerAgent ---\n{evaluations['HiringManagerAgent']}\n
Now write your summary evaluation below:
"""

        response = self.llm.create_completion(prompt=prompt, max_tokens=512, temperature=0.4)
        decision_text = response['choices'][0]['text'].strip()
        decision_text = decision_text.encode('utf-8', errors='ignore').decode('utf-8')
        decision_text = re.sub(r'-{3,}', '', decision_text).lstrip()

        match = re.search(r'Final recommendation:\s*\*\*(Yes|No)\*\*', decision_text, re.IGNORECASE)
        flag = match.group(1) if match else "Unknown"

        save_match_result(
            applicant_id=applicant_id,
            job_id=job_id,
            agent_name="technical_lead_agent",
            agent_opinion=decision_text
        )

        final_msg = {
            "type": "agent_response",
            "source": "TechnicalLeadAgent",
            "applicant_id": applicant_id,
            "flag": flag,
            "message": decision_text
        }
        self.channel.basic_publish(
            exchange='',
            routing_key=self.queue_out,
            body=json.dumps(final_msg)
        )
        print(f"[FINAL] TechnicalLeadAgent published final decision for {applicant_id}")

    def _handle_message(self, ch, method, properties, body):
        try:
            message = json.loads(body)
            applicant_id = message.get("applicant_id")
            source = message.get("source")

            if not applicant_id or source not in ["RecruiterAgent", "PortfolioAgent", "HiringManagerAgent"]:
                print(f"[SKIP] Invalid or unknown message source: {source}")
                return

            self._buffer_message(message)
            print(f"[BUFFER] Received from {source} for {applicant_id}")

            if self._has_all_responses(applicant_id):
                print(f"[BUFFER] All agent responses received for {applicant_id}. Evaluating...")
                self._evaluate_consensus(applicant_id)
                del self.buffer[applicant_id]  # cleanup to avoid memory bloat

        except Exception as e:
            print(f"(X) TechnicalLeadAgent failed to handle message: {e}")

    def start(self):
        print(f"🤖 FourthTechnicalLeadAgent listening on queue {self.queue_in}")
        self.channel.basic_consume(
            queue=self.queue_in,
            on_message_callback=self._handle_message,
            auto_ack=True
        )
        self.channel.start_consuming()

if __name__ == "__main__":
    agent = FourthTechnicalLeadAgent()
    agent.start()

