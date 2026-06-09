from langchain_classic.memory import ConversationBufferMemory
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
import google.generativeai as genai

from src.retriever import retrieve_docs
from src.config import GROQ_API_KEY, GEMINI_API_KEY, OPENAI_API_KEY, LLM_MODEL, FALLBACK_MODEL

# ── Configure Gemini for translation ─────────────────────
genai.configure(api_key=GEMINI_API_KEY)

# ── 1. LLMs ───────────────────────────────────────────────

# Primary: Gemini 2.5 Flash
_primary_llm = ChatGoogleGenerativeAI(
    google_api_key=GEMINI_API_KEY,
    model=LLM_MODEL,
    temperature=0.7
)
_primary_rewrite_llm = ChatGoogleGenerativeAI(
    google_api_key=GEMINI_API_KEY,
    model=LLM_MODEL,
    temperature=0
)

# Fallback: Groq Llama 3.3 70B
_fallback_llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model_name=FALLBACK_MODEL,
    temperature=0.7
)
_fallback_rewrite_llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model_name=FALLBACK_MODEL,
    temperature=0
)


# ── 2. Fallback invoke ────────────────────────────────────
GEMINI_RATE_LIMIT_PHRASES = (
    "rate_limit_exceeded", "rate limit",
    "429", "too many requests",
    "quota", "resource_exhausted",
    "tokens per minute", "requests per minute",
)

def _is_rate_limit_error(e: Exception) -> bool:
    return any(p in str(e).lower() for p in GEMINI_RATE_LIMIT_PHRASES)

def invoke_llm(messages, temperature: float = 0.7) -> str:
    primary_llm  = _primary_llm  if temperature > 0 else _primary_rewrite_llm
    fallback_llm = _fallback_llm if temperature > 0 else _fallback_rewrite_llm
    try:
        result = primary_llm.invoke(messages)
        print("[LLM] Gemini 2.5 Flash responded successfully.")
        return result.content.strip()
    except Exception as e:
        if _is_rate_limit_error(e):
            print(f"[LLM] Gemini rate limit — switching to Groq. Error: {e}")
            result = fallback_llm.invoke(messages)
            print("[LLM] Groq responded successfully.")
            return result.content.strip()
        raise

# ── 3. Translation using Gemini directly ─────────────────
def translate_to_english(text: str) -> str:
    try:
        model    = genai.GenerativeModel("gemini-2.5-flash-preview-05-20")
        response = model.generate_content(
            f"""Translate this text to English.
Return ONLY the English translation as a single natural sentence.
Do NOT include any explanation, alternatives, punctuation at the end, or extra text.

Text to translate: {text}"""
        )
        translated = response.text.strip().strip(".")
        print(f"[Translator] '{text}' → '{translated}'")
        return translated
    except Exception as e:
        print(f"[Translator] Gemini translation failed: {e} — trying Groq")
        try:
            result = _fallback_llm.invoke([
                {"role": "system", "content": "Translate to English. Return ONLY the translation, nothing else."},
                {"role": "user",   "content": f"Translate: {text}"}
            ])
            translated = result.content.strip()
            print(f"[Translator] Groq translated: '{translated}'")
            return translated
        except Exception as e2:
            print(f"[Translator] All translation failed: {e2}")
            return text
# ── 4. Memory ─────────────────────────────────────────────
_memory_store: dict[str, ConversationBufferMemory] = {}

def get_memory(session_id: str) -> ConversationBufferMemory:
    if session_id not in _memory_store:
        _memory_store[session_id] = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="answer"
        )
    return _memory_store[session_id]

def clear_memory(session_id: str) -> None:
    if session_id in _memory_store:
        del _memory_store[session_id]

# ── 5. Language instruction ───────────────────────────────
def get_language_instruction(language: str) -> str:
    return (
        f"\n\nLANGUAGE INSTRUCTION:\n"
        f"You MUST respond ENTIRELY in {language}.\n"
        f"Every word of your answer must be in {language}.\n"
        f"Do not mix any other language.\n"
        f"Even if the question is in a different language, answer in {language}."
    )

