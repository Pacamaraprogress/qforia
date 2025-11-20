import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import re

# App config
st.set_page_config(page_title="Qforia 3.0", layout="wide")
st.title("🔍 Qforia: Query Fan-Out Simulator (Expert Mode)")

# --- 1. MODEL CATALOG ---
MODEL_CATALOG = {
    "Gemini 2.5 Pro": {
        "id": "gemini-2.0-pro-exp-02-05", # Best current stable-ish preview or use 1.5-pro if preferred
        "icon": "⚖️",
        "desc": "The best balance of complex reasoning and stability."
    },
    "Gemini 2.5 Flash": {
        "id": "gemini-2.0-flash-thinking-exp-01-21", 
        "icon": "⚡",
        "desc": "Optimized for speed and thinking process."
    },
    "Gemini 1.5 Pro (Legacy)": {
        "id": "gemini-1.5-pro",
        "icon": "🛡️",
        "desc": "Universal fallback. Reliable and widely available."
    },
    "Gemini 3.0 (Preview/Private)": {
        "id": "gemini-3.0-pro-preview", 
        "icon": "🚀",
        "desc": "Access to V3 architecture (requires specific allowlist)."
    }
}

# --- SIDEBAR ---
st.sidebar.header("Configuration")
gemini_key = st.sidebar.text_input("Gemini API Key", type="password")

st.sidebar.markdown("---")
st.sidebar.subheader("🤖 Model Selection")
selected_model_name = st.sidebar.selectbox("Choose Model", options=list(MODEL_CATALOG.keys()), index=0)

# Get details
current_model = MODEL_CATALOG[selected_model_name]
model_id = current_model["id"]
st.sidebar.info(f"**{current_model['icon']} {selected_model_name}**\n\n{current_model['desc']}")

# Custom Override
if st.sidebar.checkbox("Override Model ID"):
    model_id = st.sidebar.text_input("Custom ID", model_id)

st.sidebar.markdown("---")
user_query = st.sidebar.text_area("Enter your query", "What's the best electric SUV for driving up mt rainier?", height=120)
mode = st.sidebar.radio("Search Mode", ["AI Overview (simple)", "AI Mode (complex)"])

if gemini_key:
    genai.configure(api_key=gemini_key)

# --- 2. RESTORED ORIGINAL PROMPT LOGIC ---
def QUERY_FANOUT_PROMPT(q, mode):
    min_queries_simple = 10
    min_queries_complex = 20

    if mode == "AI Overview (simple)":
        num_queries_instruction = (
            f"First, analyze the user's query: \"{q}\". Based on its complexity and the '{mode}' mode, "
            f"**you must decide on an optimal number of queries to generate.** "
            f"This number must be **at least {min_queries_simple}**. "
            f"For a straightforward query, generating around {min_queries_simple}-{min_queries_simple + 2} queries might be sufficient. "
            f"If the query has a few distinct aspects, aim for {min_queries_simple + 3}-{min_queries_simple + 5}. "
            f"Provide a brief reasoning for why you chose this specific number."
        )
    else:  # AI Mode (complex)
        num_queries_instruction = (
            f"First, analyze the user's query: \"{q}\". Based on its complexity and the '{mode}' mode, "
            f"**you must decide on an optimal number of queries to generate.** "
            f"This number must be **at least {min_queries_complex}**. "
            f"For multifaceted queries, generate potentially {min_queries_complex + 5}-{min_queries_complex + 10} queries. "
            f"Provide a brief reasoning for why you chose this specific number."
        )

    # Restoring the FULL detailed instructions
    return (
        f"You are simulating Google's AI Mode query fan-out process for generative search systems.\n"
        f"The user's original query is: \"{q}\". The selected mode is: \"{mode}\".\n\n"
        f"**Task 1: Planning**\n"
        f"{num_queries_instruction}\n\n"
        f"**Task 2: Generation**\n"
        f"Once you have decided on the number, generate exactly that many unique synthetic queries.\n"
        f"Each of the following query transformation types MUST be represented at least once if the count allows:\n"
        f"1. Reformulations\n2. Related Queries\n3. Implicit Queries\n4. Comparative Queries\n5. Entity Expansions\n6. Personalized Queries\n\n"
        f"The 'reasoning' field for each *individual query* should explain why that specific query was generated.\n"
        f"Do NOT include queries dependent on real-time user history or geolocation.\n\n"
        f"**Return ONLY valid JSON following this format:**\n"
        f"{{\n"
        f"  \"generation_details\": {{\n"
        f"    \"target_query_count\": <integer>,\n"
        f"    \"reasoning_for_count\": \"<string>\"\n"
        f"  }},\n"
        f"  \"expanded_queries\": [\n"
        f"    {{\n"
        f"      \"query\": \"...\",\n"
        f"      \"type\": \"...\",\n"
        f"      \"user_intent\": \"...\",\n"
        f"      \"reasoning\": \"...\"\n"
        f"    }}\n"
        f"  ]\n"
        f"}}"
    )

