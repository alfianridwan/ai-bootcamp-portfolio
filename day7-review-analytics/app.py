import streamlit as st
from datetime import datetime
import config
from database.db_manager import init_db, save_summary, get_summaries_by_category, get_summary_by_id
from services.gemini_service import analyze_review_sentiment

init_db()

st.set_page_config(page_title="Review Analyst Pro", page_icon="📈", layout="wide")

if "view_mode" not in st.session_state:
    st.session_state.view_mode = "new_analysis"
if "selected_summary_id" not in st.session_state:
    st.session_state.selected_summary_id = None

with st.sidebar:
    st.title("📁 Navigation & History")

    if st.button("➕ Analyze New Reviews", use_container_width=True, type="primary"):
        st.session_state.view_mode = "new_analysis"
        st.session_state.selected_summary_id = None
        st.rerun()

    st.divider()
    st.subheader("📜 Filter Past Summaries")

    categories = {
        "🟢 Good (8-10)": "Good",
        "🟡 Average (4-7)": "Average",
        "🔴 Bad (0-3)": "Bad"
    }

    for label, db_category in categories.items():
        with st.expander(label):
            records = get_summaries_by_category(db_category)
            if not records:
                st.caption("No historical records found.")
            for rec_id, filename, timestamp in records:
                time_str = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f").strftime("%b %d, %H:%M")
                btn_label = f"📄 {filename} ({time_str})"

                if st.button(btn_label, key=f"rec_{rec_id}", use_container_width=True):
                    st.session_state.view_mode = "view_past"
                    st.session_state.selected_summary_id = rec_id
                    st.rerun()

# MODE 1: View Past Record History
if st.session_state.view_mode == "view_past" and st.session_state.selected_summary_id is not None:
    record = get_summary_by_id(st.session_state.selected_summary_id)
    if record:
        filename, summary, rating, category, created_at = record

        st.title(f"📜 Archived Summary: {filename}")
        st.caption(f"Analyzed on: {created_at} | Category Tier: **{category}**")
        st.markdown("---")

        col1, col2 = st.columns([1, 4])
        with col1:
            st.metric(label="Overall Rating", value=f"{rating} / 10")
        with col2:
            if category == "Good":
                st.success("🎯 Category Score: This batch reflects overall positive customer sentiment.")
            elif category == "Average":
                st.warning("⚖️ Category Score: This batch reflects mixed or average customer sentiment.")
            else:
                st.error("⚠️ Category Score: This batch reflects critical or negative customer sentiment.")

        st.markdown("### 📋 Core Synthesis Summary")
        st.markdown(summary)
    else:
        st.error("Could not retrieve the specified historical record.")

# MODE 2: Run Fresh Analysis Uploader
else:
    st.title("📊 Customer Review Analytics Engine")
    st.caption(f"Cloud Architecture Backend: **{config.MODEL_NAME}**")
    st.markdown("---")

    st.markdown("""
    ### 📥 Processing Pipeline
    Upload a text file containing compilation feedback. The platform will evaluate metrics,
    generate structured takeaways, and catalog the entry into the database repository automatically.
    """)

    upload_tab, manual_tab = st.tabs(["📁 Upload .txt File", "✍️ Type Manually"])

    review_text = None
    source_name = None

    with upload_tab:
        uploaded_file = st.file_uploader("Drop customer feedback .txt file here", type=["txt"])
        if uploaded_file is not None:
            try:
                review_text = uploaded_file.read().decode("utf-8")
                source_name = uploaded_file.name
                with st.expander("📄 Review File Context Preview", expanded=False):
                    st.text(review_text)
            except Exception as file_err:
                st.error(f"❌ Structural Read Error: {file_err}")

    with manual_tab:
        manual_text = st.text_area("Paste or type customer feedback here", height=200)
        if manual_text.strip():
            review_text = manual_text
            source_name = f"manual-entry-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    if review_text:
        st.markdown("---")

        if st.button("🚀 Execute Sentiment Analysis", use_container_width=True):
            with st.spinner("Gemini is interpreting text blocks and mapping score parameters..."):
                try:
                    clean_summary, rating, category = analyze_review_sentiment(review_text)
                    save_summary(source_name, clean_summary, rating, category)

                    st.success(f"✅ Processing Finalized! Saved under **{category}** classification category.")

                    m_col, d_col = st.columns([1, 4])
                    m_col.metric(label="Calculated Score", value=f"{rating} / 10")
                    d_col.info(f"Database Router Pipeline assigned this to the **{category}** segment container.")

                    st.markdown("### 📋 AI Generated Synthesis Review")
                    st.markdown(clean_summary)

                except Exception as api_err:
                    st.error(f"❌ Cloud API Request Interrupted: {api_err}")
