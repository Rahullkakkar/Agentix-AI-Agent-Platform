from engine.llm import llm

class OutboundRecommendationAgent:
    name = "Outbound Recommendation Agent"
    start_state = "OPEN"

    states = {

        # 1️⃣ OPEN — permission anchor
        "OPEN": {
            "prompt": (
                "Hi, this is a quick call to let you know about a limited-time offer "
                "we’re currently running in your area. Is now a good time to talk?"
            ),
            "allowed_intents": ["affirmative", "negative", "neutral"],
            "min_confidence": 0.5,
            "transitions": {
                "affirmative": "OFFER_PITCH",
                "neutral": "OFFER_PITCH",
                "negative": "END"
            }
        },

        # 2️⃣ OFFER PITCH — LLM-generated, spoken, no CTA
        "OFFER_PITCH": {
            "prompt": lambda memory: OutboundRecommendationAgent.generate_offer_pitch(memory),
            "allowed_intents": ["affirmative", "negative", "neutral", "question"],
            "min_confidence": 0.0,
            "transitions": {
                "affirmative": "RELEVANCE_CHECK",
                "neutral": "RELEVANCE_CHECK",
                "negative": "SOFT_CLOSE",
                "question": "FACTUAL_INTERRUPT"
            }
        },
            

        

         "RELEVANCE_CHECK": {
            "prompt": "Should I have someone reach out with the details?",
            "allowed_intents": ["affirmative", "negative", "question", "confused"],
            "min_confidence": 0.5,
            "transitions": {
                "affirmative": "CTA",
                "negative": "SOFT_CLOSE",
                "question": "FACTUAL_INTERRUPT",
                "confused": "FACTUAL_INTERRUPT"
            }
        },


        "FACTUAL_INTERRUPT": {
            "prompt": lambda memory: OutboundRecommendationAgent.generate_factual_response(memory),
            "allowed_intents": ["affirmative", "negative", "neutral", "confused", "question"],
            "min_confidence": 0.0,
            "transitions": {
                "affirmative": "__RETURN__",   # go back to where we came from
                "neutral": "__RETURN__",       # "ok/okay/alright" → return, don't end call
                "negative": "SOFT_CLOSE",
                "confused": "RELEVANCE_CHECK",
                "question": "FACTUAL_INTERRUPT"
            }
        },

        "SOFT_CLOSE": {
            "prompt": "No worries at all. Thanks for your time, and have a great day.",
            "auto": "END"
        },
        
        
        # 4️⃣ CTA — continue, not hang up
        "CTA": {
            "prompt": ("Thanks for that. Someone from our team will reach out shortly with more details."),
            "auto": "END"
        }
        
    }

    @staticmethod
    def generate_offer_pitch(memory):
        prompt = f"""
You are speaking on a real outbound phone call.

STRICT RULES:
- Use the EXACT name provided below, word-for-word
- Do NOT greet (no hello, hi, welcome, etc.)
- Do NOT say "we noticed" or imply prior interest
- Use the clinic name directly
- 2 short sentences MAX
- Plain spoken English
- No marketing language
- End with ONE soft interest question

Template you MUST follow:
Sentence 1: I am speaking on behalf of NAME + location + reason for call 
Sentence 2: What the offer includes
Sentence 3: Soft interest check using this exact wording:
"Would you like us to {memory.get('cta_phrase')}?"

You MUST literally say this name:
NAME: {memory.get("organization_name")}

Service: {memory.get('service_name')}
Location: {memory.get('location')}
Offer details: {memory.get('offer_description')}

Generate the exact spoken pitch now:
"""
        return llm.invoke(prompt).strip().strip('"')

    def outcome(self, memory):
        return {
        "agent": "outbound_recommendation",
        "domain": memory.get("domain"),
        "service": memory.get("service_name"),
        "offer": memory.get("offer_title"),
        "interest_captured": memory.get("interest_captured", False),
        "data": memory
    }
 
    @staticmethod
    def generate_factual_response(memory):
        """
        Handles factual interruptions during outbound calls.
        Rule-based first, LLM fallback last.
        """

        user_input = memory.get("_last_user_input", "").lower().strip()
        location = memory.get("location", "your area")
        service = memory.get("service_name", "our services")

        # -----------------------------
        # 1️⃣ LOCATION QUESTIONS

        # -----------------------------
        # 1️⃣ LOCATION QUESTIONS
        # -----------------------------
        if any(kw in user_input for kw in [
            "where", "location", "located", "address", "clinic", "based"
        ]):
            return (
                f"We’re based in {location} and operate locally in your area. "
            )

        # -----------------------------
        # 2️⃣ OTHER SERVICES
        # -----------------------------
        if any(kw in user_input for kw in [
            "other services", "anything else", "what else", "other options"
        ]):
            return (
                "We do offer other treatments as well. "
                "If you tell me what you’re looking for, I can have the right person help."
            )

        # -----------------------------
        # 3️⃣ PRICING / COST
        # -----------------------------
        if any(kw in user_input for kw in [
            "price", "cost", "charges", "fees", "how much", "pricing"
        ]):
            return (
                "Pricing depends on the consultation, and the initial consultation is free. "
                "Someone from our team can explain the options clearly."
            )

        # -----------------------------
        # 4️⃣ TIMING / AVAILABILITY
        # -----------------------------
        if any(kw in user_input for kw in [
            "when", "timing", "available", "availability", "schedule", "time"
        ]):
            return (
                "Availability varies, but the offer is currently active. "
                "Our team can help find a suitable time."
            )

        if user_input.strip() in ["located", "location"]:
            return f"We’re based in {location}."
       # -----------------------------
        # 5️⃣ CONFUSED / VAGUE INPUT
        # -----------------------------
        if user_input in [
            "what", "huh", "ok", "okay", "not sure", "maybe", "i don't know"
        ]:
            return (
                "No problem at all. "
                f"We’re based in {location}, and the consultation is free. "
                "Would you like to know more about the treatment or pricing?"
            )

        # -----------------------------
        # 6️⃣ DEFAULT SAFE RESPONSE
        # -----------------------------
        return (
            "I can help clarify that. "
            "Would you like someone from our team to walk you through the details?"
        )