# --- 3. ROBUST GENERATION FUNCTION ---
def generate_fanout(query, mode, active_model_id):
    if not gemini_key:
        st.error("❌ Missing API Key")
        return None

    prompt = QUERY_FANOUT_PROMPT(query, mode)
    
    try:
        model = genai.GenerativeModel(active_model_id)
        
        # Use response_mime_type for cleaner JSON, but keep text cleaning just in case
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.7
            )
        )
        
        json_text = response.text.strip()
        
        # Safety: Clean markdown fences if the model adds them despite mime_type
        if json_text.startswith("```json"):
            json_text = json_text[7:]
        if json_text.startswith("```"):
            json_text = json_text[3:]
        if json_text.endswith("```"):
            json_text = json_text[:-3]
            
        data = json.loads(json_text)
        return data

    except Exception as e:
        st.error(f"🔴 Error with model **{active_model_id}**: {e}")
        return None

# Initialize session state
if 'data' not in st.session_state:
    st.session_state.data = None

# --- 4. EXECUTION & DISPLAY ---
if st.sidebar.button("Run Fan-Out 🚀"):
    st.session_state.data = None
    
    if not user_query.strip():
        st.warning("⚠️ Please enter a query.")
    elif not gemini_key:
        st.warning("⚠️ Please enter your API Key.")
    else:
        with st.spinner(f"🤖 Generating using {selected_model_name}..."):
            result_data = generate_fanout(user_query, mode, model_id)

        if result_data:
            st.session_state.data = result_data
            st.success("✅ Query fan-out complete!")

# --- 5. RESULTS (With Original Dataframe Logic) ---
if st.session_state.data:
    data = st.session_state.data
    details = data.get("generation_details", {})
    queries = data.get("expanded_queries", [])

    target = details.get('target_query_count', 'N/A')
    reasoning = details.get('reasoning_for_count', 'Not provided.')
    actual = len(queries)

    # Header Stats
    st.markdown("---")
    st.subheader("🧠 Model Strategy")
    st.info(f"**Reasoning:** {reasoning}")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Target Count", target)
    c2.metric("Actual Generated", actual)
    c3.metric("Model ID", model_id)

    if isinstance(target, int) and target != actual:
        st.warning(f"⚠️ Model aimed for {target} but produced {actual}.")

    # DataFrame
    st.markdown("### 🔍 Generated Queries")
    df = pd.DataFrame(queries)
    
    if not df.empty:
        # Restored your specific height calculation
        height = (min(len(df), 20) + 1) * 35 + 3
        
        st.dataframe(
            df, 
            use_container_width=True, 
            height=height,
            column_config={
                "query": st.column_config.TextColumn("Synthetic Query", width="medium"),
                "type": st.column_config.TextColumn("Type", width="small"),
                "reasoning": st.column_config.TextColumn("Rationale", width="large"),
            }
        )

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download CSV", data=csv, file_name=f"qforia_{model_id}.csv", mime="text/csv")
