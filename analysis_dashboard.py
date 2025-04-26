import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import re
import os
from wordcloud import WordCloud
from sklearn.feature_extraction.text import CountVectorizer
from collections import Counter

st.set_page_config(
    page_title="Job Market Trend Analysis",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main {
        background-color: #f5f5f5;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 5px;
        border: none;
        padding: 10px 24px;
        text-align: center;
        text-decoration: none;
        display: inline-block;
        font-size: 16px;
        margin: 4px 2px;
        cursor: pointer;
    }
    .stSelectbox, .stTextInput, .stSlider, .stDateInput {
        margin-bottom: 20px;
    }
    .css-1aumxhk {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_data(keyword, date_filter=None):
    try:
        if not os.path.exists('job_data'):
            st.error("The 'job_data' directory does not exist.")
            return None
            
        files = [f for f in os.listdir('job_data') if f.startswith(f'naukri_jobs_{keyword}')]
        if not files:
            st.warning(f"No data files found for keyword: {keyword}")
            return None
    
        latest_file = sorted(files)[-1]
        file_path = os.path.join('job_data', latest_file)
        
    
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else: 
            df = pd.read_json(file_path)
        
        if 'Scraped Date' in df.columns:
            df['Scraped Date'] = pd.to_datetime(df['Scraped Date'], errors='coerce')
        
        numeric_cols = ['Min Salary', 'Max Salary', 'Min Experience', 'Max Experience']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        if date_filter:
            days = int(date_filter)
            cutoff_date = datetime.now() - timedelta(days=days)
            df = df[df['Scraped Date'] >= cutoff_date]
        
        return df
    
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None
def plot_salary_distribution(df):
    df = df.dropna(subset=['Min Salary', 'Max Salary'])
    
    # Calculate average salary (midpoint between min and max)
    df['Avg Salary'] = (df['Min Salary'] + df['Max Salary']) / 2
    
    # Calculate statistics
    stats = {
        'Mean': df['Avg Salary'].mean(),
        'Median': df['Avg Salary'].median(),
        'Mode': df['Avg Salary'].mode()[0]
    }
    
    # Function to format INR values for display
    def format_inr(value):
        if value >= 10000000:  # 1 crore or more
            return f'₹{value/10000000:.1f} Cr'
        elif value >= 100000:  # 1 lakh or more
            return f'₹{value/100000:.1f} L'
        else:
            return f'₹{value/1000:.0f} K'
    
    fig = go.Figure()
    
    # Add single bar chart for the salary statistics
    fig.add_trace(go.Bar(
        x=list(stats.keys()),
        y=list(stats.values()),
        marker_color='#1f77b4',
        opacity=0.75,
        text=[format_inr(val) for val in stats.values()],
        textposition='outside'
    ))
    
    # Convert values to lakhs for y-axis display
    y_values = [val/100000 for val in stats.values()]  # Convert to lakhs
    
    fig.update_layout(
        title_text='Salary Statistics (Mean, Median, Mode)',
        xaxis_title_text='Statistic',
        yaxis_title_text='Salary (INR)',
        bargap=0.2,
        template='plotly_white',
        showlegend=False,
        uniformtext_minsize=8,
        uniformtext_mode='hide'
    )
    
    # Format y-axis to show clean lakh values
    fig.update_yaxes(
        tickprefix='₹',
        ticksuffix=' L',
        tickvals=[val/100000 for val in stats.values()],  # Use actual values in lakhs
        ticktext=[f"{val/100000:.1f}" for val in stats.values()]  # Show as 8.0 instead of 8000000
    )
    
    st.plotly_chart(fig, use_container_width=True)
def format_inr(value):
    """Format numbers to Indian Rupees (INR) with proper notation"""
    if pd.isna(value):
        return "N/A"
    
    value = float(value)
    if value >= 10000000:  # 1 crore or more
        return f'₹{value/10000000:.1f} Cr'
    elif value >= 100000:  # 1 lakh or more
        return f'₹{value/100000:.1f} L'
    else:
        return f'₹{value:,.0f}'

def plot_experience_distribution(df):
    # Filter out NaN values and extreme outliers
    df = df.dropna(subset=['Min Experience', 'Min Salary'])
    df = df[(df['Min Experience'] >= 0) & (df['Min Experience'] <= 30)]
    df = df[(df['Min Salary'] >= 100000) & (df['Min Salary'] <= 5000000)]  # 1L to 50L
    
    if df.empty:
        st.warning("Not enough data to plot experience vs salary")
        return
    
    # Create experience bins
    bins = [0, 2, 5, 8, 12, 15, 20, 30]
    labels = ['0-2', '3-5', '6-8', '9-12', '13-15', '16-20', '20+']
    df['Experience Range'] = pd.cut(df['Min Experience'], bins=bins, labels=labels)
    
    # Calculate median salary for each experience range
    exp_salary = df.groupby('Experience Range', observed=True)['Min Salary'].median().reset_index()
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=exp_salary['Experience Range'],
        y=exp_salary['Min Salary'],
        marker_color='#4CAF50',
        opacity=0.8,
        text=[format_inr(val) for val in exp_salary['Min Salary']],
        textposition='outside'
    ))
    
    fig.update_layout(
        title_text='Median Salary by Experience Range',
        xaxis_title_text='Years of Experience',
        yaxis_title_text='Median Salary (INR)',
        template='plotly_white',
        uniformtext_minsize=8,
        uniformtext_mode='hide'
    )
    
    # Format y-axis as INR
    fig.update_yaxes(
        tickprefix='₹',
        tickformat=',.0f',
        range=[0, exp_salary['Min Salary'].max() * 1.2]  # Add some padding
    )
    
    st.plotly_chart(fig, use_container_width=True)

