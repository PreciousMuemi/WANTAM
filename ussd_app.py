import os
import logging
import threading
from typing import Dict, Optional

from flask import Flask, request, Response
from dotenv import load_dotenv
from supabase import create_client
import requests

from katiba_rag import KatibaRAG

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
AT_USERNAME = os.getenv("AT_USERNAME", "")
AT_API_KEY = os.getenv("AT_API_KEY", "")
AT_SENDER_ID = os.getenv("AT_SENDER_ID", "")
AT_SMS_URL = os.getenv("AT_SMS_URL", "https://api.africastalking.com/version1/messaging")

# In-memory session tracker
SESSION_STATE: Dict[str, Dict[str, str]] = {}
SESSION_LOCK = threading.Lock()

# Lazy-loaded clients
_supabase_client = None
_rag = None


def get_supabase_client():
    global _supabase_client
    if _supabase_client is None and SUPABASE_URL and SUPABASE_KEY:
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase_client


def get_rag():
    global _rag
    if _rag is None:
        _rag = KatibaRAG()
    return _rag


def store_question(session_id: str, phone_number: str, question: str) -> Optional[int]:
    client = get_supabase_client()
    if not client:
        logger.warning("Supabase not configured. Skipping question storage.")
        return None

    try:
        response = client.table("questions").insert({
            "session_id": session_id,
            "phone_number": phone_number,
            "question": question,
            "status": "pending"
        }).execute()
        if response.data:
            return response.data[0].get("id")
        return None
    except Exception as e:
        logger.error(f"Error inserting question: {e}")
        return None


def update_question(question_id: int, status: str, answer: Optional[str] = None, error: Optional[str] = None):
    client = get_supabase_client()
    if not client or not question_id:
        return

    payload = {"status": status}
    if answer:
        payload["answer"] = answer
    if error:
        payload["error"] = error

    try:
        client.table("questions").update(payload).eq("id", question_id).execute()
    except Exception as e:
        logger.error(f"Error updating question {question_id}: {e}")


