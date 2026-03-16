import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="Industry Analysis", page_icon="🏭", layout="wide")

def main():
    st.title("🏭 Industry Analysis")
    st.markdown("Distribution of software categories using the standard Peruvian CIIU classification.")
    
    try:
        repos = pd.read_csv("data/processed/repositories.csv")
        classes = pd.read_csv("data/processed/classifications.csv")
        df = pd.merge(repos, classes[['repo_id', 'industry_name', 'industry_code', 'reasoning']], 
                      left_on='id', right_on='repo_id', how='inner')
    except:
        st.error("Data missing.")
        return
        
    if df.empty:
        st.warning("No classification data loaded.")
        return

    # Pie Chart
    col1, col2 = st.columns([1, 1])
    
    ind_counts = df['industry_name'].value_counts().reset_index()
    ind_counts.columns = ['Industry', 'Count']
    
    with col1:
        st.subheader("Repositories per Subject")
        fig_bar = px.bar(ind_counts, x='Count', y='Industry',
                         color='Count', color_continuous_scale='Viridis',
                         orientation='h', height=500)
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_bar, use_container_width=True)
        
    with col2:
        st.subheader("Dominant Sectors")
        fig_pie = px.pie(ind_counts, values='Count', names='Industry', 
                         hole=0.5, height=500, color_discrete_sequence=px.colors.qualitative.Plotly)
        fig_pie.update_traces(textposition='inside')
        st.plotly_chart(fig_pie, use_container_width=True)
        
    st.markdown("---")
    
    st.subheader("Top Software by Industry")
    selected_ind = st.selectbox("Select an Industry to explore its top repositories", ind_counts['Industry'])
    
    sub_df = df[df['industry_name'] == selected_ind].sort_values('stargazers_count', ascending=False)
    
    for _, row in sub_df.head(5).iterrows():
        st.markdown(f"#### [{row['name']}]({row['url']}) (⭐ {int(row['stargazers_count'])})")
        st.write(f"_{row['description']}_")
        st.caption(f"GPT-4 Reasoning: {row['reasoning']}")
        st.markdown("---")

if __name__ == "__main__":
    main()
