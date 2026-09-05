import streamlit as st
import yaml
import os
from registry import PromptRegistry
from evaluator import run_evaluation

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Prompt Registry Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- MODERN STYLING (CSS) ---
st.markdown("""
<style>
    /* Metric Cards */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 700 !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
        color: #8b949e !important;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Subtle status badge */
    .badge-active {
        display: inline-block;
        padding: 4px 10px;
        font-size: 0.8rem;
        font-weight: 600;
        border-radius: 12px;
        background-color: rgba(16, 185, 129, 0.15);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .badge-author {
        display: inline-block;
        padding: 4px 10px;
        font-size: 0.8rem;
        font-weight: 500;
        border-radius: 12px;
        background-color: rgba(107, 114, 128, 0.15);
        color: #9ca3af;
        border: 1px solid rgba(107, 114, 128, 0.3);
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def load_registry():
    return PromptRegistry()

registry = load_registry()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### 🗂️ Prompt Catalog")
    prompt_keys = list(registry.config.keys())
    prompt_name = st.selectbox("Select Prompt to Inspect:", prompt_keys)
    
    st.markdown("---")
    st.markdown("#### 💡 Quick Guide")
    st.caption("1. **Edit** prompt instructions on the canvas.\n"
               "2. **Save** creates an auto-incremented new version.\n"
               "3. **Deploy** switches live traffic to that version.\n"
               "4. **Run Evals** tests quality and checks token costs.")

# --- LOAD DATA ---
meta = registry.get_metadata(prompt_name)
active_version = meta.get('active_version', 'unknown')
author = meta.get('metadata', {}).get('author', 'Unknown')

file_path = os.path.join(registry.prompts_dir, prompt_name, f"{active_version}.yaml")
with open(file_path, 'r') as f:
    current_data = yaml.safe_load(f)
current_template = current_data.get('template', '')

# --- HEADER SECTION ---
header_col, info_col = st.columns([2, 1])
with header_col:
    st.title("Prompt Registry Pro")
    st.caption(f"Managing prompt configurations for **`{prompt_name}`**")

with info_col:
    st.markdown(
        f"""
        <div style="text-align: right; padding-top: 15px;">
            <span class="badge-active">● Active: {active_version}</span>
            <span class="badge-author">Author: {author}</span>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("")

# --- WORKSPACE: EDITOR & VERSION CONTROL ---
col_editor, col_deploy = st.columns([1.5, 1], gap="medium")

# FEATURE 1: EDIT & SAVE UI
with col_editor:
    with st.container(border=True):
        st.markdown("#### ✏️ Template Editor")
        st.caption("Refine and test variations of your system instructions.")
        
        new_template = st.text_area(
            "Prompt Template",
            value=current_template,
            height=260,
            label_visibility="collapsed"
        )
        
        if st.button("💾 Save as New Version", use_container_width=True, type="secondary"):
            versions = registry.get_versions(prompt_name)
            nums = [int(v.replace('v', '')) for v in versions if v.startswith('v') and v[1:].isdigit()]
            next_num = max(nums) + 1 if nums else 1
            new_version_name = f"v{next_num}"
            
            new_file_path = os.path.join(registry.prompts_dir, prompt_name, f"{new_version_name}.yaml")
            with open(new_file_path, 'w') as f:
                yaml.dump({"template": new_template, "metadata": {"author": "you", "created_at": "just now"}}, f)
                
            st.success(f"Successfully committed and saved as **{new_version_name}**!")
            st.balloons()

# FEATURE 2: DEPLOY BUTTON
with col_deploy:
    with st.container(border=True):
        st.markdown("#### 🚀 Release Management")
        st.caption("Select and route production traffic to a specific version.")
        
        versions = registry.get_versions(prompt_name)
        version_to_deploy = st.selectbox(
            "Target Version:",
            versions,
            index=versions.index(active_version) if active_version in versions else 0
        )
        
        st.markdown("<div style='height: 125px;'></div>", unsafe_allow_html=True) # visual spacer
        
        if st.button("⚡ Deploy to Active", use_container_width=True, type="primary"):
            if version_to_deploy != active_version:
                registry.change_version(prompt_name, version_to_deploy)
                st.success(f"Deployed **{version_to_deploy}** to active!")
                st.rerun()
            else:
                st.warning("This version is already active.")

st.markdown("")

# --- FEATURE 3: METRICS & EVALS ---
with st.container(border=True):
    header_eval, btn_eval = st.columns([3, 1])
    with header_eval:
        st.markdown("#### 🧪 Benchmark & Quality Evaluations")
        st.caption("Validate your current prompt draft against test cases for score, latency, and cost.")
    with btn_eval:
        run_eval_btn = st.button("▶ Run Evaluations", use_container_width=True, type="primary")

    if run_eval_btn:
        with st.spinner("Executing benchmark suite with Gemini..."):
            results, avg_score, metrics = run_evaluation(new_template, prompt_name)
            
        if isinstance(results, list) and len(results) > 0 and "error" in results[0]:
            st.error(results[0]["error"])
        else:
            st.markdown("---")
            
            # Display Metrics Dashboard
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Avg Quality Score", f"{avg_score:.1f} / 10")
            m2.metric("Total Latency", f"{metrics['total_latency']}s")
            m3.metric("Tokens Consumed", f"{metrics['total_input_tokens'] + metrics['total_output_tokens']:,}")
            m4.metric("Estimated Cost", f"${metrics['estimated_cost']}")
            
            st.markdown("##### Detailed Test Results")
            for i, res in enumerate(results):
                score = res.get('score', 0)
                status_icon = "🟢" if score >= 8 else ("🟡" if score >= 5 else "🔴")
                
                with st.expander(f"{status_icon} Test Case #{i+1} — Score: {score}/10"):
                    st.markdown("**Input**")
                    st.info(res['input'])
                    st.markdown("**Model Output**")
                    st.write(res['output'])