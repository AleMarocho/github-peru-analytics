import streamlit as st
import pandas as pd
import json
import os
import plotly.express as px
import plotly.graph_objects as go

# Set page configuration FIRST before anything else
st.set_page_config(
    page_title="GitHub Peru Analytics",
    page_icon="🇵🇪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load data helper functions
@st.cache_data
def load_data():
    base_path = "data/"
    
    try:
        users = pd.read_csv(os.path.join(base_path, "processed/users.csv"))
        repos = pd.read_csv(os.path.join(base_path, "processed/repositories.csv"))
        metrics = pd.read_csv(os.path.join(base_path, "metrics/user_metrics.csv"))
        classifications = pd.read_csv(os.path.join(base_path, "processed/classifications.csv"))
        
        with open(os.path.join(base_path, "metrics/ecosystem_metrics.json"), "r") as f:
            eco_metrics = json.load(f)
            
        full_repos = pd.merge(repos, classifications[['repo_id', 'industry_code', 'industry_name', 'confidence']], 
                              left_on='id', right_on='repo_id', how='left')
                              
        return users, full_repos, metrics, eco_metrics
    except Exception as e:
        st.error(f"Error loading data: {e}. Please ensure data collection and processing scripts have been run.")
        return None, None, None, None

def main():
    st.sidebar.title("🇵🇪 GitHub Peru Analytics")
    st.sidebar.markdown("---")
    
    users, repos, metrics, eco = load_data()
    
    if users is None:
        return
        
    st.title("Ecosystem Overview")
    st.markdown("A comprehensive view of the Peruvian Developer Ecosystem on GitHub.")
    
    # CSS to inject for better styling
    st.markdown("""
        <style>
        .metric-card {
            background-color: #f0f2f6; 
            border-radius: 10px; 
            padding: 20px;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
        }
        [data-testid="stMetricValue"] {
            font-size: 2.2rem;
            color: #1f77b4;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # ------------------ TOP METRICS ------------------
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="Total Developers", value=f"{eco['ecosystem_size']['total_developers']:,}")
    with col2:
        st.metric(label="Total Repositories", value=f"{eco['ecosystem_size']['total_repositories']:,}")
    with col3:
        st.metric(label="Total Stars Received", value=f"{eco['ecosystem_size']['total_stars']:,}")
    with col4:
        st.metric(label="Active Developers", value=f"{eco['health_indicators']['active_developer_pct']}%")
        
    st.markdown("---")
    
    # ------------------ CHARTS ROW 1 ------------------
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Top Programming Languages")
        langs = eco['top_technologies']['most_popular_languages']
        df_langs = pd.DataFrame(list(langs.items()), columns=['Language', 'Count'])
        fig = px.bar(df_langs, x='Count', y='Language', orientation='h', 
                     color='Language', color_discrete_sequence=px.colors.qualitative.Pastel)
        fig.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Industry Distribution (CIIU)")
        inds = eco['industry_distribution']
        df_inds = pd.DataFrame(list(inds.items()), columns=['Industry', 'Count'])
        fig_pie = px.pie(df_inds, values='Count', names='Industry', hole=0.4,
                         color_discrete_sequence=px.colors.qualitative.Set3)
        fig_pie.update_layout(showlegend=False)
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)
        
    # ------------------ TOP BOARDS ------------------
    st.markdown("---")
    st.subheader("Leaderboards")
    
    col_l1, col_l2 = st.columns(2)
    
    with col_l1:
        st.markdown("**Top 10 Developers by Impact Score**")
        top_devs = metrics.sort_values(by='impact_score', ascending=False).head(10)
        st.dataframe(top_devs[['login', 'name', 'impact_score', 'h_index', 'total_stars_received']], 
                     use_container_width=True, hide_index=True)
                     
    with col_l2:
        st.markdown("**Top 10 Repositories by Stars**")
        top_repos = repos.sort_values(by='stargazers_count', ascending=False).head(10)
        st.dataframe(top_repos[['name', 'owner_login', 'language', 'stargazers_count']], 
                     use_container_width=True, hide_index=True)
    
if __name__ == "__main__":
    main()