# Top companies plot
def plot_top_companies(df, top_n=10):
    top_companies = df['Company Name'].value_counts().head(top_n)
    
    fig = px.bar(
        top_companies,
        x=top_companies.index,
        y=top_companies.values,
        labels={'x': 'Company', 'y': 'Number of Jobs'},
        title=f'Top {top_n} Companies Hiring',
        color=top_companies.values,
        color_continuous_scale='Viridis'
    )
    
    fig.update_layout(
        xaxis_tickangle=-45,
        template='plotly_white'
    )
    
    st.plotly_chart(fig, use_container_width=True)

# Location distribution plot
def plot_location_distribution(df, top_n=10):
    location_counts = df['Location'].value_counts().head(top_n)
    
    fig = px.pie(
        location_counts,
        names=location_counts.index,
        values=location_counts.values,
        title=f'Top {top_n} Job Locations'
    )
    
    st.plotly_chart(fig, use_container_width=True)

# Skills word cloud
def plot_skills_wordcloud(df):
    if 'Tags and Skills' not in df.columns:
        st.warning("No skills data available")
        return
    
    skills_text = ' '.join(df['Tags and Skills'].dropna().astype(str))
    
    if not skills_text.strip():
        st.warning("No skills data available")
        return
    
    wordcloud = WordCloud(
        width=800,
        height=400,
        background_color='white',
        colormap='viridis',
        max_words=100
    ).generate(skills_text)
    
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wordcloud, interpolation='bilinear')
    ax.axis('off')
    ax.set_title('Most In-Demand Skills')
    
    st.pyplot(fig)

# Salary vs Experience scatter plot
def plot_salary_vs_experience(df):
    df_clean = df.dropna(subset=['Min Salary', 'Min Experience'])
    
    if df_clean.empty:
        st.warning("Not enough data to plot salary vs experience")
        return
    
    fig = px.scatter(
        df_clean,
        x='Min Experience',
        y='Min Salary',
        color='Company Name',
        size='Max Salary',
        hover_name='Job Title',
        title='Salary vs Experience Requirements',
        labels={
            'Min Experience': 'Years of Experience',
            'Min Salary': 'Salary (INR)'
        }
    )
    
    fig.update_layout(
        template='plotly_white',
        hovermode='closest'
    )
    
    st.plotly_chart(fig, use_container_width=True)

