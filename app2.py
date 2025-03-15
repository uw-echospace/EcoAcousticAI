import os
import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image 
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Function to extract datetime from filename - Added for activity plot
def extract_datetime_from_filename(filename):
    """Extracts datetime from a filename in format: 'batdetect2_pipeline_20210603_034102.csv'"""
    try:
        parts = filename.split('_')
        date_str, time_str = parts[2], parts[3].split('.')[0]  # Extract date and time
        file_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y%m%d %H%M%S")
        return file_datetime
 
    except (IndexError, ValueError):
        st.error("Filename format incorrect. Expected format: batdetect2_pipeline_YYYYMMDD_HHMMSS.csv")
        return None
        
# Function to safely read CSV files
def safe_read_csv(file_path):
    """Attempts to read a CSV file, skipping empty or invalid ones."""
    try:
        if os.stat(file_path).st_size == 0:  # Check if file is empty
            #st.warning(f"⚠ Skipping empty file: {file_path}")
            return None

        df = pd.read_csv(file_path)

        # if df.empty:
        #     st.warning(f"Skipping file with no data: {file_path}")
        #     return None

        if 'start_time' not in df.columns or 'end_time' not in df.columns or 'class' not in df.columns:
            #st.warning(f"Skipping file with missing columns: {file_path}")
            return None

        return df
    except pd.errors.EmptyDataError:
        st.warning(f"Skipping corrupted file: {file_path}")
        return None
    except Exception as e:
        st.error(f"Error reading file {file_path}: {e}")
        return None
        
# Combine dataframes and compute activity
def combine_dataframes(manila_path):
    combined_data = []

    for root, _, files in os.walk(manila_path):
        for file in files:
            if file.endswith(".csv"):
                file_path = os.path.join(root, file)
                file_datetime = extract_datetime_from_filename(file)

                if file_datetime:
                    df = safe_read_csv(file_path)
                    if df is None:
                        continue  # Skip empty/invalid files

                    # Convert start & end times
                    df['start_time'] = df['start_time'].apply(lambda x: file_datetime + timedelta(seconds=x))
                    df['end_time'] = df['end_time'].apply(lambda x: file_datetime + timedelta(seconds=x))

                    # Compute species count per interval
                    df['species_count'] = df.groupby('start_time')['class'].transform('nunique')

                    combined_data.append(df)
                    
    
    if combined_data:

        # Filter out empty dataframes before concatenation
        combined_data = [df for df in combined_data if not df.empty]
    
        combined_df = pd.concat(combined_data, ignore_index=True)

        # Convert 'start_time' to DatetimeIndex
        combined_df['start_time'] = pd.to_datetime(combined_df['start_time'])
        combined_df = combined_df.set_index('start_time')  # Set 'start_time' as the index

        # Resample to 10-minute intervals
        activity_df = (
            combined_df[['species_count', 'class', 'class_prob', 'KMEANS_CLASSES']]
            .drop_duplicates()
            .resample('10min')  # Resample to 10min intervals
            .agg({
                'species_count': 'sum',  # Sum species count per 10-minute interval
                'class': lambda x: x.mode().iloc[0] if not x.mode().empty else None,  # Most common valid species
                'class_prob': 'mean'  # Average confidence for the interval
            })
        )

        
        # Replace remaining invalid or empty 'class' values with NaN
        activity_df['class'] = activity_df['class'].replace({0: None, '0': None, 'No Data': None})

        # Add a new column for plotting, e.g., filling missing intervals with zero values
        activity_df['heatmap_value'] = activity_df['species_count'].fillna(0)

        # Final cleanup for invalid or empty rows
        activity_df = activity_df.dropna(subset=['class', 'heatmap_value'], how='all')

        
        return combined_df, activity_df
    else:
        return pd.DataFrame(), pd.DataFrame()  # Return empty DataFrame if no data found


