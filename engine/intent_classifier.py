from langchain_core.prompts import PromptTemplate
from engine.llm import llm
import json
import re

DEBUG = False


prompt = PromptTemplate(
    template="""
You are an intent classification engine.

Allowed intents:
{allowed_intents}

Rules:
- Respond with JSON only
- No explanations

Output format:
{{
  "intent": "<intent>",
  "confidence": 0.0-1.0,
  "entities": {{}}
}}

Conversation summary:
{summary}

User input:
"{user_input}"
""",
    input_variables=["allowed_intents", "summary", "user_input"],
)

# -------------------------------------------------
# HELPERS
# -------------------------------------------------

def extract_email(text: str):
    match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    return match.group() if match else None


def extract_amount(text: str):
    """
    Handles:
    - 4k, 25k
    - 25 thousand
    - 2 lakh
    - 5 lakhs
    - 3000
    - 3,000
    """
    text = text.lower()

    num_match = re.search(r"\d+(\.\d+)?", text)
    if not num_match:
        return None

    value = float(num_match.group())

    if "k" in text:
        return int(value * 1000)
    if "thousand" in text:
        return int(value * 1000)
    if "lakh" in text:
        return int(value * 100000)
    if "lakhs" in text:
        return int(value * 100000)
    if ",000" in text:
        return int(value * 1000)


    return int(value)


# -------------------------------------------------
# MAIN CLASSIFIER
# -------------------------------------------------

def classify_intent(user_input, allowed_intents, summary):
    text = user_input.lower().strip()

    # =================================================
    # HARD GUARDED INTENTS (ORDER IS CRITICAL)
    # =================================================

    # 1️⃣ Loan request
    if "loan" in text and "loan_request" in allowed_intents:
        return "loan_request", 0.95, {}

    # 2️⃣ Loan amount capture
    if "loan_amount_provided" in allowed_intents:
        amount = extract_amount(text)
        if amount:
            return "loan_amount_provided", 0.9, {"loan_amount": amount}

    # 3️⃣ Email capture
    email = extract_email(text)
    if email and "email_provided" in allowed_intents:
        return "email_provided", 0.95, {"email": email}

    # 4️⃣ Income capture (guard absurd values)
    if "income_provided" in allowed_intents:
        amount = extract_amount(text)
        if amount and amount >= 1000:
            return "income_provided", 0.9, {"income": amount}
        elif amount:
            # 10 rupees, 50, etc → force retry
            return "confused", 0.2, {}

    # 5️⃣ EMI handling
    if "emi_yes" in allowed_intents and (
        "emi" in text or text.startswith("yes")
    ):
        count = extract_amount(text) or 1
        return "emi_yes", 0.85, {"emi_count": count}

    if "emi_no" in allowed_intents and text in ["no", "nope", "nah"]:
        return "emi_no", 0.85, {}

    # 6.5️⃣ Question detection (outbound-safe) — must run BEFORE affirmative
    if "question" in allowed_intents:
        if any(word in text for word in [
            "where", "what", "how", "when", "price", "cost", "location", "services",
            "time", "timing", "available", "availability", "schedule",
            "charges", "fees", "how much", "address", "clinic", "based",
            "other services", "anything else", "what else"
        ]):
            return "question", 0.85, {}

    # Strip leading filler sounds once, reused for all checks below
    cleaned = re.sub(r"^(uh+|um+|hmm+|err+|ah+)[\s\.,]*", "", text).strip()

    # 6️⃣ Simple affirm / deny
    # "ok/okay" alone = neutral, but "okay go ahead", "okay sure" etc = affirmative
    AFFIRM_WORDS = [
        "yes", "yeah", "sure", "yep", "absolutely", "of course",
        "go ahead", "go on", "proceed", "do it", "please", "sounds good",
        "that works", "lets do it", "let's do it"
    ]
    if "affirmative" in allowed_intents and (
        text in AFFIRM_WORDS
        or cleaned in AFFIRM_WORDS
        or any(w in text for w in AFFIRM_WORDS)
    ):
        return "affirmative", 0.7, {}

    if "negative" in allowed_intents and text in ["no", "nah", "nope"]:
        return "negative", 0.7, {}

    # 6.7️⃣ Acknowledgement words → neutral
    # cleaned handles filler-prefixed variants: "uh okay", "uhhhh okay"
    if text in ["ok", "okay", "alright", "right", "i see", "got it", "fine"] or \
       cleaned in ["ok", "okay", "alright", "right", "i see", "got it", "fine"]:
        if "neutral" in allowed_intents:
            return "neutral", 0.75, {}
        if "confused" in allowed_intents:
            return "confused", 0.6, {}
    # =================================================
    # LLM FALLBACK
    # =================================================

    try:
        raw = llm.invoke(
            prompt.format(
                allowed_intents=allowed_intents,
                summary=summary,
                user_input=user_input
            )
        )

        if DEBUG:
            print(raw)

        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start == -1 or end == -1:
            raise ValueError("No JSON")

        data = json.loads(raw[start:end])
        intent = data.get("intent")
        confidence = float(data.get("confidence", 0.0))

        if intent not in allowed_intents:
            raise ValueError("Invalid intent")

        return intent, confidence, {}

    except Exception:
        pass

    # =================================================
    # FINAL SAFE FALLBACK
    # =================================================

    return "confused", 0.0, {}