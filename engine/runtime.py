from engine.intent_classifier import classify_intent
from engine.summary_memory import update_summary
from engine.voice_local import LocalVoiceSession
import random


class AgentRuntime:
    MAX_RETRIES_PER_STATE = 3

    def __init__(self, agent, campaign_context=None):
        self.agent = agent
        self.state_id = agent.start_state
        self.state_memory = {}
        self.summary_memory = ""
        self.voice = LocalVoiceSession()

        # Campaign data (Excel / future CRM)
        self.campaign_context = campaign_context or {}
        self.state_memory.update(self.campaign_context)

        self.context = {
            "has_greeted": False,
            "retry_count": {}
        }

    # ---------------- MAIN LOOP ----------------

    def run(self):
        print(f"\n--- Running agent: {self.agent.name} ---\n")

        if self.campaign_context:
            print("[Campaign Loaded]")
            for k, v in self.campaign_context.items():
                print(f"  {k}: {v}")
            print()

        while True:
            # END STATE
            
            if self.state_id == "END":
                print("\n--- Call ended ---")
                print("Outcome:", self.agent.outcome(self.state_memory))
                break

            # Safety guard
            if self.state_id not in self.agent.states:
                print(f"[Runtime Warning] Invalid state: {self.state_id}")
                self.state_id = "END"
                continue

            state = self.agent.states[self.state_id]
            state_name = self.state_id
            self.context["retry_count"].setdefault(state_name, 0)

            prompt = state.get("prompt", "")

            

            # 🔹 Agent-owned dynamic prompt resolution
            if callable(prompt):
                prompt = prompt(self.state_memory)

            # Speak
            if state_name == "OPEN":
                if not self.context["has_greeted"]:
                    if prompt:
                        self.voice.speak(prompt)
                    self.context["has_greeted"] = True
            else:
                if prompt:
                    self.voice.speak(prompt)

            # Auto transitions
            if state.get("auto"):
                if state["auto"] == "__RETURN__":
                    self.state_id = self.state_memory.pop(
                        "_return_state",
                        "RELEVANCE_CHECK"
                    )
                else:
                    self.state_id = state["auto"]
                continue

            # Listen
            user_input = self.voice.listen()
            self.state_memory["_last_user_input"] = user_input

            intent, confidence, entities = classify_intent(
                user_input,
                state["allowed_intents"],
                self.summary_memory
            )

            # Retry guard
            if confidence < state["min_confidence"]:
                self.context["retry_count"][state_name] += 1

                if self.context["retry_count"][state_name] >= self.MAX_RETRIES_PER_STATE:
                    self.voice.speak("Let’s pause here for now. We’ll follow up shortly.")
                    self.state_id = "END"
                    continue

                self.voice.speak("Sorry, could you clarify that?")
                continue

            self.context["retry_count"][state_name] = 0

            if entities:
                self.state_memory.update(entities)

            self.summary_memory = update_summary(
                self.summary_memory,
                user_input,
                prompt
            )

            next_state = state["transitions"].get(intent)


            if next_state == "FACTUAL_INTERRUPT":
                # Never return to OFFER_PITCH — that would replay the pitch.
                # If interrupted mid-pitch, return to RELEVANCE_CHECK instead.
                return_to = state_name if state_name != "OFFER_PITCH" else "RELEVANCE_CHECK"
                self.state_memory["_return_state"] = return_to

            if state_name == "RELEVANCE_CHECK" and intent == "affirmative":
                self.state_memory["interest_captured"] = True


            if not next_state:
                print("AGENT: Got it.")
                continue

            # Handle __RETURN__ — go back to state before FACTUAL_INTERRUPT
            if next_state == "__RETURN__":
                next_state = self.state_memory.pop("_return_state", "RELEVANCE_CHECK")

            self.state_id = next_state