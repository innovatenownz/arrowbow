import streamlit as st
import pandas as pd
import json
import streamlit.components.v1 as components
from datetime import datetime
from jinja2 import Template
import db
from ai_engine import AssessmentAI
from pdf_service import PDFGeneratorClient
import os

# --- INITIALIZE DB ---
db.init_db()

st.set_page_config(page_title="Arrowbow Team Assessment", layout="wide")

# --- LOAD QUESTIONS ---
@st.cache_data
def load_questions():
    try:
        with open('questions.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("questions.json not found.")
        st.stop()
MASTER_DATA = load_questions()

# --- NEW PDF-STYLE HTML TEMPLATE ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <link href="https://fonts.googleapis.com/css2?family=Helvetica+Now+Display:wght@400;700&display=swap" rel="stylesheet">
    <style>
        body { 
            font-family: 'Helvetica', 'Arial', sans-serif; 
            color: #333; 
            background-color: #ffffff; 
            padding: 40px; 
            max-width: 1000px;
            margin: 0 auto;
        }
        
        /* BRANDING */
        .brand-red { color: #C00000; }
        .brand-bg-red { background-color: #C00000; }
        
        /* COVER SECTION */
        .header { border-bottom: 4px solid #C00000; padding-bottom: 20px; margin-bottom: 40px; display: flex; justify-content: space-between; align-items: flex-end; }
        .title { font-size: 36px; font-weight: bold; text-transform: uppercase; line-height: 1.1; }
        .subtitle { font-size: 18px; color: #666; margin-top: 5px; }
        .meta { text-align: right; font-size: 14px; color: #888; }
        
        /* EXECUTIVE SUMMARY */
        .exec-summary { 
            background: #f8f9fa; 
            padding: 30px; 
            border-left: 8px solid #C00000; 
            margin-bottom: 50px; 
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        }
        .exec-summary h3 { margin-top: 0; color: #C00000; text-transform: uppercase; letter-spacing: 1px; }
        
        /* CHART SECTION */
        .chart-container { margin-bottom: 50px; }
        .chart-row { display: flex; align-items: center; margin-bottom: 15px; }
        .chart-label { width: 250px; font-weight: bold; font-size: 14px; }
        .bar-container { flex-grow: 1; background: #eee; height: 25px; border-radius: 4px; overflow: hidden; }
        .bar-fill { height: 100%; background: #C00000; text-align: right; padding-right: 10px; color: white; font-size: 12px; line-height: 25px; font-weight: bold; width: 0; transition: width 1s; }
        
        /* INSIGHTS GRID */
        .insight-section { margin-bottom: 40px; page-break-inside: avoid; }
        .insight-header { background: #333; color: white; padding: 10px 15px; font-weight: bold; border-radius: 4px 4px 0 0; display: flex; justify-content: space-between; }
        .insight-body { border: 1px solid #ddd; padding: 20px; border-radius: 0 0 4px 4px; background: #fff; }
        .ai-analysis { font-size: 14px; line-height: 1.6; color: #444; margin-bottom: 15px; border-bottom: 1px dashed #ccc; padding-bottom: 15px; }
        
        /* SCORING TABLE */
        .mini-table { width: 100%; font-size: 12px; border-collapse: collapse; }
        .mini-table td { padding: 6px 0; border-bottom: 1px solid #eee; }
        .score-bad { color: #C00000; font-weight: bold; }
        .score-good { color: #2e7d32; font-weight: bold; }

        /* FOOTER */
        .footer { margin-top: 60px; border-top: 1px solid #ccc; padding-top: 20px; font-size: 12px; color: #999; text-align: center; }
    </style>
</head>
<body>
    <div class="header">
        <div>
            <div class="title">Baseline Sales<br>Assessment</div>
            <div class="subtitle">Arrowbow Sales Performance Accelerator</div>
        </div>
        <div class="meta">
            <strong>{{ company_name }}</strong><br>
            {{ date }}
        </div>
    </div>

    <div class="exec-summary">
        <h3>Executive Summary</h3>
        <p>{{ exec_summary | replace('\n', '<br>') }}</p>
        <p style="margin-top: 20px; font-weight: bold;">
            Overall Maturity Score: <span style="font-size: 24px; color: #C00000;">{{ overall_score }}%</span>
        </p>
    </div>

    <h2 style="border-bottom: 2px solid #eee; padding-bottom: 10px;">Performance by Pillar</h2>
    <div class="chart-container">
        {% for section in sections %}
        <div class="chart-row">
            <div class="chart-label">{{ section.name }}</div>
            <div class="bar-container">
                <div class="bar-fill" style="width: {{ section.score_percent }}%;">{{ section.score }}/10</div>
            </div>
        </div>
        {% endfor %}
    </div>

    <h2 style="border-bottom: 2px solid #eee; padding-bottom: 10px; margin-top: 50px;">Detailed Insights</h2>
    {% for section in sections %}
    <div class="insight-section">
        <div class="insight-header">
            <span>{{ section.name }}</span>
            <span style="background: rgba(255,255,255,0.2); padding: 0 10px; border-radius: 10px;">{{ section.score }}/10</span>
        </div>
        <div class="insight-body">
            <div class="ai-analysis">
                {{ section.insight }}
            </div>
            <table class="mini-table">
                {% for q in section.questions %}
                <tr>
                    <td style="width: 80%;">{{ q.text }}</td>
                    <td style="text-align: right;" class="{{ 'score-bad' if q.score|float < 5 else 'score-good' }}">
                        {{ q.score }}
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </div>
    {% endfor %}
    
    <div class="footer">
        Arrowbow Sales Performance Accelerator | Confidential Report
    </div>
</body>
</html>
"""

def render_html_report(data):
    return Template(HTML_TEMPLATE).render(data)

# --- SIDEBAR: NAVIGATION ---
with st.sidebar:
    st.image("https://via.placeholder.com/150x50?text=ARROWBOW", use_container_width=True) # Placeholder for logo
    st.title("🚀 Team Mode")
    page = st.radio("Go to", ["Project Dashboard", "Assessment Room"])

# --- PAGE 1: DASHBOARD ---
if page == "Project Dashboard":
    st.title("🗂️ Company Projects")
    
    # Create Project
    with st.expander("➕ Create New Project", expanded=True):
        with st.form("new_proj"):
            c1, c2 = st.columns(2)
            name = c1.text_input("Company Name")
            ind = c2.text_input("Industry")
            if st.form_submit_button("Create"):
                if name:
                    db.create_project(name, ind)
                    st.success(f"Project '{name}' created!")
                    st.rerun()

    # List Projects
    st.subheader("Active Projects")
    projs = db.get_all_projects()
    if not projs.empty:
        for _, row in projs.iterrows():
            col1, col2, col3 = st.columns([3, 2, 1])
            col1.markdown(f"**{row['company_name']}**")
            col2.caption(f"{row['industry']}")
            if col3.button("Enter", key=f"ent_{row['id']}"):
                st.session_state.active_project_id = row['id']
                st.session_state.active_company_name = row['company_name']
                if 'current_user_name' in st.session_state:
                    del st.session_state['current_user_name']
                st.rerun()
    else:
        st.info("No projects yet.")

# --- PAGE 2: ASSESSMENT ROOM ---
elif page == "Assessment Room":
    if 'active_project_id' not in st.session_state:
        st.warning("Please select a project from the Dashboard first.")
        st.stop()
        
    st.title(f"🏢 {st.session_state.active_company_name}")
    
    # --- AUTHENTICATION LAYER ---
    if 'current_user_name' not in st.session_state:
        st.info("Who are you?")
        user_name = st.text_input("Enter your name to join this session:")
        if st.button("Join Session"):
            if user_name:
                aid = db.join_project(st.session_state.active_project_id, user_name)
                st.session_state.current_user_name = user_name
                st.session_state.my_assessment_id = aid
                st.rerun()
        st.stop() 

    # --- MAIN UI ---
    user = st.session_state.current_user_name
    st.caption(f"Logged in as: **{user}**")
    
    tab1, tab2 = st.tabs(["📝 My Input", "📊 Team Report & Download"])
    
    # === TAB 1: INDIVIDUAL SCORING ===
    with tab1:
        st.subheader(f"{user}'s Evaluation")
        my_scores_df = db.get_my_scores(st.session_state.my_assessment_id)
        
        for section in MASTER_DATA['sections']:
            with st.expander(f"📌 {section['title']}", expanded=True):
                for q in section['questions']:
                    col_q, col_s = st.columns([3, 1])
                    col_q.markdown(f"**{q['text']}**")
                    
                    # Fetch existing score for this user
                    existing = my_scores_df[my_scores_df['question_id'] == q['id']]
                    val = int(existing.iloc[0]['score']) if not existing.empty else 0
                    
                    # Live Save Callback
                    def save_callback(qid=q['id'], sid=section['id']):
                        s = st.session_state[f"s_{qid}"]
                        db.save_score(st.session_state.my_assessment_id, qid, sid, s)
                        
                    col_s.slider(
                        "Score", 0, 10, val, 
                        key=f"s_{q['id']}", 
                        label_visibility="collapsed",
                        on_change=save_callback
                    )

    # === TAB 2: AGGREGATED REPORT ===
    with tab2:
        st.subheader("Team Consensus")
        
        scorers = db.get_project_scorers(st.session_state.active_project_id)
        st.success(f"Active Contributors: {', '.join(scorers)}")
        
        if st.button("🔄 Refresh Data"):
            st.rerun()
            
        agg_df = db.get_aggregated_scores(st.session_state.active_project_id)
        
        if agg_df.empty:
            st.warning("No data submitted yet.")
        else:
            # 1. DISPLAY MATRIX
            st.markdown("### Scoring Breakdown")
            display_data = []
            for sec in MASTER_DATA['sections']:
                for q in sec['questions']:
                    row = agg_df[agg_df['question_id'] == q['id']]
                    if not row.empty:
                        avg = row.iloc[0]['avg_score']
                        display_data.append({
                            "Question": q['text'],
                            "Average": f"{avg:.1f}",
                            "Inputs": row.iloc[0]['scorer_count']
                        })
            st.dataframe(pd.DataFrame(display_data), use_container_width=True)
            
            st.divider()
            
            # 2. GENERATE REPORT BUTTON
            if st.button("✨ Generate / Update Team Report", type="primary"):
                with st.spinner("Aggregating scores & consulting Gemini 2.5 Flash..."):
                    # Prepare data
                    report_struct = []
                    for sec in MASTER_DATA['sections']:
                        sec_qs = agg_df[agg_df['section_id'] == sec['id']]
                        if sec_qs.empty: continue
                        sec_avg = sec_qs['avg_score'].mean()
                        weak_qs_text = []
                        q_details = []
                        for q in sec['questions']:
                            q_row = sec_qs[sec_qs['question_id'] == q['id']]
                            if q_row.empty: continue
                            score = q_row.iloc[0]['avg_score']
                            q_details.append({'text': q['text'], 'score': f"{score:.1f}"})
                            if score < 5: weak_qs_text.append(q['text'])
                        
                        report_struct.append({
                            'name': sec['title'],
                            'score': sec_avg,
                            'score_percent': (sec_avg * 10), # For the chart width
                            'weak_qs': weak_qs_text,
                            'questions': q_details
                        })
                    
                    # AI Processing
                    try:
                        ai = AssessmentAI()
                        overall = agg_df['avg_score'].mean()
                        overall_percent = overall * 10
                        lowest = min(report_struct, key=lambda x: x['score'])
                        
                        # 1. Exec Summary
                        exec_sum = ai.generate_executive_summary(
                            st.session_state.active_company_name, overall, lowest['name']
                        )
                        
                        # 2. Section Analysis
                        final_sections = []
                        for s in report_struct:
                            insight = ai.generate_insight(s['name'], s['score'], s['questions'])
                            final_sections.append({
                                'name': s['name'],
                                'score': f"{s['score']:.1f}",
                                'score_percent': s['score_percent'],
                                'insight': insight,
                                'questions': s['questions']
                            })
                            
                        # Save to State
                        st.session_state.team_report = {
                            'company_name': st.session_state.active_company_name,
                            'date': datetime.now().strftime("%B %d, %Y"),
                            'exec_summary': exec_sum,
                            'overall_score': f"{overall_percent:.1f}", # PDF style uses %
                            'sections': final_sections
                        }
                    except Exception as e:
                        st.error(f"AI Error: {e}")
                        st.stop()
                        
                st.rerun()

            # 3. PREVIEW & DOWNLOADS
            if 'team_report' in st.session_state:
                st.success("Report Ready!")
                
                # Render HTML
                html_content = render_html_report(st.session_state.team_report)
                
                # Preview Window
                with st.expander("👀 Report Preview", expanded=True):
                    components.html(html_content, height=800, scrolling=True)
                
                # Download Buttons
                col_d1, col_d2 = st.columns(2)
                
                with col_d1:
                    st.download_button(
                        label="📄 Download Report (HTML)",
                        data=html_content,
                        file_name=f"Arrowbow_Assessment_{st.session_state.active_company_name}.html",
                        mime="text/html"
                    )