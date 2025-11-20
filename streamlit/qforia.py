import streamlit as st
import google.generativeai as genai
import pandas as pd
import json

# App config
st.set_page_config(page_title="Qforia 2.0", layout="wide")
st.title("🔍 Qforia: Query Fan-Out Simulator (Advanced)")

# --- 1. MODEL CATALOG & CONFIGURATION ---
# This dictionary maps the friendly name to the API ID and a helpful description.
MODEL_CATALOG = {
    "Gemini 3.0 Pro (Preview)": {
        "id": "gemini-3.0-pro-preview",
        "icon": "🚀",
        "desc": "The latest V3 architecture. Highest reasoning capability. Best for complex fan-outs."
    },
    "Gemini 2.5 Pro": {
        "id": "gemini-2.5-pro",
        "icon": "⚖️",
        "desc": "The current industry standard. Excellent balance of stability, reasoning, and speed."
    },
    "Gemini 2.5 Flash": {
        "id": "gemini-2.5-flash",
        "icon": "⚡",
        "desc": "Optimized for high-volume, low-latency tasks. Use this for simple, fast queries."
    },
    "Gemini Experimental": {
        "id": "gemini-exp-1114",
        "icon": "🧪",
        "desc": "Snapshot of the absolute newest research. May be unstable but very smart."
    },
    "Gemini 1.5 Pro (Legacy)": {
        "id": "gemini-1.5-pro",
        "icon": "🛡️",
        "desc": "Universal fallback. Use this if you don't have access to V2.5/V3 yet."
    }
}

# --- SIDEBAR ---
st.sidebar.header("Configuration")
gemini_key = st.sidebar.text_input("Gemini API Key", type="password")

st.sidebar.markdown("---")
st.sidebar.subheader("🤖 AI Model Selector")

# Dropdown for Model Selection
selected_model_name = st.sidebar.selectbox(
    "Choose your Model",
    options=list(MODEL_CATALOG.keys()),
    index=0 # Default to Gemini 3.0
)

# Get details based on selection
current_model_config = MODEL_CATALOG[selected_model_name]
model_id = current_model_config["id"]
model_icon = current_model_config["icon"]
model_desc = current_model_config["desc"]

# Display Dynamic Info Box in Sidebar
st.sidebar.info(f"**{model_icon} {selected_model_name}**\n\n{model_desc}")

# Custom Override (Optional)
use_custom = st.sidebar.checkbox("Use Custom Model ID manually?")
if use_custom:
    model_id = st.sidebar.text_input("Enter Custom Model ID", model_id)

st.sidebar.markdown("---")
user_query = st.sidebar.text_area("Enter your query", "What's the best electric SUV for driving up mt rainier?", height=120)
mode = st.sidebar.radio("Search Mode", ["AI Overview (simple)", "AI Mode (complex)"])

# Configure Gemini
if gemini_key:
    genai.configure(api_key=gemini_key)

# --- 2. PROMPTING LOGIC ---
def QUERY_FANOUT_PROMPT(q, mode):
    min_queries_simple = 10
    min_queries_complex = 20

    if mode == "AI Overview (simple)":
        num_queries_instruction = (
            f"First, analyze the user's query: \"{q}\". Based on its complexity and the '{mode}' mode, "
            f"**you must decide on an optimal number of queries to generate.** "
            f"This number must be **at least {min_queries_simple}**."
        )
    else:  # AI Mode (complex)
        num_queries_instruction = (
            f"First, analyze the user's query: \"{q}\". Based on its complexity and the '{mode}' mode, "
            f"**you must decide on an optimal number of queries to generate.** "
            f"This number must be **at least {min_queries_complex}**."
        )

    return (
        f"You are simulating Google's AI Mode query fan-out process.\n"
        f"User Query: \"{q}\"\nMode: \"{mode}\"\n\n"
        f"**Task:**\n"
        f"1. Determine the target number of queries based on: {num_queries_instruction}\n"
        f"2. Generate exactly that many unique synthetic queries.\n"
        f"3. Ensure diversity: Reformulations, Related, Implicit, Comparative, Entity Expansions, Personalized.\n\n"
        f"**Return JSON Only:**\n"
        f"The response must be a valid JSON object with this structure:\n"
        f"{{\n"
        f"  \"generation_details\": {{\n"
        f"    \"target_query_count\": <integer>,\n"
        f"    \"reasoning_for_count\": \"<string>\"\n"
        f"  }},\n"
        f"  \"expanded_queries\": [\n"
        f"    {{\n"
        f"      \"query\": \"<string>\",\n"
        f"      \"type\": \"<string>\",\n"
        f"      \"user_intent\": \"<string>\",\n"
        f"      \"reasoning\": \"<string>\"\n"
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
        # Initialize Model
        model = genai.GenerativeModel(active_model_id)
        
        # Generate with JSON Enforcement
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.7
            )
        )
        
        # Parse Response
        data = json.loads(response.text)
        return data

    except Exception as e:
        st.error(f"🔴 Error with model **{active_model_id}**:")
        st.error(f"{e}")
        st.warning("💡 If this is a 404 or Resource Error, try selecting 'Gemini 1.5 Pro (Legacy)' or 'Gemini 2.5 Pro' from the sidebar.")
        return None

# Initialize session state
if 'data' not in st.session_state:
    st.session_state.data = None

# --- 4. UI ACTIONS ---
if st.sidebar.button("Run Fan-Out 🚀"):
    st.session_state.data = None
    
    if not user_query.strip():
        st.warning("⚠️ Please enter a query.")
    elif not gemini_key:
        st.warning("⚠️ Please enter your API Key.")
    else:
        with st.spinner(f"🤖 Generating using {selected_model_name} ({model_id})..."):
            result_data = generate_fanout(user_query, mode, model_id)

        if result_data:
            st.session_state.data = result_data
            st.success("✅ Query fan-out complete!")

# --- 5. RESULTS DISPLAY ---
if st.session_state.data:
    data = st.session_state.data
    details = data.get("generation_details", {})
    queries = data.get("expanded_queries", [])

    target = details.get('target_query_count', 'N/A')
    reasoning = details.get('reasoning_for_count', 'N/A')
    actual = len(queries)

    # Reasoning Block
    st.markdown("### 🧠 Strategy & Reasoning")
    st.info(f"**Model:** {selected_model_name}\n\n**Strategy:** {reasoning}")

    col1, col2, col3 = st.columns(3)
    col1.metric("Target Count", target)
    col2.metric("Actual Generated", actual)
    col3.metric("Model Used", model_id)

    # Data Table
    st.markdown("### 🔍 Generated Queries")
    df = pd.DataFrame(queries)
    
    if not df.empty:
        st.dataframe(
            df, 
            use_container_width=True, 
            column_config={
                "query": st.column_config.TextColumn("Synthetic Query", width="medium"),
                "type": st.column_config.TextColumn("Type", width="small"),
                "reasoning": st.column_config.TextColumn("Rationale", width="large"),
            }
        )

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download CSV", data=csv, file_name=f"qforia_{model_id}.csv", mime="text/csv")
    else:
        st.warning("JSON was parsed, but 'expanded_queries' list was empty.")