def display_summary_statistics(combined_df):
    """Prints key statistics about the acoustic detections instead of displaying a table."""
    
    if combined_df.empty:
        #st.warning("⚠ No activity data available to summarize.")
        return

    # 1. Count of Unique Species Detected
    unique_species = combined_df['class'].nunique()
    
    # 2. Percentage of LF vs HF Detections
    total_detections = len(combined_df)
    lf_detections = len(combined_df[combined_df['KMEANS_CLASSES'] == 'LF'])
    hf_detections = len(combined_df[combined_df['KMEANS_CLASSES'] == 'HF'])

    lf_percentage = (lf_detections / total_detections) * 100 if total_detections > 0 else 0
    hf_percentage = (hf_detections / total_detections) * 100 if total_detections > 0 else 0

    # 3. Percentage of the Day with a Detection
    detected_times = combined_df.index.floor('min').nunique()  # Unique time slots with detections
    total_time_slots = 24 * 60  # Total minutes in a day

    day_coverage = (detected_times / total_time_slots) * 100 if total_time_slots > 0 else 0

    selected_date = combined_df.index.date.min()  # Extracts the earliest date in the dataset

    # Print Summary
    st.write(f"### 📊 Summary Statistics for {selected_date}")
    st.write(f"- **Total Unique Species Detected:** {unique_species}")
    st.write(f"- **Low-Frequency Detections:** {lf_percentage:.2f}%")
    st.write(f"- **High-Frequency Detections:** {hf_percentage:.2f}%")
    st.write(f"- **% of the Day with Detections:** {day_coverage:.2f}%")


# Create the heatmap
def combined_activity_chart(activity_df):
    # Extract Time of Day
    activity_df['time_of_day'] = activity_df.index.strftime('%H:%M')

    # Create the heatmap data
    heatmap_data = activity_df.pivot_table(
        index='time_of_day',
        columns='class',
        values='heatmap_value',
        fill_value=0 
    )

    # Adjust data: Replace zero values with 0.1 for log scale while keeping the legend showing "0"
    heatmap_data_no_zero = heatmap_data.replace(0, 0.1)  # Replace zeros with small value for log scale
    
    custom_viridis_spectrum = [
        [0.0, '#2b0136'],    # Darkest Purple
        [0.05, '#440154'],   # Deep Purple
        [0.1, '#481567'],    # Violet
        [0.15, '#482677'],   # Violet transitioning to Blue
        [0.2, '#453781'],    # Blue-Violet
        [0.25, '#404788'],   # Deep Blue
        [0.3, '#39568C'],    # Blue-Green
        [0.35, '#33638D'],   # Teal-Blue
        [0.4, '#2D708E'],    # Teal
        [0.45, '#287D8E'],   # Teal transitioning to Green
        [0.5, '#238A8D'],    # Green-Teal
        [0.55, '#1F968B'],   # True Green
        [0.6, '#20A387'],    # Bright Green
        [0.65, '#29AF7F'],   # Light Green
        [0.7, '#3CBB75'],    # Green with Yellow Tint
        [0.75, '#55C667'],   # Lime Green
        [0.8, '#73D055'],    # Bright Lime
        [0.85, '#95D840'],   # Yellowish Green
        [0.9, '#B8DE29'],    # Yellow-Green
        [0.95, '#DCE319'],   # Bright Yellow
        [1.0, '#FDE725']     # Light Yellow
    ]



    # Create the heatmap visualization
    fig = go.Figure(data=go.Heatmap(
        z=heatmap_data_no_zero.values,
        x=heatmap_data.columns,
        y=heatmap_data.index,
        xgap=1,
        zmin=0,
        #zmax=activity_df.max().max(),
        colorscale=custom_viridis_spectrum
    ))

    fig.update_layout(
        title={
            'text': 'UBNA Combined Activity Dashboard<br><span style="font-size:12px; color:grey;">If the downloaded PNG is blank, click the home icon to reset axes.</span>',
        },
        xaxis_title='Species Class',
        yaxis_title='Time of Day (24-hour format)',
        yaxis=dict(autorange='reversed'), # Flip Y-axis so 00:00 is on top
        coloraxis_colorbar=dict(title="Detections"),
        height=1200,
        width=500
    )

    st.plotly_chart(fig, use_container_width=True)


