import streamlit as st
import google.generativeai as genai
import pandas as pd
import json

# App config
st.set_page_config(page_title="Qforia 2.0", layout="wide")
st.title("🔍 Qforia: Query Fan-Out Simulator (Advanced)")

# --- 1. MODEL CATALOG & CONFIGURATION ---
MODEL_CATALOG = {
    "Gemini 3.0 Pro (Preview)": {
        "id": "gemini-3.0-pro-preview",
        "icon": "🚀",
        "desc": "The latest V3 architecture. Highest reasoning capability. Best for complex fan-outs.",
        "badge": "NEW"
    },
    "Gemini 2.5 Pro": {
        "id": "gemini-2.5-pro",
        "icon": "⚖️",
        "desc": "The current industry standard. Excellent balance of stability, reasoning, and speed.",
        "badge": "STABLE"
    },
    "Gemini 2.5 Flash": {
        "id": "gemini-2.5-flash",
        "icon": "⚡",
        "desc": "Optimized for high-volume, low-latency tasks. Use this for simple, fast queries.",
        "badge": "FAST"
    },
    "Gemini Experimental": {
        "id": "gemini-exp-1114",
        "icon": "🧪",
        "desc": "Snapshot of the absolute newest research. May be unstable but very smart.",
        "badge": "BETA"
    },
    "Gemini 1.5 Pro (Legacy)": {
        "id": "gemini-1.5-pro",
        "icon": "🛡️",
        "desc": "Universal fallback. Use this if you don't have access to V2.5/V3 yet.",
        "badge": "LEGACY"
    }
}

# --- SIDEBAR ---
st.sidebar.header("⚙️ Configuration")

# API Key Section
st.sidebar.markdown("### 🔑 Authentication")
gemini_key = st.sidebar.text_input("Gemini API Key", type="password", help="Enter your Google AI Studio API key")

# Check if API key is provided
if gemini_key:
    genai.configure(api_key=gemini_key)
    st.sidebar.success("✅ API Key configured")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🤖 AI Model Selector")
    
    # Create visual model cards for selection
    selected_model_name = st.sidebar.selectbox(
        "Choose your Model",
        options=list(MODEL_CATALOG.keys()),
        index=0,  # Default to Gemini 3.0
        help="Select the AI model for query generation"
    )
    
    # Get details based on selection
    current_model_config = MODEL_CATALOG[selected_model_name]
    model_id = current_model_config["id"]
    model_icon = current_model_config["icon"]
    model_desc = current_model_config["desc"]
    model_badge = current_model_config.get("badge", "")
    
    # Display Dynamic Info Box with enhanced styling
    badge_colors = {
        "NEW": "🟢",
        "STABLE": "🔵", 
        "FAST": "🟡",
        "BETA": "🟠",
        "LEGACY": "⚪"
    }
    
    badge_emoji = badge_colors.get(model_badge, "")
    
    st.sidebar.info(f"""
**{model_icon} {selected_model_name}** {badge_emoji}  
_{model_desc}_

📋 Model ID: `{model_id}`
""")
    
    # Custom Override (Optional)
    with st.sidebar.expander("🔧 Advanced Options"):
        use_custom = st.checkbox("Use Custom Model ID?", help="Manually enter a specific model identifier")
        if use_custom:
            model_id = st.text_input("Custom Model ID", model_id)
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📝 Query Configuration")
    
    user_query = st.sidebar.text_area(
        "Enter your query", 
        "What's the best electric SUV for driving up mt rainier?", 
        height=120,
        help="Enter the original user query to expand"
    )
    
    mode = st.sidebar.radio(
        "Search Mode", 
        ["AI Overview (simple)", "AI Mode (complex)"],
        help="Simple: 10+ queries | Complex: 20+ queries"
    )
    
    # Show mode explanation
    if mode == "AI Overview (simple)":
        st.sidebar.caption("🎯 Generates 10-15 focused queries")
    else:
        st.sidebar.caption("🎯 Generates 20-30+ comprehensive queries")

else:
    st.sidebar.warning("⚠️ Please enter your API key to continue")
    st.sidebar.markdown("---")
    st.sidebar.info("""
### 🚀 Getting Started

1. Get your API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Paste it in the field above
3. Select your preferred model
4. Enter your query and run!
""")
    st.stop()

