import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import re

# App config
st.set_page_config(page_title="Qforia 3.1", layout="wide")
st.title("🔍 Qforia: Query Fan-Out (Expert + Industry Data)")

# --- 1. MODEL CATALOG (Verified Nov 2025 IDs) ---
MODEL_CATALOG = {
    "Gemini 3.0 Pro (Preview)": {
        "id": "gemini-3-pro-preview", # Note: No ".0" in the ID
        "icon": "🚀",
        "desc": "Deepest reasoning & 'vibe coding'. Best for complex industry logic."
    },
    "Gemini 2.5 Pro (Stable)": {
        "id": "gemini-2.5-pro", 
        "icon": "⚖️",
        "desc": "High rate limits. The reliable workhorse for production apps."
    },
    "Gemini 2.5 Flash": {
        "id": "gemini-2.5-flash", 
        "icon": "⚡",
        "desc": "Fast & cheap. Good for generating large tables quickly."
    },
    "Gemini 1.5 Pro (Legacy 002)": {
        "id": "gemini-1.5-pro-002", # Use '002' to avoid 404 on generic alias
        "icon": "🛡️",
        "desc": "Previous stable version. Use if 2.5 is unavailable in your region."
    }
}

# --- SIDEBAR ---
st.sidebar.header("Configuration")
gemini_key = st.sidebar.text_input("Gemini API Key", type="password")

st.sidebar.markdown("---")
st.sidebar.subheader("🤖 AI Model Selector")
selected_model_name = st.sidebar.selectbox("Choose Model", options=list(MODEL_CATALOG.keys()), index=0)

current_model = MODEL_CATALOG[selected_model_name]
model_id = current_model["id"]
st.sidebar.info(f"**{current_model['icon']} {selected_model_name}**\n\n{current_model['desc']}")

# Custom Override
if st.sidebar.checkbox("Override Model ID manually?"):
    model_id = st.sidebar.text_input("Enter Custom ID (e.g., gemini-exp-1121)", model_id)

st.sidebar.markdown("---")
user_query = st.sidebar.text_area("Enter your query", "How to implement RAG pipelines for legal discovery?", height=100)
mode = st.sidebar.radio("Search Mode", ["AI Overview (simple)", "AI Mode (complex)"])

if gemini_key:
    genai.configure(api_key=gemini_key)

# --- 2. PROMPT LOGIC (Updated for FAQs & Industry) ---
def QUERY_FANOUT_PROMPT(q, mode):
    # Adjust counts based on mode
    if mode == "AI Overview (simple)":
        min_q = 8
        instr = f"Generate at least {min_q} queries covering basic concepts."
    else:
        min_q = 15
        instr = f"Generate at least {min_q} queries covering deep technical, strategic, and edge-case aspects."

    return (
        f"You are an expert search strategist simulating Google's advanced query fan-out.\n"
        f"User Query: \"{q}\"\nMode: \"{mode}\"\n\n"
        f"**Instructions:**\n"
        f"1. {instr}\n"
        f"2. Ensure diversity (Reformulations, Edge Cases, Comparative, Technical).\n"
        f"3. For EACH query, you must also generate:\n"
        f"   - **Related FAQ:** A specific, high-value question a user would ask next.\n"
        f"   - **Industry Usage:** The specific business sector or use-case this query is most relevant to (e.g., 'Legal Tech', 'Ecommerce Logistics', 'Healthcare Compliance').\n\n"
        f"**Output Format:** Return ONLY a valid JSON object:\n"
        f"{{\n"
        f"  \"generation_details\": {{\n"
        f"    \"target_query_count\": <integer>,\n"
        f"    \"reasoning_for_count\": \"<string>\"\n"
        f"  }},\n"
        f"  \"expanded_queries\": [\n"
        f"    {{\n"
        f"      \"query\": \"<string>\",\n"
        f"      \"type\": \"<string> (e.g. Reformulation, Comparative)\",\n"
        f"      \"reasoning\": \"<string>\",\n"
        f"      \"related_faq\": \"<string>\",\n"
        f"      \"industry_usage\": \"<string>\"\n"
        f"    }}\n"
        f"  ]\n"
        f"}}"
    )

# --- 3. GENERATION FUNCTION ---
def generate_fanout(query, mode, active_model_id):
    if not gemini_key:
        st.error("❌ Missing API Key")
        return None

    prompt = QUERY_FANOUT_PROMPT(query, mode)
    
    try:
        model = genai.GenerativeModel(active_model_id)
        
        # Force JSON output
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.7
            )
        )
        
        # Clean potential markdown formatting
        json_text = response.text.strip()
        if json_text.startswith("```json"): json_text = json_text[7:]
        if json_text.startswith("```"): json_text = json_text[3:]
        if json_text.endswith("```"): json_text = json_text[:-3]
            
        return json.loads(json_text)

    except Exception as e:
        st.error(f"🔴 Error with **{active_model_id}**: {e}")
        st.warning("💡 Try switching to 'Gemini 2.5 Pro (Stable)' if using an Experimental or Preview model.")
        return None

# Initialize State
if 'data' not in st.session_state:
    st.session_state.data = None

# --- 4. UI EXECUTION ---
if st.sidebar.button("Run Analysis 🚀"):
    st.session_state.data = None
    
    if not user_query.strip():
        st.warning("⚠️ Please enter a query.")
    elif not gemini_key:
        st.warning("⚠️ Please enter your API Key.")
    else:
        with st.spinner(f"🤖 analyzing using {selected_model_name}..."):
            result_data = generate_fanout(user_query, mode, model_id)

        if result_data:
            st.session_state.data = result_data
            st.success("✅ Analysis Complete!")

# --- 5. RESULTS TABLE ---
if st.session_state.data:
    data = st.session_state.data
    details = data.get("generation_details", {})
    queries = data.get("expanded_queries", [])

    # Metrics
    st.markdown("### 📊 Strategy Overview")
    c1, c2, c3 = st.columns(3)
    c1.metric("Target Queries", details.get('target_query_count', 'N/A'))
    c2.metric("Actual Generated", len(queries))
    c3.metric("Model", model_id)
    
    st.info(f"**AI Reasoning:** {details.get('reasoning_for_count', 'N/A')}")

    # Main Table
    st.markdown("### 🧩 Expanded Query Matrix")
    df = pd.DataFrame(queries)
    
    if not df.empty:
        # Configure columns for readability
        st.dataframe(
            df,
            use_container_width=True,
            height=600,
            column_config={
                "query": st.column_config.TextColumn("Synthetic Query", width="medium"),
                "related_faq": st.column_config.TextColumn("Related FAQ", width="medium"),
                "industry_usage": st.column_config.TextColumn("Industry Scope", width="small"),
                "type": st.column_config.TextColumn("Type", width="small"),
                "reasoning": st.column_config.TextColumn("Rationale", width="large"),
            },
            # Reorder columns to put the new ones "near" the query
            column_order=["query", "related_faq", "industry_usage", "type", "reasoning"] 
        )

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download CSV", data=csv, file_name=f"qforia_{model_id}_full.csv", mime="text/csv")