# Custom CSS for improved header design
st.markdown("""
    <style>
        .header-banner {
            background-color: #4CAF50;  /* Light green */
            color: #FFFFFF;
            text-align: center;
            padding: 20px 0;
            font-size: 28px;
            font-weight: bold;
            width: 100%;
            margin-bottom: 30px;
        }

        .nav-links {
            display: flex;
            justify-content: center;
            gap: 50px; /* Increased spacing */
            background-color: #A8D5BA;
            padding: 10px 0;
            width: 100%;
        }

        .nav-item {
            color: #FFFFFF;
            text-decoration: none;
            font-weight: bold;
            padding: 5px 20px;
            cursor: pointer;
        }

        .nav-item:hover {
            text-decoration: underline;
        }
    </style>
""", unsafe_allow_html=True)

# Header Banner
st.markdown('<div class="header-banner">EcoAcoustic AI Portal</div>', unsafe_allow_html=True)

# Navigation Links
st.markdown("""
    <div class="nav-links">
        <a class="nav-item" href="/?page=home" target="_self">HOME</a>
        <a class="nav-item" href="/?page=models" target="_self">MODELS</a>
        <a class="nav-item" href="/?page=dashboard" target="_self">DASHBOARD</a>
        <a class="nav-item" href="/?page=contact" target="_self">ABOUT US</a>
    </div>
""", unsafe_allow_html=True)

# Navigation Logic
page = st.query_params.get("page", "home")

# Content for Each Page
if page == "home":
    st.title("🏡 Home")
    st.write("Welcome to the EcoAcoustic AI project portal!")
    st.markdown("""
    ## Introduction
    The Union Bay Natural Area (UBNA) is an ecologically significant urban habitat in Seattle, characterized by its proximity to major highways and Lake Washington, which introduces unique soundscape complexities. This diverse environment hosts various wildlife, including birds and bats, while also being influenced by human-made noise such as traffic and recreational activities.  

    ## Project Overview
    The EcoAcoustic AI project focuses on developing a cloud-hosted automated pipeline for monitoring wildlife sounds in UBNA. Building on previous research centered around bat call detection, this project expands detection capabilities across multiple animal groups and human-generated sounds. The goal is to create a modular, scalable tool for research and community science engagement, promoting ecological awareness within the Greater Seattle area.  

    ## Data Pipeline
    Our project processes passive acoustic monitoring (PAM) data collected from UBNA using AudioMoth devices. These devices capture high-resolution audio (192 kHz or 250 kHz), providing detailed insights into the Union Bay soundscape. Since 2021, over 45 TB of audio data has been collected and stored in NSF Open Storage Network buckets.  

    To analyze this data, we utilize Jetstream2, a cloud computing resource. The pipeline processes raw data files into intermediate data files by breaking 30-minute audio recordings into 30-second segments for model input. The data remains in .wav format, compatible with models such as **BatDetect2**, **BirdNET-Analyzer**, **BuzzFindr**, and **Batty-BirdNET**, which generate .csv outputs for further analysis and visualization.  

    The project’s primary challenge is ensuring proper authentication and permissions between Jetstream2 and OSN for seamless data access and implementing automated pipeline triggers for new data uploads. Ultimately, the processed data will be accessible via a client-facing web portal, enhancing data-driven research and community engagement.
    """)

