import streamlit as st
import re
import pandas as pd
from urllib.parse import urlencode
from databricks.sdk.core import Config
from databricks import sql

# --- LangChain imports ---
try:
    from langchain_databricks import ChatDatabricks
    from langchain_core.prompts import ChatPromptTemplate
    from langchain.chains import create_retrieval_chain
    from langchain.chains.combine_documents import create_stuff_documents_chain
    from langchain_core.documents import Document
    LANGCHAIN_OK = True
except ImportError:
    LANGCHAIN_OK = False

# --- SarvamAI import ---
try:
    from sarvamai import SarvamAI
    SARVAM_OK = True
except ImportError:
    SARVAM_OK = False

st.set_page_config(page_title="JoSSA Rank & Institute Explorer", layout="wide")

# ==========================================
# CONFIG
# ==========================================
WAREHOUSE_ID = "65ce16d60ab74bcf"
SARVAM_API_KEY = "sk_ewpqphlu_Z5uXWNtC7tsWer8JnRZKACIP"
DASHBOARD_ID = "01f14083a67b1244a44ccd7d35e99447"
ORG_ID = "7474648620124818"
LLM_ENDPOINT = "databricks-gpt-5-4"  # Confirmed existing endpoint

sarvam_client = SarvamAI(api_subscription_key=SARVAM_API_KEY) if SARVAM_OK else None

# ==========================================
# LLM SETUP
# ==========================================

llm = None
if LANGCHAIN_OK:
    try:
        llm = ChatDatabricks(endpoint=LLM_ENDPOINT, max_tokens=512, temperature=0.1)
    except Exception as e:
        st.sidebar.warning(f"LLM init error: {e}")

system_prompt = (
    "You are a highly accurate academic admissions assistant. "
    "Use the following pieces of retrieved context to answer the user's question. "
    "If the answer is not present in the context, explicitly say 'I do not have data for that specific request.' "
    "Do not hallucinate or guess numbers. Keep the answer concise.\n\n"
    "Context:\n{context}"
)

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "{input}"),
])

# ==========================================
# SQL CONNECTION
# ==========================================

@st.cache_resource
def get_sql_connection():
    cfg = Config()
    return sql.connect(
        server_hostname=cfg.host,
        http_path=f"/sql/1.0/warehouses/{WAREHOUSE_ID}",
        credentials_provider=lambda: cfg.authenticate,
    )

# ==========================================
# TRANSLATION
# ==========================================

def translate_text(text, source_lang="en-IN", target_lang="en-IN"):
    if not sarvam_client or source_lang == target_lang or not text:
        return text
    try:
        response = sarvam_client.text.translate(
            input=text,
            source_language_code=source_lang,
            target_language_code=target_lang,
            speaker_gender="Male",
            mode="code-mixed",
            model="mayura:v1",
            numerals_format="international"
        )
        return getattr(response, 'translated_text', str(response))
    except Exception as e:
        st.sidebar.warning(f"Translation issue: {e}")
        return text

# ==========================================
# RETRIEVER (SQL-based)
# ==========================================

def retrieve_documents(query_en):
    t = query_en.upper()
    conditions, params = [], []

    # Rank
    rm = re.search(r'\b(\d{1,5})\b', query_en)
    if rm:
        r = int(rm.group(1))
        conditions.append("closing_rank BETWEEN ? - 500 AND ? + 500")
        params.extend([r, r])

    # Category
    for cat in ["OBC-NCL", "OPEN", "SC", "ST", "EWS", "PWD"]:
        key = "OBC" if cat == "OBC-NCL" else cat
        if key in t:
            conditions.append("seat_category = ?")
            params.append(cat)
            break

    # Year
    ym = re.search(r'\b(20\d{2})\b', query_en)
    if ym:
        conditions.append("year = ?")
        params.append(int(ym.group(1)))

    # Institute
    for pattern, prefix in [
        (r'IIT\s+([A-Za-z\s]+?)(?:\s|$|,|\.|;)', "Indian Institute of Technology "),
        (r'NIT\s+([A-Za-z\s]+?)(?:\s|$|,|\.|;)', "National Institute of Technology "),
        (r'IIIT\s+([A-Za-z\s]+?)(?:\s|$|,|\.|;)', "Indian Institute of Information Technology "),
    ]:
        m = re.search(pattern, query_en, re.IGNORECASE)
        if m:
            conditions.append("LOWER(institute_name) LIKE LOWER(?)")
            params.append(f"%{prefix}{m.group(1).strip()}%")
            break
    else:
        if "IIT" in t:
            conditions.append("LOWER(institute_name) LIKE LOWER(?)")
            params.append("%indian institute of technology%")
        elif "NIT" in t:
            conditions.append("LOWER(institute_name) LIKE LOWER(?)")
            params.append("%national institute of technology%")

    # Program
    prog_map = {
        "CSE": "Computer", "COMPUTER": "Computer", "COMP.": "Computer",
        "ELECTRICAL": "Electrical", "ECE": "Electronics", "ELECTRONICS": "Electronics",
        "MECHANICAL": "Mechanical", "MECH": "Mechanical",
        "CIVIL": "Civil", "CHEMICAL": "Chemical",
        "AEROSPACE": "Aerospace", "METALLURGY": "Metallurgy", "MINING": "Mining",
    }
    for kw, term in prog_map.items():
        if kw in t:
            conditions.append("LOWER(academic_program_name) LIKE LOWER(?)")
            params.append(f"%{term}%")
            break

    sql_query = """
        SELECT institute_name, academic_program_name, degree_type,
               seat_category, opening_rank, closing_rank, year
        FROM hackathon.hack_data.jossa_data_cleaned
    """
    if conditions:
        sql_query += " WHERE " + " AND ".join(conditions)
    sql_query += " ORDER BY closing_rank ASC LIMIT 30"

    conn = get_sql_connection()
    with conn.cursor() as cursor:
        cursor.execute(sql_query, params)
        cols = [desc[0] for desc in cursor.description]
        data = cursor.fetchall()

    df = pd.DataFrame(data, columns=cols)
    docs = []
    for _, row in df.iterrows():
        content = (
            f"Institute: {row['institute_name']}, Program: {row['academic_program_name']} ({row['degree_type']}), "
            f"Category: {row['seat_category']}, Opening: {row['opening_rank']}, Closing: {row['closing_rank']}, Year: {row['year']}"
        )
        docs.append(Document(page_content=content, metadata=row.to_dict()))

    return docs, df