# Job posting trend
def plot_job_posting_trend(df):
    if 'Scraped Date' not in df.columns:
        st.warning("No date data available for trend analysis")
        return
    
    daily_counts = df.groupby(df['Scraped Date'].dt.date).size()
    
    if len(daily_counts) < 2:
        st.warning("Not enough date points to show trend")
        return
    
    fig = px.line(
        daily_counts,
        x=daily_counts.index,
        y=daily_counts.values,
        title='Job Posting Trend Over Time',
        labels={'x': 'Date', 'y': 'Number of Jobs Posted'}
    )
    
    fig.update_layout(
        template='plotly_white',
        xaxis_title='Date',
        yaxis_title='Number of Jobs'
    )
    
    st.plotly_chart(fig, use_container_width=True)

# Top job titles
def plot_top_job_titles(df, top_n=10):
    job_title_counts = df['Job Title'].value_counts().head(top_n)
    
    fig = px.bar(
        job_title_counts,
        x=job_title_counts.index,
        y=job_title_counts.values,
        title=f'Top {top_n} Job Titles',
        labels={'x': 'Job Title', 'y': 'Count'}
    )
    
    fig.update_layout(
        xaxis_tickangle=-45,
        template='plotly_white'
    )
    
    st.plotly_chart(fig, use_container_width=True)

# Salary by location
def plot_salary_by_location(df, top_n=10):
    if 'Location' not in df.columns or 'Min Salary' not in df.columns:
        st.warning("Missing required columns for salary by location analysis")
        return
    
    df_clean = df.dropna(subset=['Location', 'Min Salary'])
    
    if df_clean.empty:
        st.warning("Not enough data to plot salary by location")
        return
    
    top_locations = df_clean['Location'].value_counts().head(top_n).index
    df_top = df_clean[df_clean['Location'].isin(top_locations)]
    
    fig = px.box(
        df_top,
        x='Location',
        y='Min Salary',
        title=f'Salary Distribution by Top {top_n} Locations',
        labels={'Min Salary': 'Salary (INR)', 'Location': 'Location'}
    )
    
    fig.update_layout(
        xaxis_tickangle=-45,
        template='plotly_white'
    )
    
    st.plotly_chart(fig, use_container_width=True)