# ── 6. Query rewriter ─────────────────────────────────────
REWRITE_SYSTEM_PROMPT = """You are a query rewriter for an AI assistant.
Your ONLY job is to rewrite the user's latest question so it is completely
self-contained and explicit — replacing all vague pronouns and references
(like "it", "that", "there", "both", "the first one")
with the actual subjects found in the conversation history.
Rules:
- If the question is already explicit and clear, return it unchanged.
- Return ONLY the rewritten question. No explanation. No extra text. No punctuation at end.
- Do not answer the question. Just rewrite it.
- Always rewrite in English regardless of input language.
Conversation history:
{chat_history}
"""
REWRITE_HUMAN_PROMPT = "Rewrite this question to be explicit: {question}"

rewrite_prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(REWRITE_SYSTEM_PROMPT),
    HumanMessagePromptTemplate.from_template(REWRITE_HUMAN_PROMPT)
])

def rewrite_query(raw_query: str, chat_history_text: str) -> str:
    if not chat_history_text.strip():
        return raw_query
    vague_words = [
        "it", "that", "there", "both", "this", "those",
        "the same", "first one", "second one", "here"
    ]
    if not any(word in raw_query.lower() for word in vague_words):
        print(f"[QueryRewriter] Already explicit — skipping: '{raw_query}'")
        return raw_query
    print(f"[QueryRewriter] Rewriting: '{raw_query}'")
    formatted = rewrite_prompt.format_messages(
        chat_history=chat_history_text,
        question=raw_query
    )
    rewritten = invoke_llm(formatted, temperature=0)
    print(f"[QueryRewriter] Result: '{rewritten}'")
    return rewritten

# ── 7. Prompts ────────────────────────────────────────────
PDF_ANSWER_SYSTEM_PROMPT = """You are a helpful and expert AI assistant for {business_name}.
{business_context}

Use the following document context to answer the user's question.

CRITICAL RULES:
1. Read the user's question carefully and identify exactly what they are asking about
2. Read the context carefully
3. Ask yourself:
"Does this context match BOTH:
    1. the specific topic/subject being asked about
    2. the actual question being asked?"
4. If YES → answer ONLY using the provided context
5. You may improve grammar and sentence flow
6. NEVER add facts, figures, names, prices, or details that are not explicitly present in the context

STRICT DOCUMENT MODE:
- Use ONLY information explicitly present in the context
- NEVER invent names, prices, dates, contacts, policies, products, or any details
- NEVER complete missing information using your own knowledge
- If the document contains only limited information, give only limited information
- Do NOT expand the answer beyond the provided context
- Your job is to summarize document content, NOT generate new information

VERY IMPORTANT FILTERING RULE:
- Ignore unrelated paragraphs even if they appear in the same chunk
- Extract ONLY sentences directly related to the user's question
- If user asks about pricing, ignore unrelated policies, contacts, or descriptions
- If user asks about contact, ignore products and pricing
- Never summarize the whole chunk unless the user explicitly asks for all information

IMPORTANT BEHAVIOR:
- Use ONLY the provided document context
- NEVER use outside/general knowledge
- If partial relevant information exists, answer using ONLY that information
- You may summarize and reorganize the document content naturally
- Ignore unrelated text even if it appears in the same chunk
- Return NO_CONTEXT ONLY if absolutely no relevant information exists

IMPORTANT RULES FOR NO_CONTEXT:
- Return ONLY the single word: NO_CONTEXT
- No emoji, no explanation, no extra text — just: NO_CONTEXT
- Do this ONLY when context has ZERO relevant info about what user asked

FINAL STRICT RULE:
- If a sentence does not directly answer the user's question, DO NOT include it
- Prefer incomplete but accurate answers over extra unrelated information

═══════════════════════════════════════════════════════════════
ANSWER FORMAT INSTRUCTIONS:
═══════════════════════════════════════════════════════════════

STEP 1: IDENTIFY QUERY TYPE
━━━━━━━━━━━━━━━━━━━━━━━━━━
Detect what the user is asking:
- General info / overview  → Give a clear summary
- Pricing / cost           → Give only pricing details
- Contact / location       → Give only contact or location info
- Products / services      → List relevant products or services
- Policies / rules         → Explain the relevant policy clearly
- How to / process         → Give step-by-step instructions
- Specific item / person   → Give details about that specific item or person

STEP 2: STRICT ANSWER RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━
GOLDEN RULE: Answer EXACTLY what the user asked. Nothing more. Nothing less.

- Ignore all unrelated information in the context even if it appears in the same retrieved chunk
- Extract and answer ONLY the parts directly relevant to the user's query
- Never summarize the full chunk unless the user explicitly asked for everything

IF user asks "what is this about"    → give a brief overview only
IF user asks "pricing"               → give ONLY pricing
IF user asks "contact"               → give ONLY contact details
IF user asks "how to"                → give ONLY steps/process
IF user asks "policies"              → give ONLY relevant policies
IF user asks about a specific item   → give ONLY details of that item

WARNINGS — STRICT RULES:
- ONLY add ⚠️ warning if user SPECIFICALLY asked for that info AND it is missing from context
- If user asked ONLY for an overview → NO pricing warning, NO contact warning, NOTHING extra
- If user asked for pricing and it is NOT in context → add warning
- If user did NOT ask for something → DO NOT mention it at all

STEP 3: FORMAT BEAUTIFULLY
━━━━━━━━━━━━━━━━━━━━━━━━━━

FOR OVERVIEW / GENERAL QUESTIONS:
✅ Write in clear flowing paragraphs
✅ Keep it concise and informative
✅ Make it engaging and easy to read

FOR LIST-TYPE ANSWERS (products, services, steps, policies):
✅ Use bullet points (-) for each item
✅ Give a brief description for each point
✅ Group related items under clear headers if needed
✅ Add blank line between groups

FOR PROCESS / HOW-TO QUESTIONS:
✅ Use numbered steps
✅ Keep each step clear and actionable
✅ One action per step

STRICTLY FORBIDDEN:
❌ NEVER invent information not present in the context
❌ NEVER add suggestions or recommendations beyond the context
❌ NEVER use filler phrases like "Great question!" or "Certainly!"
❌ NEVER repeat the user's question back to them
❌ Write naturally like a knowledgeable expert helping a real person

═══════════════════════════════════════════════════════════════

Context from documents:
{{context}}

STRICT SOURCE RULE:
- Your answer must be grounded ONLY in the provided document context
- Do NOT use outside knowledge
- Do NOT invent information
- Do NOT add details unless explicitly present in context

Conversation so far:
{{chat_history}}

{language_instruction}
"""

