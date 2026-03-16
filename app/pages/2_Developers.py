import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Developer Explorer", page_icon="👩‍💻", layout="wide")

def main():
    st.title("👩‍💻 Developer Explorer")
    st.markdown("Explore individual developers, sort by metrics, and dive deep into their profiles.")
    
    base_path = "data/metrics/user_metrics.csv"
    if not os.path.exists(base_path):
        st.warning("Metrics data not found. Run the metrics calculation script first.")
        return
        
    metrics = pd.read_csv(base_path)
    
    # Filters
    col1, col2 = st.columns(2)
    with col1:
        search_query = st.text_input("🔍 Search by username or name", "")
    with col2:
        sort_by = st.selectbox("Sort by", ["impact_score", "h_index", "total_stars_received", "followers", "total_repos"])
        
    # Apply filters
    filtered_df = metrics.copy()
    if search_query:
        # Search in login or name, robust against NaNs
        filtered_df = filtered_df[
            filtered_df['login'].str.contains(search_query, case=False, na=False) |
            filtered_df['name'].str.contains(search_query, case=False, na=False)
        ]
        
    filtered_df = filtered_df.sort_values(by=sort_by, ascending=False)
    
    # Display table
    columns_to_show = ['login', 'name', 'company', 'location', 'public_repos', 
                       'total_stars_received', 'h_index', 'impact_score', 'primary_languages']
    
    st.dataframe(filtered_df[columns_to_show], use_container_width=True, hide_index=True)
    
    # Export
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download data as CSV",
        data=csv,
        file_name='peru_developers.csv',
        mime='text/csv',
    )

if __name__ == "__main__":
    main()