# Main function with improved error handling
def main():
    st.title("📊 Job Market Trend Analysis")
    st.markdown("Analyze job market trends from Naukri.com data")
    
    # Sidebar with filters
    with st.sidebar:
        st.header("Filters")
        
        keyword = st.text_input(
            "Job Keyword",
            value="developer",
            help="Enter the job keyword to analyze (e.g., 'developer', 'data scientist')"
        )
        
        date_filter = st.selectbox(
            "Time Period",
            options=["All time", "Last 7 days", "Last 30 days", "Last 90 days"],
            index=0
        )
        
        salary_range = st.slider(
            "Salary Range (INR)",
            min_value=0,
            max_value=5000000,
            value=(0, 5000000),
            step=100000
        )
        
        experience_range = st.slider(
            "Experience Range (years)",
            min_value=0,
            max_value=30,
            value=(0, 30),
            step=1
        )
        
        # Initialize empty filters (will be updated after data load)
        location_filter = st.multiselect(
            "Locations",
            options=[],
            default=[],
            help="Select locations to filter by"
        )
        
        company_filter = st.multiselect(
            "Companies",
            options=[],
            default=[],
            help="Select companies to filter by"
        )
        
        analyze_button = st.button("Analyze Job Market")
    
    # Load data
    date_mapping = {
        "All time": None,
        "Last 7 days": 7,
        "Last 30 days": 30,
        "Last 90 days": 90
    }
    
    df = load_data(keyword, date_mapping[date_filter])
    
    if df is None:
        st.warning(f"No data found for keyword: {keyword}. Please scrape data first.")
        return
    
    # Update filter options based on loaded data
    with st.sidebar:
        location_options = sorted(df['Location'].dropna().unique())
        location_filter = st.multiselect(
            "Locations",
            options=location_options,
            default=location_filter,
            help="Select locations to filter by",
            key='location_filter'
        )
        
        company_options = sorted(df['Company Name'].dropna().unique())
        company_filter = st.multiselect(
            "Companies",
            options=company_options,
            default=company_filter,
            help="Select companies to filter by",
            key='company_filter'
        )
    
    # Apply filters with proper null handling
    try:
        if location_filter:
            df = df[df['Location'].isin(location_filter)]
        
        if company_filter:
            df = df[df['Company Name'].isin(company_filter)]
        
        # Handle NaN values in numeric filters
        df_filtered = df[
            (df['Min Salary'].fillna(0) >= salary_range[0]) & 
            (df['Max Salary'].fillna(float('inf')) <= salary_range[1]) &
            (df['Min Experience'].fillna(0) >= experience_range[0]) & 
            (df['Max Experience'].fillna(float('inf')) <= experience_range[1])
        ]
        
        if df_filtered.empty:
            st.warning("No data matches your filter criteria. Please adjust your filters.")
            return
            
        df = df_filtered
    
    except Exception as e:
        st.error(f"Error applying filters: {str(e)}")
        return
    
    # Display summary stats with error handling
    st.subheader("Summary Statistics")
    
    try:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Jobs", len(df))
        
        avg_min_salary = df['Min Salary'].mean()
        col2.metric("Average Min Salary", f"₹{int(avg_min_salary):,}" if not pd.isna(avg_min_salary) else "N/A")
        
        avg_exp = df['Min Experience'].mean()
        col3.metric("Average Experience", f"{avg_exp:.1f} years" if not pd.isna(avg_exp) else "N/A")
        
        unique_companies = df['Company Name'].nunique()
        col4.metric("Unique Companies", unique_companies if not pd.isna(unique_companies) else "N/A")
    
    except Exception as e:
        st.error(f"Error calculating summary statistics: {str(e)}")
    
    # Main analysis tabs
    tab1, tab2, tab3, tab4 = st.tabs(
        ["Salary Analysis", "Experience Analysis", "Company Analysis", "Skills Analysis"]
    )
    
    with tab1:
        st.subheader("Salary Analysis")
        
        col1, col2 = st.columns(2)
        with col1:
            plot_salary_distribution(df)
        with col2:
            plot_salary_by_location(df)
        
        plot_salary_vs_experience(df)
    
    with tab2:
        st.subheader("Experience Analysis")
        
        col1, col2 = st.columns(2)
        with col1:
            plot_experience_distribution(df)
        with col2:
            plot_top_job_titles(df)
    
    with tab3:
        st.subheader("Company Analysis")
        
        col1, col2 = st.columns(2)
        with col1:
            plot_top_companies(df)
        with col2:
            plot_location_distribution(df)
        
        plot_job_posting_trend(df)
    
    with tab4:
        st.subheader("Skills Analysis")
        
        plot_skills_wordcloud(df)
        
        # Top skills table
        st.subheader("Top Skills Breakdown")
        
        try:
            # Extract individual skills
            all_skills = []
            if 'Tags and Skills' in df.columns:
                for skills in df['Tags and Skills'].dropna():
                    if isinstance(skills, str) and skills != 'Not Specified':
                        skill_list = [s.strip() for s in skills.split(',')]
                        all_skills.extend(skill_list)
            
            if all_skills:
                skill_counts = Counter(all_skills)
                top_skills = pd.DataFrame.from_dict(skill_counts, orient='index', columns=['Count']).sort_values('Count', ascending=False)
                st.dataframe(top_skills.head(20), use_container_width=True)
            else:
                st.warning("No skills data available")
        except Exception as e:
            st.error(f"Error processing skills data: {str(e)}")
    
    # Raw data view
    with st.expander("View Raw Data"):
        st.dataframe(df, use_container_width=True)

if __name__ == "__main__":
    main()