elif page == "models":
    st.title("EcoAcoustic Pipeline Model Integration ")
    st.markdown("""
    The EcoAcoustic pipeline integrates multiple specialized models to detect and identify multiple species (bats, birds, frogs) from audio recordings. Our pipeline includes the following models:
    
    - **[BatDetect2](https://github.com/macaodha/batdetect2)**: A deep learning-based bat call detection pipeline that automatically detects and classifies bat echolocation calls in high-frequency recordings. By pinpointing true bat call events, it improves the accuracy of downstream bat species identification in noisy field recordings.
    
    - **[Batty-BirdNET-Analyzer](https://github.com/rdz-oss/BattyBirdNET-Analyzer)**: A BirdNET-based classifier retrained on ultrasonic bat recordings (e.g. 256 kHz sampling) to identify bat species. It classifies bat call segments (as detected by BatDetect2) using BirdNET’s deep neural network architecture adapted for echolocation calls, enabling automated bat call classification.
    
    - **[BirdNET-Analyzer](https://github.com/birdnet-team/BirdNET-Analyzer)**: An open-source tool that recognizes and classifies bird vocalizations using deep neural networks. It processes audible frequency audio to identify bird species present by their calls, allowing simultaneous avian biodiversity monitoring within the pipeline.
    
    - **Custom Frog Model**: A BirdNET-derived acoustic model trained specifically on Washington frog calls to enhance amphibian call identification in the Union Bay Seattle area. Using the BirdNET framework (originally for ~984 bird species) extended to include frog species, this model detects and classifies frog vocalizations, adding anuran amphibians to the multi-species analysis.
    
    - **[Buzzfindr](https://github.com/joelwjameson/buzzfindr)**: An automated detector for bat feeding buzzes – the rapid sequence of pulses bats emit during the final stage of insect prey capture. Buzzfindr flags these feeding buzz events in the recordings, providing behavioral insights into bat foraging activity and aiding habitat use analysis.
    
    Together, these models operate in concert as an integrated pipeline, each focusing on specific taxa or acoustic behaviors. This allows the system to concurrently monitor bats, birds, and frogs from the same acoustic data, contributing to comprehensive, multi-species biodiversity assessments through passive acoustic analysis.
    """)


elif page == "dashboard":
    st.title("📊 Dashboard")

    # Path to the Manila storage folder
    MANILA_STORAGE_PATH = "/ecoacoustic-storage"

    st.title("📂 Manila Storage Browser")

    # Check if the Manila storage path exists
    if os.path.exists(MANILA_STORAGE_PATH):
        st.write("✅ Manila storage is detected.")

        all_items = os.listdir(MANILA_STORAGE_PATH)

        # Separate directories
        directories = [d for d in all_items if os.path.isdir(os.path.join(MANILA_STORAGE_PATH, d))]

        # Display Directories Dropdown
        if directories:
            selected_directory = st.selectbox("📂 Select a Directory:", directories)

            # Show contents of the selected directory
            dir_path = os.path.join(MANILA_STORAGE_PATH, selected_directory)
            dir_contents = os.listdir(dir_path)

            # Separate files and PNGs within the selected directory
            data_files = [f for f in dir_contents if f.endswith((".csv", ".xls", ".xlsx", ".txt"))]
            png_files = [f for f in dir_contents if f.endswith(".png")]

            # Display Data Files Dropdown
            if data_files:

                # Combine data for the selected directory
                combined_df, activity_df = combine_dataframes(dir_path)

                selected_file = st.selectbox("📑 Select a Data File:", data_files)
                file_path = os.path.join(dir_path, selected_file)

                # Display Data File Content
                with open(file_path, "rb") as f:
                    st.download_button(label="⬇️ Download File", data=f, file_name=selected_file)

                # CSV Preview
                if selected_file.endswith(".csv"):
                    df = safe_read_csv(file_path)
                    st.write("### 📊 CSV Preview")
                    st.dataframe(df)

                
                # Excel Preview
                elif selected_file.endswith(('.xls', '.xlsx')):
                    df = pd.read_excel(file_path)
                    st.write("### 📊 Excel Preview")
                    st.dataframe(df)

                # Text File Preview
                elif selected_file.endswith(".txt"):
                    st.write("### 📜 Text File Preview")
                    with open(file_path, "r", encoding="utf-8") as f:
                        text_content = f.read()
                        st.text_area("📄 File Contents", text_content, height=300)

                
                # Print Summary Statistics
                display_summary_statistics(combined_df)

                # Display aggregated table before heatmap
                st.write("### Aggregated Activity Table")
                st.dataframe(activity_df)
            
                # Plot the combined activity chart
                st.write("### EcoAcoustic Activity Heatmap")
                combined_activity_chart(activity_df)
            
            else:
                st.info("📂 No data files found in this directory.")

            # Display PNG Files Dropdown
            if png_files:
                selected_png = st.selectbox("🖼️ Select a PNG File:", png_files)
                png_path = os.path.join(dir_path, selected_png)
                st.image(png_path, caption=selected_png, use_container_width=True)
            else:
                st.info("🖼️ No PNG images found in this directory.")
        else:
            st.warning("⚠️ No directories found in Manila storage.")
    else:
        st.error("🚫 Manila storage path does not exist. Make sure it is mounted correctly.")