# --- 2. PROMPTING LOGIC ---
def QUERY_FANOUT_PROMPT(q, mode):
    min_queries_simple = 10
    min_queries_complex = 20

    if mode == "AI Overview (simple)":
        num_queries_instruction = (
            f"First, analyze the user's query: \"{q}\". Based on its complexity and the '{mode}' mode, "
            f"**you must decide on an optimal number of queries to generate.** "
            f"This number must be **at least {min_queries_simple}**. "
            f"For straightforward queries, aim for {min_queries_simple}-15 queries."
        )
    else:  # AI Mode (complex)
        num_queries_instruction = (
            f"First, analyze the user's query: \"{q}\". Based on its complexity and the '{mode}' mode, "
            f"**you must decide on an optimal number of queries to generate.** "
            f"This number must be **at least {min_queries_complex}**. "
            f"For complex queries, aim for {min_queries_complex}-30+ queries covering multiple angles."
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
        st.error(f"{str(e)}")
        
        # Provide helpful suggestions
        if "404" in str(e) or "not found" in str(e).lower():
            st.warning("💡 This model may not be available with your API key. Try:")
            st.markdown("- **Gemini 1.5 Pro (Legacy)** - Most widely available")
            st.markdown("- **Gemini 2.5 Pro** - If you have access")
        
        return None

# Initialize session state
if 'data' not in st.session_state:
    st.session_state.data = None

# --- 4. UI ACTIONS ---
st.sidebar.markdown("---")

run_button_disabled = not user_query.strip()

if st.sidebar.button("Run Fan-Out 🚀", type="primary", disabled=run_button_disabled, use_container_width=True):
    st.session_state.data = None
    
    with st.spinner(f"🤖 Generating using **{selected_model_name}** (`{model_id}`)..."):
        result_data = generate_fanout(user_query, mode, model_id)

    if result_data:
        st.session_state.data = result_data
        st.balloons()
        st.success(f"✅ Successfully generated queries using **{selected_model_name}**!")

# --- 5. RESULTS DISPLAY ---
if st.session_state.data:
    data = st.session_state.data
    details = data.get("generation_details", {})
    queries = data.get("expanded_queries", [])

    target = details.get('target_query_count', 'N/A')
    reasoning = details.get('reasoning_for_count', 'N/A')
    actual = len(queries)

    # Header with model info
    st.markdown(f"## 📊 Results - Generated by {model_icon} **{selected_model_name}**")
    
    # Reasoning Block
    st.markdown("### 🧠 Strategy & Reasoning")
    st.info(f"**Model Strategy:** {reasoning}")

    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🎯 Target Count", target)
    col2.metric("✅ Generated", actual)
    col3.metric("🤖 Model", selected_model_name.split()[0])
    
    # Calculate match percentage
    if isinstance(target, int) and target > 0:
        match_pct = min(100, int((actual / target) * 100))
        col4.metric("📈 Accuracy", f"{match_pct}%")
    else:
        col4.metric("📈 Accuracy", "N/A")

    # Data Table
    st.markdown("### 🔍 Generated Queries")
    df = pd.DataFrame(queries)
    
    if not df.empty:
        # Add query type statistics
        if 'type' in df.columns:
            st.markdown("#### Query Type Distribution")
            type_counts = df['type'].value_counts()
            cols = st.columns(len(type_counts))
            for idx, (query_type, count) in enumerate(type_counts.items()):
                cols[idx].metric(query_type.title(), count)
        
        st.markdown("#### Full Query List")
        st.dataframe(
            df, 
            use_container_width=True, 
            column_config={
                "query": st.column_config.TextColumn("Synthetic Query", width="medium"),
                "type": st.column_config.TextColumn("Type", width="small"),
                "user_intent": st.column_config.TextColumn("Intent", width="medium"),
                "reasoning": st.column_config.TextColumn("Rationale", width="large"),
            },
            hide_index=True
        )

        # Download section
        st.markdown("### 📥 Export Options")
        col1, col2 = st.columns(2)
        
        with col1:
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Download CSV", 
                data=csv, 
                file_name=f"qforia_{model_id}_{mode.replace(' ', '_')}.csv", 
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            json_str = json.dumps(data, indent=2)
            st.download_button(
                "📥 Download JSON",
                data=json_str,
                file_name=f"qforia_{model_id}_{mode.replace(' ', '_')}.json",
                mime="application/json",
                use_container_width=True
            )
    else:
        st.warning("⚠️ JSON was parsed, but 'expanded_queries' list was empty.")

else:
    # Welcome screen when no results
    st.markdown("""
    ## 👋 Welcome to Qforia 2.0!
    
    This tool simulates Google's AI Mode query fan-out process, expanding a single user query into multiple synthetic search queries.
    
    ### 🎯 How it works:
    1. **Enter your API key** in the sidebar
    2. **Select an AI model** from the catalog (Gemini V3 recommended!)
    3. **Input your query** to expand
    4. **Choose a mode** (Simple or Complex)
    5. **Click "Run Fan-Out"** and watch the magic happen!
    
    ### 🚀 Featured Models:
    """)
    
    cols = st.columns(3)
    for idx, (name, config) in enumerate(list(MODEL_CATALOG.items())[:3]):
        with cols[idx % 3]:
            st.markdown(f"""
            ##### {config['icon']} {name}
            {config['desc']}
            """)
