import json
from backend.services.matches_db import save_match_result, load_recruiter_opinion, upload_debates

class DebateManager:
    def __init__(self, llama_model, channel, first_agent, second_agent, first_queue, second_queue):
        self.llm = llama_model
        self.channel = channel
        self.first_agent = first_agent
        self.second_agent = second_agent
        self.first_queue = first_queue
        self.second_queue = second_queue
        self.max_debate_rounds = 8   # 3 rounds (6 messages total)

    def start_debate(self, applicant_id, job_id, first_result, second_result):
        debate_state = {
            "applicant_id": applicant_id,
            "job_id": job_id,
            "round": 1,
            "history": [
                {self.first_agent: first_result["message"]},
                {self.second_agent: second_result["evaluation"]}
            ],
            "current_turn": self.first_agent
        }

        msg = {
            "type": "debate_context",
            "applicant_id": applicant_id,
            "job_id": job_id,
            "opponent_opinion": second_result["evaluation"],
            "debate_state": debate_state
        }

        self.channel.queue_declare(queue=self.first_queue)
        self.channel.basic_publish(
            exchange='',
            routing_key=self.first_queue,
            body=json.dumps(msg)
        )
        print(f"📨 Debate initiated with {self.first_agent} for applicant {applicant_id}")

    def handle_debate_turn(self, message, agent_name):
        debate_state = message["debate_state"]
        applicant_id = message["applicant_id"]
        job_id = message["job_id"]
        opponent_opinion = message["opponent_opinion"]

        next_agent_queue = self.second_queue if agent_name == self.first_agent else self.first_queue
        next_agent_name = self.second_agent if agent_name == self.first_agent else self.first_agent

        prompt = f"""
You are {agent_name} rebutting in a candidate hiring debate.

Opponent said:
"{opponent_opinion}"

Reply with a **sharp rebuttal under 50 words**.
"""

        response = self.llm.create_completion(prompt=prompt, max_tokens=80, temperature=0.4)
        rebuttal = response['choices'][0]['text'].strip()

        print(f"⚔️ {agent_name} rebuttal:\n{rebuttal}")

        # Save structured message
        debate_state["history"].append({agent_name: rebuttal})
        debate_state["round"] += 1

        if debate_state["round"] > self.max_debate_rounds:
            self.settle_debate(debate_state)
        else:
            debate_state["current_turn"] = next_agent_name
            msg = {
                "type": "debate_context",
                "applicant_id": applicant_id,
                "job_id": job_id,
                "opponent_opinion": rebuttal,
                "debate_state": debate_state
            }

            self.channel.queue_declare(queue=next_agent_queue)
            self.channel.basic_publish(
                exchange='',
                routing_key=next_agent_queue,
                body=json.dumps(msg)
            )
            print(f"📨 Sent next debate turn to {debate_state['current_turn']}")

    def settle_debate(self, debate_state):
        print("⚖️ Settling debate...")

        # ---------- build transcript + decide winner ----------
        full_debate_json = debate_state["history"]
        applicant_id = debate_state["applicant_id"]
        job_id       = debate_state["job_id"]

        debate_str = "\n".join(
            f"{list(entry)[0]}: {list(entry.values())[0]}" for entry in full_debate_json
        )

        winner_prompt = f"""
        Two agents debated whether to hire a candidate.

        Debate Transcript:
        {debate_str}

        Which agent presented stronger arguments overall?
        Answer exactly "{self.first_agent}" or "{self.second_agent}" and nothing else.
        """
        winner = self.llm.create_completion(
            prompt=winner_prompt, max_tokens=10, temperature=0.2
        )["choices"][0]["text"].strip()

        # ------------------------------------------------------
        base_col = f"{self.first_agent.lower()}_{self.second_agent.lower()}_debate_response"

        # Full transcript (JSON string)
        transcript_str = json.dumps(full_debate_json)

        # 1️⃣  Save / update the transcript
        save_match_result(
            applicant_id=applicant_id,
            job_id=job_id,
            agent_name=base_col,             # ← same as before
            agent_opinion=transcript_str
        )

        # 2️⃣  Save / update the winner in its own column
        save_match_result(
            applicant_id=applicant_id,
            job_id=job_id,
            agent_name=f"{base_col}_winner", # ← same name + "_winner"
            agent_opinion=winner             # just "recruiteragent" or "hiringmanageragent"
        )

        print(f"✅ Transcript → {base_col}, winner → {base_col}_winner")
