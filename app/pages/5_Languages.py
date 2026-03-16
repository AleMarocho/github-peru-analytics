import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Language Analytics", page_icon="💻", layout="wide")

def main():
    st.title("💻 Language Analytics")
    st.markdown("Analyzing technical choices in the ecosystem based on primary repository language.")
    
    try:
        repos = pd.read_csv("data/processed/repositories.csv")
        classes = pd.read_csv("data/processed/classifications.csv")
        df = pd.merge(repos, classes[['repo_id', 'industry_name']], 
                      left_on='id', right_on='repo_id', how='inner')
    except:
        st.error("Data missing.")
        return
        
    valid_langs = df.dropna(subset=['language'])
    lang_counts = valid_langs['language'].value_counts().reset_index()
    lang_counts.columns = ['Language', 'Count']
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Most Frequently Used")
        fig_bar = px.bar(lang_counts.head(15), x='Language', y='Count',
                         color='Language', text='Count', height=400)
        st.plotly_chart(fig_bar, use_container_width=True)
        
    with col2:
        st.subheader("Language vs Industry Heatmap")
        
        # Cross tabulation of top 10 languages and top 6 industries
        top_langs = lang_counts.head(10)['Language'].tolist()
        top_inds = df['industry_name'].value_counts().head(6).index.tolist()
        
        heat_df = df[df['language'].isin(top_langs) & df['industry_name'].isin(top_inds)]
        cross = pd.crosstab(heat_df['industry_name'], heat_df['language'])
        
        fig_heat = px.imshow(cross, text_auto=True, color_continuous_scale='Blues',
                             aspect="auto", height=400)
        st.plotly_chart(fig_heat, use_container_width=True)
        
    st.markdown("---")
    st.subheader("Top Developers by Language")
    
    selected_lang = st.selectbox("Choose a programming language:", lang_counts['Language'])
    lang_repos = valid_langs[valid_langs['language'] == selected_lang]
    
    top_devs = lang_repos.groupby('owner_login').agg(
        repos_in_lang=('id', 'count'),
        stars_in_lang=('stargazers_count', 'sum')
    ).reset_index().sort_values('stars_in_lang', ascending=False).head(10)
    
    st.dataframe(top_devs, use_container_width=True)

if __name__ == "__main__":
    main()