def send_sms(to_number: str, message: str) -> bool:
    if not AT_USERNAME or not AT_API_KEY:
        logger.warning("Africa's Talking not configured. Skipping SMS send.")
        return False

    payload = {
        "username": AT_USERNAME,
        "to": to_number,
        "message": message
    }
    if AT_SENDER_ID:
        payload["from"] = AT_SENDER_ID

    headers = {
        "apiKey": AT_API_KEY,
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    try:
        response = requests.post(AT_SMS_URL, data=payload, headers=headers, timeout=30)
        if response.status_code >= 400:
            logger.error(f"SMS send failed: {response.status_code} {response.text}")
            return False
        return True
    except Exception as e:
        logger.error(f"SMS send error: {e}")
        return False


def build_sms_answer(answer_text: str) -> str:
    max_len = 780
    cleaned = " ".join(answer_text.split())
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[:max_len - 3] + "..."


def _sms_suffix() -> str:
    return "Reply HELP for menu | kenyalaw.org"


def _paginate_sms(text: str, max_len: int = 160) -> str:
    suffix = _sms_suffix()
    cleaned = " ".join(text.split())

    if len(cleaned) + 1 + len(suffix) <= max_len:
        return f"{cleaned} {suffix}"

    # Reserve space for pagination label like "1/2 "
    parts = []
    remaining = cleaned
    page = 1
    while remaining:
        label = f"{page}/{{total}} "
        available = max_len - len(label) - 1 - len(suffix)
        if available <= 0:
            break
        chunk = remaining[:available]
        remaining = remaining[available:].lstrip()
        parts.append(chunk)
        page += 1

    total = len(parts)
    formatted = [f"{i+1}/{total} {parts[i]} {suffix}" for i in range(total)]
    return "\n".join(formatted)


def _help_menu() -> str:
    return (
        "Send: RIGHTS | ARREST | BILL [name] | KATIBA [question]"
    )


def _rights_summary() -> str:
    return (
        "Rights: life, dignity, freedom, privacy, expression, assembly, movement, religion, "
        "health, education, fair trial, equality, property (Art 26-57)."
    )


def _arrest_summary() -> str:
    return (
        "Arrest rights: be told reason, remain silent, contact lawyer/family, be charged or released "
        "within 24h, humane treatment (Art 49)."
    )


def async_answer_and_sms(session_id: str, phone_number: str, question: str, question_id: Optional[int]):
    try:
        rag = get_rag()
        result = rag.answer(question)
        answer = result.get("answer", "I don't have that information, but you can check kenyalaw.org")
        message = build_sms_answer(answer)

        if send_sms(phone_number, message):
            update_question(question_id, status="sent", answer=message)
        else:
            update_question(question_id, status="failed", error="SMS send failed")
    except Exception as e:
        logger.error(f"Async processing error: {e}")
        update_question(question_id, status="failed", error=str(e))


def parse_text(text: str) -> list:
    if text is None:
        return []
    if not text.strip():
        return []
    return [seg for seg in text.split("*") if seg != ""]


def main_menu() -> str:
    return (
        "CON Welcome to Katiba AI 🇰🇪\n"
        "1. Know Your Rights\n"
        "2. Understand a Bill\n"
        "3. Ask Any Question\n"
        "4. Recent Laws Explained"
    )


def know_your_rights_menu() -> str:
    return (
        "CON Choose a topic:\n"
        "1. Arrested by Police\n"
        "2. Landlord & Tenant\n"
        "3. Employment Rights\n"
        "4. Back"
    )


def bills_menu() -> str:
    return (
        "CON Recent Bills:\n"
        "1. Finance Act 2023\n"
        "2. Housing Fund Act\n"
        "3. Data Protection Act\n"
        "4. Back"
    )


def invalid_choice() -> str:
    return "CON Invalid choice.\n" + main_menu().replace("CON ", "")


def handle_ussd(session_id: str, phone_number: str, text: str) -> str:
    segments = parse_text(text)

    with SESSION_LOCK:
        SESSION_STATE[session_id] = {
            "last_text": text or "",
            "phone_number": phone_number
        }

    if not segments:
        return main_menu()

    level1 = segments[0]

    if level1 == "1":
        if len(segments) == 1:
            return know_your_rights_menu()
        if segments[1] == "4":
            return main_menu()
        if segments[1] in {"1", "2", "3"}:
            return "END Thanks! Use option 3 to ask a specific question."
        return invalid_choice()

    if level1 == "2":
        if len(segments) == 1:
            return bills_menu()
        if segments[1] == "4":
            return main_menu()
        if segments[1] in {"1", "2", "3"}:
            return "END Thanks! Use option 3 to ask a specific question."
        return invalid_choice()

    if level1 == "3":
        if len(segments) == 1:
            return "CON Type your question and we'll SMS you the answer within 1 minute."

        question = "*".join(segments[1:]).strip()
        if len(question) < 5:
            return "CON Please type a full question (at least 5 characters)."

        question_id = store_question(session_id, phone_number, question)
        thread = threading.Thread(
            target=async_answer_and_sms,
            args=(session_id, phone_number, question, question_id),
            daemon=True
        )
        thread.start()

        return "END Your answer is being sent to this number via SMS!"

    if level1 == "4":
        return "END Coming soon. Use option 3 to ask about recent laws."

    return invalid_choice()


@app.route("/ussd", methods=["POST"])
def ussd_callback():
    session_id = request.form.get("sessionId", "")
    phone_number = request.form.get("phoneNumber", "")
    text = request.form.get("text", "")

    if not session_id:
        return Response("END Missing sessionId", mimetype="text/plain")
    if not phone_number:
        return Response("END Missing phoneNumber", mimetype="text/plain")

    response = handle_ussd(session_id, phone_number, text)
    return Response(response, mimetype="text/plain")


@app.route("/health", methods=["GET"])
def health_check():
    return {"status": "ok"}


@app.route("/sms", methods=["POST"])
def sms_callback():
    text = (request.form.get("text") or "").strip()
    from_number = (request.form.get("from") or request.form.get("phoneNumber") or "").strip()

    if not text:
        return Response(_paginate_sms(_help_menu()), mimetype="text/plain")

    upper = text.upper().strip()

    if upper == "HELP":
        return Response(_paginate_sms(_help_menu()), mimetype="text/plain")

    if upper == "RIGHTS":
        return Response(_paginate_sms(_rights_summary()), mimetype="text/plain")

    if upper == "ARREST":
        return Response(_paginate_sms(_arrest_summary()), mimetype="text/plain")

    if upper.startswith("BILL "):
        bill_name = text[5:].strip()
        if not bill_name:
            return Response(_paginate_sms("Please provide a bill name. Example: BILL HOUSING"), mimetype="text/plain")
        query = f"What does the {bill_name} bill say? Provide a short summary."
        try:
            answer = get_rag().answer(query).get("answer", "I don't have that information, but you can check kenyalaw.org")
        except Exception as e:
            logger.error(f"RAG error (BILL): {e}")
            answer = "I don't have that information, but you can check kenyalaw.org"
        return Response(_paginate_sms(answer), mimetype="text/plain")

    if upper.startswith("KATIBA "):
        question = text[7:].strip()
        if not question:
            return Response(_paginate_sms("Please provide a question after KATIBA."), mimetype="text/plain")
        try:
            answer = get_rag().answer(question).get("answer", "I don't have that information, but you can check kenyalaw.org")
        except Exception as e:
            logger.error(f"RAG error (KATIBA): {e}")
            answer = "I don't have that information, but you can check kenyalaw.org"
        return Response(_paginate_sms(answer), mimetype="text/plain")

    return Response(_paginate_sms(_help_menu()), mimetype="text/plain")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
