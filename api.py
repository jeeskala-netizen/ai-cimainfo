import logging
# ضع هذا في أعلى الملف مرة واحدة
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

def _normalize_gemini_model(model: str) -> str:
    """
    Normalize model identifier so the final path contains exactly one 'models/' prefix.
    Accepts either 'gemini-1.5' or 'models/gemini-1.5' and returns 'models/gemini-1.5'.
    """
    if not model:
        return ""
    model = model.strip()
    # remove accidental leading/trailing slashes
    model = model.strip("/")
    # if already starts with 'models/', keep it; otherwise add prefix
    if model.startswith("models/"):
        return model
    return f"models/{model}"

def _call_gemini(prompt_text: str, temperature: float = 0.7, max_tokens: int = 500) -> str:
    """
    Call Gemini REST generate endpoint. Normalizes model string to avoid double 'models/models'.
    Returns text or an error string starting with 'Error:'.
    """
    if not GEMINI_API_KEY:
        return "Error: Gemini API key not configured."
    if not GEMINI_MODEL:
        return "Error: Gemini model not configured."

    normalized_model = _normalize_gemini_model(GEMINI_MODEL)
    url = f"https://generativelanguage.googleapis.com/v1beta2/{normalized_model}:generate?key={GEMINI_API_KEY}"

    payload = {
        "prompt": {"text": prompt_text},
        "temperature": temperature,
        "maxOutputTokens": max_tokens
    }
    headers = {"Content-Type": "application/json"}

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        # سجل رمز الحالة للاستكشاف
        logger.info("Gemini request to %s returned status %s", url, resp.status_code)
        resp.raise_for_status()
        data = resp.json()
        # سجل الاستجابة الخام عند الحاجة لتصحيح البنية
        logger.debug("Gemini raw response: %s", data)

        # استخراج النص من أشكال الاستجابة الشائعة
        # 1) candidates -> [ { "content": "..."} ]  (أو output.content)
        if isinstance(data, dict):
            # candidates
            candidates = data.get("candidates")
            if isinstance(candidates, list) and len(candidates) > 0:
                cand = candidates[0]
                if isinstance(cand, dict):
                    return cand.get("output", {}).get("content") or cand.get("content") or cand.get("text") or ""
            # output.text
            out = data.get("output")
            if isinstance(out, dict):
                text = out.get("text")
                if text:
                    return text
            # fallback: top-level text/content
            return data.get("text") or data.get("content") or ""
        return ""
    except requests.HTTPError as http_err:
        # سجل جسم الاستجابة إن وُجد لمساعدة التصحيح
        try:
            logger.error("Gemini HTTP error: %s - response: %s", http_err, resp.text)
        except Exception:
            logger.error("Gemini HTTP error: %s", http_err)
        return f"Error: {http_err}"
    except Exception as e:
        logger.exception("Gemini call failed")
        return f"Error: {e}"
