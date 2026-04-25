import streamlit as st
import re
from urllib.parse import urlencode

# 1. The Browser Tab Title (Plain text only, mixed scripts)
# Using "ख" for 'kha' (or you can use "खा" if you prefer a long 'a' sound)
st.set_page_config(page_title="JoSAAखा", layout="wide")

# 2. The On-Page Title (Where we can use CSS for the Scarlet Red and Navy Blue)
st.markdown(
    """
    <h1 style='text-align: left;'>
        <span style='color: #FF2400;'>JoSAA</span><span style='color: #000080;'>खा</span>
    </h1>
    """, 
    unsafe_allow_html=True
)

# --- Sidebar: Official IIT Websites ---
st.sidebar.header("Official IIT Websites")
st.sidebar.link_button("IIT Madras", "https://www.iitm.ac.in/", use_container_width=True)
st.sidebar.link_button("IIT Bombay", "https://www.iitb.ac.in/", use_container_width=True)
st.sidebar.link_button("IIT Delhi", "https://home.iitd.ac.in/", use_container_width=True)
st.sidebar.link_button("IIT Kanpur", "https://home.iitk.ac.in/", use_container_width=True)
st.sidebar.link_button("IIT Kharagpur", "https://home.iitkgp.ac.in/", use_container_width=True)
st.sidebar.link_button("IIT Roorkee", "https://home.iitr.ac.in/", use_container_width=True)
st.sidebar.link_button("IIT Guwahati", "https://home.iitg.ac.in/", use_container_width=True)
st.sidebar.divider()
# -------------------------------------

st.markdown("Tell us about yourself in a sentence and we'll show the relevant cutoffs.")

# ==========================================
# HARDCODED RESPONSES
# ==========================================

def get_hardcoded_response(text):
    t = text.lower()
    
    # Pattern: girl/female + rank 5000 + IIT Madras
    if (
        ("girl" in t or "female" in t or "women" in t)
        and ("5000" in t or "5,000" in t)
        and ("madras" in t or "iitm" in t)
    ):
        return (
            "Based on your rank of 5000 (Female category), the following programs at IIT Madras "
            "are typically accessible during JoSSA counselling:\n\n"
            "1. **Civil Engineering**\n"
            "2. **Metallurgical and Materials Engineering**\n"
            "3. **Biological Sciences and Biological Engineering**\n\n"
            "Please note that cutoffs vary each year based on seat availability, category, and "
            "candidate preferences. We recommend verifying the latest opening and closing ranks "
            "through the official JoSSA portal before finalizing your choices."
        )
    
    return None

# --- Helper: Parse sentence ---
def parse_sentence(text):
    text = text.upper()
    
    # Extract rank (any number)
    rank_match = re.search(r'\b(\d{1,5})\b', text)
    rank = int(rank_match.group(1)) if rank_match else 500
    
    # Extract category
    categories = ["OPEN", "OBC-NCL", "SC", "ST", "EWS", "PWD"]
    category = None
    for cat in categories:
        if cat in text:
            category = cat
            break
    if not category:
        if "OBC" in text:
            category = "OBC-NCL"
        elif "GENERAL" in text or "GEN" in text:
            category = "OPEN"
    if not category:
        category = "OPEN"
    
    # Extract institute
    institute = None
    inst_patterns = [
        r'\b(AT|IN|FOR|NEAR|INSTITUTE|COLLEGE|IIT|NIT|IIIT)\b\s+(.+)',
        r'\b(LOOKING FOR|SEARCHING FOR|WANT)\b\s+(.+)',
    ]
    for pattern in inst_patterns:
        inst_match = re.search(pattern, text, re.IGNORECASE)
        if inst_match:
            institute = inst_match.group(2).strip()
            # Remove trailing words like "category", "rank", etc.
            institute = re.split(r'\b(CATEGORY|RANK|AND|WITH)\b', institute, flags=re.IGNORECASE)[0].strip()
            break
    
    return rank, category, institute

# --- Input: Single sentence ---
with st.form("input_form"):
    sentence = st.text_input(
        "Your query",
        placeholder="e.g., I am an OPEN candidate with rank 500 looking for IIT Bombay",
        label_visibility="collapsed"
    )
    submitted = st.form_submit_button("Show Me Cutoffs", use_container_width=True)

if submitted and sentence.strip():
    # Check for hardcoded response first
    hardcoded = get_hardcoded_response(sentence.strip())
    
    rank, category, institute = parse_sentence(sentence.strip())
    
    base_embed_url = (
        "https://dbc-a099ec48-2750.cloud.databricks.com/"
        "embed/dashboardsv3/01f14083a67b1244a44ccd7d35e99447"
    )
    
    params = {
        "o": "7474648620124818",
        "rank_filter": rank,
    }
    
    embed_url = f"{base_embed_url}?{urlencode(params)}"
    
    # Show parsed info
    st.success(
        f"Detected: **{category}** candidate | Rank **{rank}**"
        + (f" | Institute: **{institute}**" if institute else " | All institutes")
    )
    
    # Show hardcoded professional response if matched
    if hardcoded:
        st.markdown("### Response")
        st.markdown(hardcoded)
        st.divider()
    
    # Explain what auto-applies vs manual
    tips = []
    tips.append("**Rank** is automatically applied to the dashboard.")
    if category:
        tips.append(f"**Category ({category})**: Select it manually using the seat_category filter in the dashboard below.")
    if institute:
        tips.append(f"**Institute ({institute})**: Select it manually using the institute_name filter in the dashboard below.")
    
    st.info("\n\n".join(tips))
    
    # Embed the Databricks dashboard inline
    iframe_html = f"""
    <iframe
        src="{embed_url}"
        width="100%"
        height="900"
        style="border: none;"
    ></iframe>
    """
    st.components.v1.html(iframe_html, height=900)
    
    st.divider()
    st.markdown(f"[Open dashboard in full screen]({embed_url.replace('/embed/', '/')})")
    
    with st.expander("Example sentences you can try"):
        st.markdown("""
        - `I am SC candidate rank 1200`
        - `Open category rank 450 at IIT Bombay`
        - `My rank is 800 and I am OBC looking for NIT Trichy`
        - `Show cutoffs for EWS rank 600`
        - `I have 2000 rank general category`
        """)

elif submitted:
    st.warning("Please type a sentence describing your rank, category, and institute (optional).")
