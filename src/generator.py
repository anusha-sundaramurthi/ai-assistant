from langchain_classic.memory import ConversationBufferMemory
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI

from src.retriever import retrieve_docs
from src.config import GROQ_API_KEY, GEMINI_API_KEY, LLM_MODEL, FALLBACK_MODEL

# ── 1. Build primary (Groq) and fallback (Gemini) LLMs ───
_groq_llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model_name=LLM_MODEL,
    temperature=0.7
)

_gemini_llm = ChatGoogleGenerativeAI(
    google_api_key=GEMINI_API_KEY,
    model=FALLBACK_MODEL,
    temperature=0.7
)

_groq_rewrite_llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model_name=LLM_MODEL,
    temperature=0
)

_gemini_rewrite_llm = ChatGoogleGenerativeAI(
    google_api_key=GEMINI_API_KEY,
    model=FALLBACK_MODEL,
    temperature=0
)

# ── 2. Smart invoke — falls back to Gemini on Groq rate limit ──
GROQ_RATE_LIMIT_PHRASES = (
    "rate_limit_exceeded",
    "rate limit",
    "429",
    "too many requests",
    "tokens per minute",
    "requests per minute",
)

def _is_rate_limit_error(e: Exception) -> bool:
    msg = str(e).lower()
    return any(phrase in msg for phrase in GROQ_RATE_LIMIT_PHRASES)

def invoke_llm(messages, temperature: float = 0.7) -> str:
    """
    Try Groq first. If a rate-limit error is raised, fall back to Gemini Flash.
    Returns the response content as a string.
    """
    # Choose LLM based on requested temperature
    groq_llm   = _groq_llm   if temperature > 0 else _groq_rewrite_llm
    gemini_llm = _gemini_llm if temperature > 0 else _gemini_rewrite_llm

    try:
        result = groq_llm.invoke(messages)
        print("[LLM] Groq responded successfully.")
        return result.content.strip()
    except Exception as e:
        if _is_rate_limit_error(e):
            print(f"[LLM] Groq rate limit hit — switching to Gemini Flash. Error: {e}")
            result = gemini_llm.invoke(messages)
            print("[LLM] Gemini Flash responded successfully.")
            return result.content.strip()
        raise  # re-raise non-rate-limit errors as usual


# ── 3. Per-session memory store ───────────────────────────
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

# ── 4. Language instruction ───────────────────────────────
def get_language_instruction(language: str) -> str:
    return (
        f"\n\nLANGUAGE INSTRUCTION:\n"
        f"You MUST respond ENTIRELY in {language}.\n"
        f"Every word of your answer must be in {language}.\n"
        f"Do not mix any other language.\n"
        f"Even if the question is in a different language, answer in {language}."
    )

# ── 5. Query rewriter ─────────────────────────────────────
REWRITE_SYSTEM_PROMPT = """You are a query rewriter for a travel assistant.
Your ONLY job is to rewrite the user's latest question so it is completely
self-contained and explicit — replacing all vague pronouns and references
(like "there", "it", "that place", "both", "the first one", "that city")
with the actual destination names found in the conversation history.
Rules:
- If the question mentions multiple destinations implicitly, name ALL of them.
- If the question is already explicit and clear, return it unchanged.
- Return ONLY the rewritten question. No explanation. No extra text.
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
        "there", "it", "that place", "both", "the city",
        "that country", "first one", "second one", "those",
        "the destination", "that", "here", "same place"
    ]
    if not any(word in raw_query.lower() for word in vague_words):
        print(f"[QueryRewriter] Already explicit — skipping: '{raw_query}'")
        return raw_query
    print(f"[QueryRewriter] Rewriting vague query: '{raw_query}'")
    formatted = rewrite_prompt.format_messages(
        chat_history=chat_history_text,
        question=raw_query
    )
    rewritten = invoke_llm(formatted, temperature=0)
    print(f"[QueryRewriter] Result: '{rewritten}'")
    return rewritten

# ── 6. Prompts ────────────────────────────────────────────
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

# ── 7. Main answer function ───────────────────────────────
def generate_answer(
    query:           str,
    session_id:      str  = "default",
    use_general:     bool = False,
    language:        str  = "English",
    collection_name: str  = "default"   
) -> dict:
    memory       = get_memory(session_id)
    history_vars = memory.load_memory_variables({})
    history_msgs = history_vars.get("chat_history", [])

    history_text = ""
    for msg in history_msgs:
        role          = "User" if msg.type == "human" else "Assistant"
        history_text += f"{role}: {msg.content}\n"

    original_query = query

    # Translate non-ASCII queries to English for search
    if not all(ord(char) < 128 for char in query):
        print(f"[Generator] Non-English query detected: '{query}'")
        query_for_search = invoke_llm([
            {"role": "system", "content": "You are a translator. Translate to English."},
            {"role": "user",   "content": f"Translate this to English, keep it concise: {query}"}
        ])
        print(f"[Generator] English translation: '{query_for_search}'")
    else:
        query_for_search = query

    # Spell-correct
    query_for_search = invoke_llm([
        {"role": "system", "content": "You correct spelling mistakes in travel queries."},
        {"role": "user",   "content": f"Correct spelling mistakes in this travel query. Return ONLY the corrected query. Do not change meaning.\n\nQuery: {query_for_search}"}
    ])
    print(f"[Generator] Corrected query: '{query_for_search}'")

    rewritten_query  = rewrite_query(query_for_search, history_text)
    lang_instruction = get_language_instruction(language)
    print(f"[Generator] Language: '{language}'")

    # ── Path A: General knowledge ─────────────────────────
    if use_general:
        print(f"[Generator] General knowledge path for: '{original_query}'")
        system_prompt = GENERAL_ANSWER_SYSTEM_PROMPT.format(language_instruction=lang_instruction)
        prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_prompt),
            HumanMessagePromptTemplate.from_template("{question}")
        ])
        formatted = prompt.format_messages(chat_history=history_text, question=original_query)
        answer    = invoke_llm(formatted)
        memory.save_context({"input": original_query}, {"answer": answer})
        return {"answer": answer, "rewritten_query": rewritten_query, "has_pdf_context": False}

    # ── Path B: PDF retrieval ─────────────────────────────
    docs = retrieve_docs(rewritten_query, collection_name)
    context = "\n".join(docs)

    if not context.strip():
        print(f"[Generator] No PDF context for: '{original_query}' → asking user")
        return {"answer": None, "rewritten_query": rewritten_query, "has_pdf_context": False}

    print(f"[Generator] PDF context found for: '{original_query}'")
    system_prompt = PDF_ANSWER_SYSTEM_PROMPT.format(language_instruction=lang_instruction)
    prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system_prompt),
        HumanMessagePromptTemplate.from_template("{question}")
    ])
    formatted = prompt.format_messages(context=context, chat_history=history_text, question=original_query)
    answer    = invoke_llm(formatted)

    if "NO_PDF_CONTEXT" in answer:
        print(f"[Generator] LLM detected irrelevant context → asking user")
        return {"answer": None, "rewritten_query": rewritten_query, "has_pdf_context": False}

    memory.save_context({"input": original_query}, {"answer": answer})
    return {"answer": answer, "rewritten_query": rewritten_query, "has_pdf_context": True}