elif page == "contact":
    st.title("Meet the Team:")
    st.markdown("""
    **Isha Gokhale**
    has experience as a Graduate Research Assistant at the University of Washington's Genomics Department, where she contributed to enhancing a peptide sequencing model by detecting chimeric spectra through signal processing analysis. She also worked as a Data Science Intern at Qualtrics, utilizing Athena and Redshift to query large databases and analyze user behaviors related to value achievement. Additionally, Isha interned at Conversica, where she trained and analyzed transformer and LSTM models to detect client churn. She is skilled in data analysis, machine learning, and the development of predictive models. Isha is passionate about applying her technical expertise to solve real-world problems and optimize business outcomes through data-driven insights. Her professional interests include building end-to-end data pipelines, ETL processes, and applying machine learning techniques to large-scale datasets.
    
    **Lawrie Brunswick**
    has a Master’s of Science in Data Science with over nine years of experience in programming and analytics. Lawrie has held roles such as: Data Science Trainee in the genomics Department at the University of Washington, Senior Data Analyst at the American Institutes for Research, and Senior Reporting Analyst at Optum Inc. She has built CI/CD pipelines, conducted detailed statistical analyses, and created visual reports for executive decision-making. Her skills include ML model training using Cellpose for nuclear segmentation and stereo-seq analysis for spatial transcriptomics, utilizing tools like TensorFlow and PyTorch. Lawrie is proficient in Python, R, SQL, SAS, and C++, with experience in big data environments like Hadoop, Teradata, and cluster computing via Sun Grid Engine. She has applied a range of statistical techniques, including regression, ANOVA, and factor analysis. Her strong data manipulation and automation skills have been vital to her success. Through her extensive experience in healthcare and biological research, Lawrie is eager to explore new industries and to expand skills in machine learning, deep learning, and AI.

    **Jacob Peterson**
    is a skilled data science student with experience in statistical analysis, machine learning, and data analytics. He works at the Port of Seattle, where he applies predictive modeling, providing critical insights for operational planning. This role involved building and refining data pipelines and dashboards in collaboration with the business intelligence team to optimize data-driven decision-making processes. Proficient in Python, SQL, and predictive analytics, Jacob excels at developing scalable data systems and impactful visualizations. He is particularly interested in healthcare, AI, and cloud computing, with a focus on leveraging LLMs, machine learning algorithms, and data pipelines to drive innovation in tech and business intelligence.

    """)
    st.write("For questions, feedback, or to report issues, please visit our [**GitHub Issues page**](https://github.com/uw-echospace/EcoAcousticAI/issues) to connect with the team directly.")

else:
    st.write("Page not found. Please use the navigation links above.")