GENERAL_ANSWER_SYSTEM_PROMPT = """You are a helpful and expert AI assistant for {business_name}.
{business_context}

⚠️ IMPORTANT: The user's question is NOT covered by the uploaded documents.
You are answering from your GENERAL KNOWLEDGE.

INSTRUCTIONS:
1. Provide helpful, accurate information based on your knowledge
2. Be honest if you are not 100% certain — say so clearly
3. Format beautifully and naturally
4. Stay relevant to the business context described above
5. Do not make up specific details like prices, contacts, or policies
   unless they are universally known facts

FOR OVERVIEW / GENERAL QUESTIONS:
- Write in natural, flowing paragraphs
- Be conversational and friendly
- Keep it concise

FOR LIST-TYPE ANSWERS:
- Use bullet points for clarity
- Brief description for each item
- Group under headers if needed

FOR PROCESS / HOW-TO:
- Use numbered steps
- Keep each step clear and actionable

STRICTLY FORBIDDEN:
❌ NEVER invent specific business details (prices, contacts, policies, staff names)
❌ NEVER use filler phrases like "Great question!" or "Certainly!"
❌ NEVER repeat the user's question back to them

Conversation so far:
{{chat_history}}

{language_instruction}
"""

# ── 8. Main answer function ───────────────────────────────
def generate_answer(
    query:            str,
    session_id:       str  = "default",
    use_general:      bool = False,
    language:         str  = "English",
    collection_name:  str  = "default",
    business_name:    str  = "AI Assistant",
    business_context: str  = "You are a helpful assistant that answers questions accurately."
) -> dict:

    memory       = get_memory(session_id)
    history_vars = memory.load_memory_variables({})
    history_msgs = history_vars.get("chat_history", [])

    history_text = ""
    for msg in history_msgs:
        role          = "User" if msg.type == "human" else "Assistant"
        history_text += f"{role}: {msg.content}\n"

    original_query = query

    # ── Language detection and translation ───────────────────
    try:
        from langdetect import detect
        detected_lang = detect(query)
        was_translated = detected_lang != "en"
        print(f"[Generator] Detected language: '{detected_lang}'")
    except Exception:
        was_translated = not all(ord(char) < 128 for char in query)

    if was_translated:
        print(f"[Generator] Translating: '{query}'")
        query_for_search = None

    # Try gemini-1.5-flash first, then gemini-2.0-flash, then groq
    translation_attempts = [
        ("gemini-1.5-flash",   "gemini"),
        ("gemini-2.0-flash",   "gemini"),
        (LLM_MODEL,            "groq"),
    ]

    for model_name, provider in translation_attempts:
        try:
            if provider == "gemini":
                model    = genai.GenerativeModel(model_name)
                response = model.generate_content(
                    f"Translate this text to English. Return ONLY the English translation as a natural sentence, nothing else:\n{query}"
                )
                query_for_search = response.text.strip().strip(".")
            else:
                query_for_search = invoke_llm([
                    {"role": "system", "content": "You are a translator. Translate the given text to English. Return ONLY the English translation as a natural sentence. Nothing else."},
                    {"role": "user",   "content": f"Translate to English: {query}"}
                ])
            print(f"[Generator] Translated using {model_name}: '{query_for_search}'")
            break
        except Exception as e:
            print(f"[Generator] Translation failed with {model_name}: {e}")
            continue

    if not query_for_search or query_for_search == query:
        # All translation attempts failed — use English query from language param
        print(f"[Generator] All translations failed — asking user in {language}")
        return {
            "answer":          "I'm having trouble processing your query right now. Please try again in a moment or ask in English.",
            "rewritten_query": query,
            "has_pdf_context": False
        }
    else:
        query_for_search = query
        query_for_search = invoke_llm([
        {"role": "system", "content": "Correct spelling mistakes in this query. Return ONLY the corrected query, nothing else."},
        {"role": "user",   "content": f"Correct: {query_for_search}"}
    ])
    print(f"[Generator] Corrected: '{query_for_search}'")

    # Skip rewriting for translated queries
    if was_translated:
        rewritten_query = query_for_search
        print(f"[Generator] Using translated query for search: '{rewritten_query}'")
    else:
        rewritten_query = rewrite_query(query_for_search, history_text)

    # ── Rewrite only for English queries ─────────────────
    if was_translated:
        rewritten_query = query_for_search
        print(f"[Generator] Skipping rewrite for translated query: '{rewritten_query}'")
    else:
        rewritten_query = rewrite_query(query_for_search, history_text)

    lang_instruction = get_language_instruction(language)
    print(f"[Generator] Language: '{language}' | Business: '{business_name}'")
    print(f"[Generator] Final search query: '{rewritten_query}'")

    # ── Path A: General knowledge ─────────────────────────
    if use_general:
        print(f"[Generator] General knowledge path")
        system_prompt = GENERAL_ANSWER_SYSTEM_PROMPT.format(
            business_name=business_name,
            business_context=business_context,
            language_instruction=lang_instruction
        )
        prompt    = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_prompt),
            HumanMessagePromptTemplate.from_template("{question}")
        ])
        formatted = prompt.format_messages(
            chat_history=history_text,
            question=original_query
        )
        answer = invoke_llm(formatted)
        memory.save_context({"input": original_query}, {"answer": answer})
        return {
            "answer":          answer,
            "rewritten_query": rewritten_query,
            "has_pdf_context": False
        }

    # ── Path B: PDF retrieval ─────────────────────────────
    docs    = retrieve_docs(rewritten_query, collection_name)
    context = "\n".join(docs)

    if not context.strip():
        print(f"[Generator] No context found for: '{rewritten_query}'")
        return {
            "answer":          None,
            "rewritten_query": rewritten_query,
            "has_pdf_context": False
        }

    print(f"[Generator] Context found — answering from documents")
    system_prompt = PDF_ANSWER_SYSTEM_PROMPT.format(
        business_name=business_name,
        business_context=business_context,
        language_instruction=lang_instruction
    )
    prompt    = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system_prompt),
        HumanMessagePromptTemplate.from_template("{question}")
    ])
    formatted = prompt.format_messages(
        context=context,
        chat_history=history_text,
        question=original_query
    )
    answer = invoke_llm(formatted)

    if "NO_CONTEXT" in answer:
        print(f"[Generator] LLM found no relevant context")
        return {
            "answer":          None,
            "rewritten_query": rewritten_query,
            "has_pdf_context": False
        }

    memory.save_context({"input": original_query}, {"answer": answer})
    return {
        "answer":          answer,
        "rewritten_query": rewritten_query,
        "has_pdf_context": True
    }