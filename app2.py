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

    MANILA_STORAGE_PATH = "/ecoacoustic-storage"
    st.title("📂 Manila Storage Browser")

    if os.path.exists(MANILA_STORAGE_PATH):
        st.write("Manila storage is detected.")

        all_items = os.listdir(MANILA_STORAGE_PATH)
        directories = [d for d in all_items if os.path.isdir(os.path.join(MANILA_STORAGE_PATH, d))]

        if directories:
            selected_directory = st.selectbox("📂 Select a Date Directory:", directories)
            dir_path = os.path.join(MANILA_STORAGE_PATH, selected_directory)
            model_list = ["frognet", "battybirdnet", "batdetect2", "buzzfindr"]
            selected_model = st.selectbox("🤖 Select a Model:", model_list)

            # Combine path with the selected model
            model_path = os.path.join(dir_path, selected_model)

            if os.path.exists(model_path):
                dir_contents = os.listdir(model_path)

                data_files = [f for f in dir_contents if f.endswith(('.csv', '.xls', '.xlsx', '.txt'))]
                combined_df, activity_df = combine_dataframes(model_path)

                if data_files:
                    selected_file = st.selectbox("📑 Select a Data File:", data_files)
                    file_path = os.path.join(model_path, selected_file)

                    with open(file_path, "rb") as f:
                        st.download_button(label="⬇️ Download File", data=f, file_name=selected_file)

                    if selected_file.endswith(".csv"):
                        df = safe_read_csv(file_path)
                        st.write("### 📊 CSV Preview")
                        st.dataframe(df)

                    elif selected_file.endswith(('.xls', '.xlsx')):
                        df = pd.read_excel(file_path)
                        st.write("### 📊 Excel Preview")
                        st.dataframe(df)

                    elif selected_file.endswith(".txt"):
                        st.write("### 📜 Text File Preview")
                        with open(file_path, "r", encoding="utf-8") as f:
                            text_content = f.read()
                            st.text_area("📄 File Contents", text_content, height=300)

                    display_summary_statistics(combined_df)
                    st.write("### Aggregated Activity Table")
                    st.dataframe(activity_df)
                    st.write("### EcoAcoustic Activity Heatmap")
                    combined_activity_chart(activity_df)
                else:
                    st.info("📂 No data files found in this directory.")

            # Handle activity_plot PNG files
            activity_plot_path = os.path.join(dir_path, "activity_plot")
            if os.path.exists(activity_plot_path):
                png_files = [f for f in os.listdir(activity_plot_path) if f.endswith(".png")]
                if png_files:
                    selected_png = st.selectbox("🖼️ Select an Activity Plot:", png_files)
                    png_path = os.path.join(activity_plot_path, selected_png)
                    st.image(png_path, caption=selected_png, use_container_width=True)
                else:
                    st.info("🖼️ No PNG images found in this directory.")
        else:
            st.warning("⚠️ No directories found in Manila storage.")
    else:
        st.error("🚫 Manila storage path does not exist. Make sure it is mounted correctly.")


elif page == "contact":

    st.title("Meet the Team:")
    
    # Custom CSS for sleek design
    st.markdown("""
        <style>
            .team-container {
                display: flex;
                justify-content: center;
                gap: 30px;
                flex-wrap: wrap;
            }
    
            .team-card {
                position: relative;
                width: 200px;
                height: 200px;
                border-radius: 15px;
                overflow: hidden;
                cursor: pointer;
                transition: transform 0.3s ease-in-out, box-shadow 0.3s ease-in-out;
                box-shadow: 2px 2px 10px rgba(0, 0, 0, 0.2);
            }
    
            .team-card:hover {
                transform: scale(1.05);
                box-shadow: 4px 4px 20px rgba(0, 0, 0, 0.3);
            }
    
            .team-card img {
                width: 100%;
                height: 100%;
                object-fit: cover;
                border-radius: 15px;
            }
    
            .team-overlay {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.6);
                display: flex;
                align-items: center;
                justify-content: center;
                color: #fff;
                font-size: 18px;
                font-weight: bold;
                opacity: 0;
                transition: opacity 0.3s ease-in-out;
            }
    
            .team-card:hover .team-overlay {
                opacity: 1;
            }
    
            .bio-container {
                margin-top: 30px;
                padding: 20px;
                background-color: #f9f9f9;
                border-left: 5px solid #4CAF50;
                border-radius: 10px;
                box-shadow: 2px 2px 10px rgba(0, 0, 0, 0.1);
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Team Members Data
    team_members = [
        {
            "name": "Isha Gokhale",
            "image": "./assets/isha.png",
            "bio": """Isha has experience as a Graduate Research Assistant at the University of Washington's Genomics Department..."""
        },
        {
            "name": "Lawrie Brunswick",
            "image": "./assets/lawrie.png",
            "bio": """Lawrie has a Master’s of Science in Data Science with over nine years of experience in programming and analytics..."""
        },
        {
            "name": "Jacob Peterson",
            "image": "./assets/jacob.png",
            "bio": """Jacob is a skilled data science student with experience in statistical analysis, machine learning, and data analytics..."""
        }
    ]
    
    # Display Team Section
    st.title("Meet the Team")
    selected_member = st.session_state.get('selected_member', None)
    
    # Row of Team Members
    st.markdown('<div class="team-container">', unsafe_allow_html=True)
    for idx, member in enumerate(team_members):
        col1, col2 = st.columns([1, 3])  # Image on the left, text on the right
        
        with col1:
            st.image(member["image"], use_column_width=True, caption=f"{member['name']}")
    
        with col2:
            if st.button(f"More About {member['name']}", key=f"bio_{idx}"):
                st.markdown(f'<div class="bio-container">', unsafe_allow_html=True)
                st.markdown(f"### {member['name']}")
                st.markdown(member['bio'])
                st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
            
    st.markdown("""

    \n\t *placeholder for sponser acknowledgment*
    """)
    st.write("\n\n\n For questions, feedback, or to report issues, please visit our [**GitHub Issues page**](https://github.com/uw-echospace/EcoAcousticAI/issues) to connect with the team directly.")

else:
    st.write("Page not found. Please use the navigation links above.")

