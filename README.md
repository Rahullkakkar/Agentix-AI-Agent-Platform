# 🚀 AI Calling Agent Platform

An end-to-end **AI-powered voice agent** for automated customer outreach, capable of handling multi-turn conversations over real phone calls using LLMs, speech processing, and telephony integration.

---

## 🧠 Overview

This project implements a **production-style outbound calling system** that:

- Initiates automated calls via Exotel telephony APIs  
- Converts user speech to text in real time using Whisper (tiny)  
- Generates intelligent responses using Groq-hosted LLaMA 3.1  
- Maintains conversation context across multiple turns  
- Extracts structured insights for lead qualification  

Designed for real-world outreach use cases across **healthcare, finance, and real estate**.

---


## ⚙️ Tech Stack

- **Backend:** Python, FastAPI  
- **LLM:** Groq (LLaMA 3.1)  
- **Speech-to-Text (STT):** Whisper (tiny)  
- **Telephony:** Exotel API  
- **Data Handling:** Pandas, Excel (XLSX)  
- **Architecture:** REST APIs, Webhooks, LangChain  
- **Deployment:** Linux VPS (Oracle Cloud)

---

## 🔑 Key Features

### 📞 AI Voice Calling
- Automated outbound calls using Exotel  
- Real-time conversational handling via webhook events  

### 🧠 Conversation Engine
- State-machine based dialogue management  
- Intent classification with confidence-based transitions  
- Rolling memory for multi-turn conversations  

### 📊 Campaign Management
- Excel-based lead upload and execution  
- Batch campaign processing using Pandas  
- Per-lead context injection into conversations  

### 🔄 Webhook-Driven Architecture
- Handles real-time call events and user responses  
- Dynamically generates replies during live calls  

### 🧾 Lead Qualification
Extracts structured data such as:
- Interest level  
- Budget  
- Intent  

---

## 🚀 Deployment

- Deployed on a **Linux VPS (Oracle Cloud)**  
- Exposes **HTTPS endpoints** for:
  - REST API routes  
  - Exotel webhook callbacks  
- Supports real-time call handling and processing  

---

## ▶️ How It Works

1. Upload campaign data via Excel  
2. Backend processes leads using Pandas  
3. Exotel initiates outbound calls  
4. User speech is transcribed using Whisper (tiny)  
5. Conversation engine processes context and intent  
6. LLaMA 3.1 generates a response via Groq  
7. Response is played back through telephony  
8. Webhooks update conversation state in real time  

---

## 📌 Future Improvements

- Redis-based conversation memory  
- Conversation summarization / truncation to reduce token usage  
- Advanced TTS integration (e.g., ElevenLabs, Coqui)  
- Dashboard UI for campaign monitoring  
- Multi-agent workflows for complex interactions  

---

## 🤝 Use Cases

- Lead qualification automation  
- Customer outreach campaigns  
- Appointment booking calls  
- Pre-sales customer interaction  

---

## ⚠️ Disclaimer

This project is intended for **educational and experimental purposes**.  
Production use should ensure compliance with telephony regulations and user consent policies.

---

## 📬 Author

**Rahul Kakkar**  
Computer Engineering 

---