# ==========================================
# RAG CHAIN
# ==========================================

def run_rag(query_en):
    if llm is None or not LANGCHAIN_OK:
        return None, None

    docs, df = retrieve_documents(query_en)

    if not docs:
        return "I do not have data for that specific request. Try a different rank, institute, or program.", df

    # Build the RAG chain dynamically
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(
        retriever=lambda _: docs,  # Return our SQL-retrieved docs
        combine_docs_chain=question_answer_chain
    )

    response = rag_chain.invoke({"input": query_en})
    return response['answer'], df

# ==========================================
# UI
# ==========================================

st.title("JoSSA Rank & Institute Explorer")
st.markdown("Ask anything about JoSSA admissions — in any Indian language!")

lang_map = {
    "English": "en-IN", "Hindi (हिन्दी)": "hi-IN", "Tamil (தமிழ்)": "ta-IN",
    "Telugu (తెలుగు)": "te-IN", "Kannada (ಕನ್ನಡ)": "kn-IN", "Malayalam (മലയാളം)": "ml-IN",
    "Marathi (मराठी)": "mr-IN", "Gujarati (ગુજરાતી)": "gu-IN", "Bengali (বাংলা)": "bn-IN",
    "Punjabi (ਪੰਜਾਬੀ)": "pa-IN",
}

with st.container():
    c1, c2 = st.columns([3, 1])
    with c1:
        query = st.text_input(
            "Your question",
            placeholder="e.g., What was the closing rank for Civil Engineering at IIT Madras for Female candidates in 2021?",
            label_visibility="collapsed"
        )
    with c2:
        selected_lang = st.selectbox("Language", list(lang_map.keys()), label_visibility="collapsed")

    source_lang = lang_map[selected_lang]
    submitted = st.button("🤖 Ask", use_container_width=True)

if submitted and query.strip():
    with st.spinner("Processing..."):
        # Translate to English
        if source_lang != "en-IN" and sarvam_client:
            query_en = translate_text(query.strip(), source_lang, "en-IN")
        else:
            query_en = query.strip()

        # RAG
        answer_en, df = run_rag(query_en)

        # Translate answer back
        if answer_en and source_lang != "en-IN" and sarvam_client:
            answer = translate_text(answer_en, "en-IN", source_lang)
        else:
            answer = answer_en

        # Dashboard embed URL
        rm = re.search(r'\b(\d{1,5})\b', query_en)
        rank = int(rm.group(1)) if rm else None
        base_embed_url = f"https://dbc-a099ec48-2750.cloud.databricks.com/embed/dashboardsv3/{DASHBOARD_ID}"
        dash_params = {"o": ORG_ID}
        if rank:
            dash_params["rank_filter"] = rank
        embed_url = f"{base_embed_url}?{urlencode(dash_params)}"

    if answer:
        st.success("**🤖 Answer:**")
        st.markdown(answer)

    with st.expander("🔍 See the data used"):
        st.markdown(f"**English query:** `{query_en}`")
        if df is not None and not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.warning("No matching data found.")

    if rank:
        st.subheader("Visual Dashboard")
        st.components.v1.html(
            f'<iframe src="{embed_url}" width="100%" height="900" style="border:none;"></iframe>',
            height=900
        )
        st.markdown(f"📊 [Open dashboard in full screen ↗]({embed_url.replace('/embed/', '/')})")

elif submitted:
    st.warning("Please type a question.")

st.divider()
st.markdown("**Example questions:**")
for ex in [
    "What was the closing rank for CSE at IIT Bombay in 2023?",
    "Show me Civil Engineering cutoff at IIT Madras for SC category",
    "What programs can I get with rank 1500 in OPEN category?",
    "Compare NIT Trichy vs NIT Warangal for Mechanical Engineering"
]:
    st.markdown(f"- {ex}")
