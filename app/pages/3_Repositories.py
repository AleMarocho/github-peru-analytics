import streamlit as st
import pandas as pd
import json
import os

st.set_page_config(page_title="Repository Browser", page_icon="📦", layout="wide")

def main():
    st.title("📦 Repository Browser")
    st.markdown("Search through 1,000+ public repositories scraped from Peru.")
    
    base_path = "data/processed/repositories.csv"
    class_path = "data/processed/classifications.csv"
    
    if not (os.path.exists(base_path) and os.path.exists(class_path)):
        st.warning("Data not found. Run extraction and classification sequences.")
        return
        
    repos = pd.read_csv(base_path)
    classes = pd.read_csv(class_path)
    
    # Merge classification info
    full_df = pd.merge(repos, classes[['repo_id', 'industry_name', 'confidence', 'reasoning']], 
                       left_on='id', right_on='repo_id', how='left')
                       
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    search = col1.text_input("Search by Name or Description", "")
    ind_filter = col2.selectbox("Filter Industry", ["All"] + list(full_df['industry_name'].dropna().unique()))
    lang_filter = col3.selectbox("Filter Language", ["All"] + list(full_df['language'].dropna().unique()))
    
    st.markdown("---")
    
    filtered = full_df.copy()
    if search:
        search_lower = search.lower()
        filtered = filtered[
            filtered['name'].str.lower().str.contains(search_lower, na=False) |
            filtered['description'].str.lower().str.contains(search_lower, na=False)
        ]
    if ind_filter != "All":
        filtered = filtered[filtered['industry_name'] == ind_filter]
    if lang_filter != "All":
        filtered = filtered[filtered['language'] == lang_filter]
        
    st.metric("Repositories matching criteria", len(filtered))
    
    # Render detail views for each repo
    for idx, row in filtered.head(20).iterrows(): # Render top 20 to avoid freezing DOM
        with st.expander(f"⭐ {int(row['stargazers_count'])} | 🔗 {row['full_name']}"):
            c1, c2 = st.columns([2, 1])
            with c1:
                st.markdown(f"**Description:** {row['description'] or 'No description provided.'}")
                st.markdown(f"**Language:** {row['language']}  |  **Forks:** {int(row['forks_count'])}  |  [View on GitHub]({row['url']})")
                st.markdown(f"**Topics:** {row['topics'] if pd.notna(row['topics']) else 'None'}")
                
            with c2:
                # Industry detail panel
                st.info(f"**Classification:** {row['industry_name']}\n\n"
                        f"**Confidence:** {row['confidence'].capitalize()}\n\n"
                        f"**Reasoning:** {row['reasoning']}")
                        
    if len(filtered) > 20:
        st.info(f"Showing top 20 results. Refine your search to see more of the {len(filtered)} matching repositories.")

if __name__ == "__main__":
    main()
