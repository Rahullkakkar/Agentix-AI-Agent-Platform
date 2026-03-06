class LeadQualificationAgent:
    name = "Lead Qualification Agent"
    start_state = "OPEN"

    states = {

        # 1️⃣ Greeting + intent capture
        "OPEN": {
            "prompt": "Hi, how can I help you today?",
            "retry": [
                "Could you tell me a bit more about what you’re looking for?",
                "Just to make sure I understand—what can I help you with today?",
                "What are you hoping to get assistance with?"
            ],
            "allowed_intents": ["loan_request"],
            "min_confidence": 0.4,
            "transitions": {
                "loan_request": "LOAN_AMOUNT"
            }
        },

        # 2️⃣ Loan amount capture
        "LOAN_AMOUNT": {
            "prompt": "Sure. How much loan are you looking for approximately?",
            "retry": [
                "An approximate loan amount would help me assist you better.",
                "Could you share a rough loan amount you have in mind?"
            ],
            "allowed_intents": ["loan_amount_provided"],
            "min_confidence": 0.6,
            "transitions": {
                "loan_amount_provided": "EMPLOYMENT"
            }
        },

        # 3️⃣ Employment type
        "EMPLOYMENT": {
            "prompt": "Got it. Are you currently salaried or self-employed?",
            "retry": [
                "Are you working as a salaried employee or are you self-employed?",
                "Just to confirm, are you salaried or self-employed?"
            ],
            "allowed_intents": [
                "employment_salaried",
                "employment_self_employed"
            ],
            "min_confidence": 0.6,
            "transitions": {
                "employment_salaried": "INCOME",
                "employment_self_employed": "INCOME"
            }
        },

        # 4️⃣ Income capture
        "INCOME": {
            "prompt": "What’s your approximate monthly income?",
            "retry": [
                "A rough estimate of your monthly income would help me guide you better.",
                "Could you share an approximate monthly income?"
            ],
            "allowed_intents": ["income_provided"],
            "min_confidence": 0.6,
            "transitions": {
                "income_provided": "ELIGIBILITY"
            }
        },

        # 5️⃣ Eligibility explanation (SAFE + SMART)
        "ELIGIBILITY": {
            "prompt": lambda memory: (
                f"Thanks for sharing that. Based on a monthly income of ₹{memory.get('income', 0):,}, "
                f"customers are typically eligible for loans up to "
                f"₹{memory.get('income', 0) * 5:,}. "
                + (
                    f"You mentioned needing around ₹{memory.get('loan_amount'):,}. "
                    if memory.get("loan_amount") else ""
                )
                + "I just need to verify a few more details so we can tailor the best offer for you."
            ),
            "auto": "EMAIL"

            
        },

        # 6️⃣ Email collection
        "EMAIL": {
            "prompt": "Could you please share your email address? I’ll send you a secure link there.",
            "retry": [
                "May I have your email address so I can send the secure verification link?",
                "I’ll need an email address to proceed—could you share one?"
            ],
            "allowed_intents": ["email_provided"],
            "min_confidence": 0.6,
            "transitions": {
                "email_provided": "DOCUMENTS"
            }
        },

        # 7️⃣ Document upload confirmation
        "DOCUMENTS": {
            "prompt": (
                "Thanks. I’ve sent a secure link to your email where you can upload your latest paycheck "
                "and a valid ID. Let me know once you’ve completed the upload."
            ),
            "retry": [
                "Just let me know once you’ve uploaded the documents.",
                "Take your time—tell me once the documents are uploaded."
            ],
            "allowed_intents": ["documents_uploaded"],
            "min_confidence": 0.5,
            "transitions": {
                "documents_uploaded": "EMI"
            }
        },

        # 8️⃣ Existing EMI check
        "EMI": {
            "prompt": "One last thing—do you currently have any existing EMIs?",
            "retry": [
                "Do you have any ongoing EMIs at the moment?",
                "Just checking—are there any current EMIs?"
            ],
            "allowed_intents": ["emi_yes", "emi_no"],
            "min_confidence": 0.5,
            "transitions": {
                "emi_yes": "OFFER",
                "emi_no": "OFFER"
            }
        },

        # 9️⃣ Offer + closure
        "OFFER": {
            "prompt": (
                "Perfect. Based on the details you’ve shared, your loan is being processed. "
                "I’ll notify you once it’s approved and share the final offer shortly."
            ),
            "auto": "END"
        }
    }

    def outcome(self, memory):
        return {
            "agent": "lead_qualification",
            "qualified": True,
            "data": memory
        }