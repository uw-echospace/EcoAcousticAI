import os
import streamlit as st
import pandas as pd
import numpy as np
import base64
from PIL import Image 
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(layout="wide")


# Function to extract datetime from filename - Added for activity plot
def extract_datetime_from_filename(filename):
    """Extracts datetime from a filename in format: '*_20210603_034102.csv'"""
    try:
        filename = os.path.splitext(filename)[0]
        parts = filename.split('_')
        
        # Identify the position of the date-time
        for part in parts:

            # Extract only numeric characters
            numeric_part = ''.join(filter(str.isdigit, part))
            
            if len(numeric_part) == 8:  # Date in YYYYMMDD format
                date_str = numeric_part
            if len(numeric_part) == 6:  # Time in HHMMSS format
                time_str = numeric_part
                break  # Stop once both date and time are found

        # Parse date and time
        file_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y%m%d %H%M%S")
        return file_datetime
 
    except (IndexError, ValueError):
        st.error("Filename format incorrect. Expected format: *_YYYYMMDD_HHMMSS.csv")
        return None
        
# Function to safely read CSV files
def safe_read_csv(file_path):
    """Attempts to read a CSV file, skipping empty or invalid ones."""
    try:
        if os.stat(file_path).st_size == 0:  # Check if file is empty
            #st.warning(f"Skipping empty file: {file_path}")
            return None

        df = pd.read_csv(file_path)

        if df.empty:
            #st.warning(f"Skipping file with no data: {file_path}")
            return None
            
        # Dynamically rename any column containing 'start' to 'start_time' (same for end_time)
        df.rename(columns={col: 'start_time' for col in df.columns if 'start' in col.lower()}, inplace=True)
        df.rename(columns={col: 'end_time' for col in df.columns if 'end' in col.lower()}, inplace=True)
        # Dynamically rename any column containing 'prob' or 'confidence' to 'confidence'
        df.rename(columns={col: 'confidence' for col in df.columns if any(x in col.lower() for x in ['prob', 'confidence'])}, inplace=True)


        # Rename columns containing 'scientific' or == 'class' to 'species'
        df.rename(columns={col: 'species' for col in df.columns if 'scientific' in col.lower() or col.lower() == 'class'}, inplace=True)
        
        if 'buzz' in df.columns:
            df.rename(columns={'buzz': 'event'}, inplace=True)
            
        return df
        
    except pd.errors.EmptyDataError:
        st.warning(f"Skipping corrupted file: {file_path}")
        return None
    except Exception as e:
        st.error(f"Error reading file {file_path}: {e}")
        return None
        
def combine_dataframes(manila_path):
    combined_data = []

    for root, _, files in os.walk(manila_path):
        # Now we ensure the root path has the model folder structure
        if any(model in root for model in ["frognet", "battybirdnet", "batdetect2", "buzzfindr"]):
            for file in files:
                if file.endswith(".csv"):
                    file_path = os.path.join(root, file)
                    file_datetime = extract_datetime_from_filename(file)

                    if file_datetime:
                        df = safe_read_csv(file_path)
                        if df is None:
                            continue  # Skip empty/invalid files

                        # Convert start & end times
                        if 'start_time' in df.columns:
                            df['start_time'] = df['start_time'].apply(lambda x: file_datetime + timedelta(seconds=x))
                            # Compute species count per interval
                            if 'species' in df.columns:
                                df['species_count'] = df.groupby('start_time')['species'].transform('nunique')
                            if 'event' in df.columns:
                                df['event_count'] = df.groupby('start_time')['event'].transform('nunique')
                                
                        if 'end_time' in df.columns:
                            df['end_time'] = df['end_time'].apply(lambda x: file_datetime + timedelta(seconds=x))

                        combined_data.append(df)
                    
    if combined_data:

        # Filter out empty dataframes before concatenation
        combined_data = [df for df in combined_data if not df.empty]
    
        combined_df = pd.concat(combined_data, ignore_index=True)

        # Convert 'start_time' to DatetimeIndex
        combined_df['start_time'] = pd.to_datetime(combined_df['start_time'])
        combined_df = combined_df.set_index('start_time')  # Set 'start_time' as the index

        if 'species' in combined_df.columns:
            # Resample to 10-minute intervals
            activity_df = (
                combined_df[['species_count', 'species', 'confidence']]
                .drop_duplicates()
                .resample('10min')  # Resample to 10min intervals
                .agg({
                    'species_count': 'sum',  # Sum species count per 10-minute interval
                    'species': lambda x: x.mode().iloc[0] if not x.mode().empty else None,  # Most common valid species
                    'confidence': 'mean'  # Average confidence for the interval
                })
            )

        if 'event' in combined_df.columns:
            # Resample to 10-minute intervals
            activity_df = (
                combined_df[['species_count', 'species', 'confidence']]
                .drop_duplicates()
                .resample('10min')  # Resample to 10min intervals
                .agg({
                    'event_count': 'sum',  # Sum species count per 10-minute interval
                    'event': lambda x: x.mode().iloc[0] if not x.mode().empty else None,  # Most common valid species
                    'confidence': 'mean'  # Average confidence for the interval
                })
            )

        if 'species' in activity_df.columns:
            # Replace remaining invalid or empty 'class' values with NaN
            activity_df['species'] = activity_df['species'].replace({0: None, '0': None, 'No Data': None})
    
            # Add a new column for plotting, e.g., filling missing intervals with zero values
            activity_df['heatmap_value'] = activity_df['species_count'].fillna(0)
    
            # Final cleanup for invalid or empty rows
            activity_df = activity_df.dropna(subset=['species', 'heatmap_value'], how='all')


        if 'event' in activity_df.columns:
            # Replace remaining invalid or empty 'class' values with NaN
            activity_df['event'] = activity_df['class'].replace({0: None, '0': None, 'No Data': None})
    
            # Add a new column for plotting, e.g., filling missing intervals with zero values
            activity_df['heatmap_value'] = activity_df['event_count'].fillna(0)
    
            # Final cleanup for invalid or empty rows
            activity_df = activity_df.dropna(subset=['event', 'heatmap_value'], how='all')

        
        return combined_df, activity_df
    else:
        return pd.DataFrame(), pd.DataFrame()  # Return empty DataFrame if no data found


def display_summary_statistics(combined_df):
    """Prints key statistics about the acoustic detections instead of displaying a table."""
    
    if combined_df.empty:
        #st.warning("⚠ No activity data available to summarize.")
        return

     # Print Summary
    start_date = combined_df.index.date.min()  # Extracts the earliest date in the dataset
    end_date = combined_df.index.date.max()
    st.write(f"### 📊 Summary Statistics for {start_date} - {end_date}")
    
    if 'species' in combined_df.columns:
    # 1. Count of Unique Species Detected
        unique_species = combined_df['species'].nunique()
        st.write(f"- **Total Unique Species Detected:** {unique_species}")

    
    # 2. Percentage of LF vs HF Detections
    total_detections = len(combined_df)

    if 'KMEANS_CLASSES' in combined_df.columns:
        lf_detections = len(combined_df[combined_df['KMEANS_CLASSES'] == 'LF'])
        hf_detections = len(combined_df[combined_df['KMEANS_CLASSES'] == 'HF'])
    
        lf_percentage = (lf_detections / total_detections) * 100 if total_detections > 0 else 0
        hf_percentage = (hf_detections / total_detections) * 100 if total_detections > 0 else 0
        
        st.write(f"- **Low-Frequency Detections:** {lf_percentage:.2f}%")
        st.write(f"- **High-Frequency Detections:** {hf_percentage:.2f}%")
        
    # 3. Percentage of the Day with a Detection
    detected_times = combined_df.index.floor('min').nunique()  # Unique time slots with detections
    total_time_slots = 24 * 60  # Total minutes in a day

    day_coverage = (detected_times / total_time_slots) * 100 if total_time_slots > 0 else 0
    
    st.write(f"- **% of the Day with Detections:** {day_coverage:.2f}%")

   
    


# Create the heatmap
def combined_activity_chart(activity_df):
    # Extract Time of Day
    activity_df['time_of_day'] = activity_df.index.strftime('%H:%M')

    # Ensure full 24-hour coverage
    full_time_range = pd.date_range('00:00', '23:59', freq='1min').strftime('%H:%M')
    activity_df = activity_df.reindex(full_time_range, fill_value=0)
    
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
        [0.0, '#2b0136'],    # Darkest Purple (this is the only added color so we could see a zero-value more clearly)
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
    st.title("🏡 Welcome to the EcoAcoustic AI project portal!")

    st.markdown("""
    ## Introduction
    The Union Bay Natural Area (UBNA) is an ecologically significant urban habitat in Seattle, characterized by its proximity to major highways and Lake Washington, which introduces unique soundscape complexities. This diverse environment hosts various wildlife, including birds and bats, while also being influenced by human-made noise such as traffic and recreational activities.  

    ## Project Overview
    The EcoAcoustic AI project focuses on developing a cloud-hosted automated pipeline for monitoring wildlife sounds in UBNA. Building on previous research centered around bat call detection, this project expands detection capabilities across multiple animal groups and human-generated sounds. The goal was to create a modular, scalable tool for research and community science engagement, promoting ecological awareness within the Greater Seattle area.  

    ## Data Pipeline
    Our project processes passive acoustic monitoring (PAM) data collected from UBNA using AudioMoth devices. These devices capture high-resolution audio (sampled at 192 kHz or 250 kHz), providing detailed insights into the Union Bay soundscape. Since 2021, over 65 TB of audio data has been collected and stored in NSF Open Storage Network buckets.  

    To analyze this data, we utilize Jetstream2, a cloud computing resource. The pipeline processes raw data files into intermediate data files by breaking 30-minute audio recordings into 30-second segments for model input. The data remains in .wav format, compatible with models such as **BatDetect2**, **BirdNET-Analyzer**, **BuzzFindr**, and **Batty-BirdNET**, which generate .csv outputs containing detections for further analysis and visualization.  

    The project’s primary challenge was ensuring proper authentication and permissions between Jetstream2 and OSN for seamless data access and implementing automated pipeline triggers for new data uploads. Ultimately, the processed data will be accessible via a client-facing web portal, enhancing data-driven research and community engagement.
    """)

elif page == "models":


    st.title("🌿 EcoAcoustic Pipeline Model Integration")

    # Improved CSS for better responsiveness and design
    st.markdown("""
        <style>
            .model-container {
                display: flex;
                align-items: center;
                gap: 15px; /* Space between logo and text */
                background-color: #f0f9f0; /* Light green for eco theme */
                border: 2px solid #4CAF50;
                border-radius: 10px;
                padding: 15px;
                margin-bottom: 15px;
                transition: transform 0.2s; /* Hover effect */
            }
            .model-container:hover {
                transform: scale(1.02); /* Slight zoom on hover */
            }
            .model-logo {
                width: 200px; /* Increased size for better clarity */
                height: 200px;
                border-radius: 50%;
                object-fit: contain;
                box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2); /* subtle shadow */
            }
            .model-text {
                flex: 1;
                font-family: 'Arial', sans-serif;
                color: #000 !important;
            }
            .model-title {
                font-size: 1.2em;
                color: #4CAF50;
            }
            .model-description {
                font-size: 0.95em;
                color: #333;
            }
        </style>
    """, unsafe_allow_html=True)
    

    
    st.markdown("""
    The EcoAcoustic pipeline integrates multiple specialized models to detect and identify multiple species (bats, birds, frogs) from audio recordings. Our pipeline includes the following models:    
    """)
    
    # Display each model with its logo
    models = [
        {
            "name": "BatDetect2",
            "url": "https://github.com/macaodha/batdetect2",
            "logo": "assets/batdetect2.png",
            "description": "A deep learning-based bat call detection pipeline that automatically detects and classifies bat echolocation calls in high-frequency recordings. By pinpointing true bat call events, it improves the accuracy of downstream bat species identification in noisy field recordings."
        },
        {
            "name": "Batty-BirdNET-Analyzer",
            "url": "https://github.com/rdz-oss/BattyBirdNET-Analyzer",
            "logo": "assets/battybirdnet.png",
            "description": "A BirdNET-based classifier retrained on ultrasonic bat recordings (e.g. 256 kHz sampling) to identify bat species. It classifies bat call segments (as detected by BatDetect2) using BirdNET’s deep neural network architecture adapted for echolocation calls, enabling automated bat call classification."
        },
        {
            "name": "BirdNET-Analyzer",
            "url": "https://github.com/birdnet-team/BirdNET-Analyzer",
            "logo": "assets/birdnet.png",
            "description": "An open-source tool that recognizes and classifies bird vocalizations using deep neural networks. It processes audible frequency audio to identify bird species present by their calls, allowing simultaneous avian biodiversity monitoring within the pipeline."
        },
        {
            "name": "Custom Frog Model",
            "url": "https://github.com/uw-echospace/EcoAcousticAI/tree/main/birdnetlib/frognet_model",
            "logo": "assets/frognet.png",
            "description": "A BirdNET-derived acoustic model trained specifically on Washington frog calls to enhance amphibian call identification in the Union Bay Seattle area. Using the BirdNET framework extended to include frog species, this model detects and classifies frog vocalizations, adding anuran amphibians to the multi-species analysis."
        },
        {
            "name": "Buzzfindr",
            "url": "https://github.com/joelwjameson/buzzfindr",
            "logo": "assets/buzzfindr.png",
            "description": "An automated detector for bat feeding buzzes – the rapid sequence of pulses bats emit during the final stage of insect prey capture. Buzzfindr flags these feeding buzz events in the recordings, providing behavioral insights into bat foraging activity and aiding habitat use analysis."
        }
    ]

    # Render models using base64 encoded images
    for model in models:
        with open(model['logo'], "rb") as file:
            encoded_logo = base64.b64encode(file.read()).decode()
        st.markdown(
            f"""
            <div class='model-container'>
                <img class='model-logo' src='data:image/png;base64,{encoded_logo}' alt='Logo for {model["name"]}' />
                <div class='model-text'>
                    <b><a href="{model['url']}" target="_blank">{model['name']}</a></b><br>
                    {model['description']}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        
    st.markdown("""
    Together, these models operate in concert as an integrated pipeline, each focusing on specific species or acoustic behaviors (e.g., echolocation or feeding buzzes). This allows the system to concurrently monitor bats, birds, and frogs from the same acoustic data, contributing to comprehensive, multi-species biodiversity assessments through passive acoustic analysis.
    """)


elif page == "dashboard":
    st.title("📊 Dashboard")

    MANILA_STORAGE_PATH = "/ecoacoustic-storage"
    st.title("📂 Manila Storage Browser")

    if os.path.exists(MANILA_STORAGE_PATH):
        st.write("Manila storage is detected.")

        all_items = os.listdir(MANILA_STORAGE_PATH)
        directories_8digit = [d for d in all_items if len(d) == 8 and os.path.isdir(os.path.join(MANILA_STORAGE_PATH, d))]
        directories_4digit = [d for d in all_items if len(d) == 4 and os.path.isdir(os.path.join(MANILA_STORAGE_PATH, d))]

        if directories_8digit:
            selected_directory = st.selectbox("📂 Select a Date Directory:", sorted(directories_8digit))
            dir_path = os.path.join(MANILA_STORAGE_PATH, selected_directory)

            available_models = [
                model for model in ["frognet", "battybirdnet", "batdetect2", "buzzfindr"]
                if os.path.exists(os.path.join(dir_path, model))
            ]

            if available_models:
                selected_model = st.selectbox("Select a Model:", sorted(available_models))
                model_path = os.path.join(dir_path, selected_model)

                if os.path.exists(model_path):
                    dir_contents = os.listdir(model_path)

                    data_files = [f for f in dir_contents if f.endswith(('.csv', '.xls', '.xlsx', '.txt'))]
                    combined_df, activity_df = combine_dataframes(model_path)

                    if data_files:
                        selected_file = st.selectbox("📑 Select a Data File:", sorted(data_files))
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
                    #combined_activity_chart(activity_df)
                else:
                    st.info("📂 No data files found in this directory.")


        if directories_4digit:
            selected_4digit_dir = st.selectbox("📂 Select a Cumulative Activity Directory:", sorted(directories_4digit))
            cumulative_activity_path = os.path.join(MANILA_STORAGE_PATH, selected_4digit_dir, "cumulative_activity")

            if os.path.exists(cumulative_activity_path):
                cumulative_files = [f for f in os.listdir(cumulative_activity_path) if f.endswith(".png")]
                if cumulative_files:
                    selected_cumulative_file = st.selectbox("Select a Cumulative Activity Plot:", cumulative_files)
                    cumulative_file_path = os.path.join(cumulative_activity_path, selected_cumulative_file)
                    st.image(cumulative_file_path, caption=selected_cumulative_file, use_container_width=True)
                else:
                    st.info("🖼️ No cumulative activity plots found in this directory.")
        else:
            st.warning("⚠️ No directories found in Manila storage.")
    else:
        st.error("🚫 Manila storage path does not exist. Make sure it is mounted correctly.")



elif page == "contact":

    st.title("Meet the Team:")

    # Custom CSS for justified images and reduced spacing
    st.markdown("""
        <style>
            .team-container {
            display: flex;
            align-items: center;
            gap: 15px; 
            background-color: #ffffff; /* White background for clarity */
            border: 2px solid #4CAF50;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
            transition: transform 0.2s;
        }
        .team-container:hover {
            transform: scale(1.02); 
        }
        .team-image {
            width: 350px;
            height: 350px;
            border-radius: 10px; 
            object-fit: cover;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2); 
        }
        .team-text {
            flex: 1;
            font-family: 'Arial', sans-serif;
            color: #000;
        }
        .team-title {
            font-size: 1.5em;
            color: #4CAF50;
        }
        .team-description {
            font-size: 1em;
            color: #333;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Team Members' Info and Image Paths
    team_members = [
        {
            "name": "Isha Gokhale",
            "image": "./assets/isha.png",  # path to Isha's image
            "bio": """Isha has experience as a Graduate Research Assistant at the University of Washington's Genomics Department, where she contributed to enhancing a peptide sequencing model by detecting chimeric spectra through signal processing analysis. She also worked as a Data Science Intern at Qualtrics, utilizing Athena and Redshift to query large databases and analyze user behaviors related to value achievement. Additionally, Isha interned at Conversica, where she trained and analyzed transformer and LSTM models to detect client churn. She is skilled in data analysis, machine learning, and the development of predictive models. Isha is passionate about applying her technical expertise to solve real-world problems and optimize business outcomes through data-driven insights. Her professional interests include building end-to-end data pipelines, ETL processes, and applying machine learning techniques to large-scale datasets."""
        },
        {
            "name": "Lawrie Brunswick",
            "image": "./assets/lawrie.png",  # path to Lawrie's image
            "bio": """Lawrie has a Master’s of Science in Data Science with over nine years of experience in programming and analytics. Lawrie has held roles such as: Data Science Trainee in the genomics Department at the University of Washington, Senior Data Analyst at the American Institutes for Research, and Senior Reporting Analyst at Optum Inc. She has built CI/CD pipelines, conducted detailed statistical analyses, and created visual reports for executive decision-making. Her skills include ML model training using Cellpose for nuclear segmentation and stereo-seq analysis for spatial transcriptomics, utilizing tools like TensorFlow and PyTorch. Lawrie is proficient in Python, R, SQL, SAS, and C++, with experience in big data environments like Hadoop, Teradata, and cluster computing via Sun Grid Engine. She has applied a range of statistical techniques, including regression, ANOVA, and factor analysis. Her strong data manipulation and automation skills have been vital to her success. Through her extensive experience in healthcare and biological research, Lawrie is eager to explore new industries and to expand skills in machine learning, deep learning, and AI."""
        },
        {
            "name": "Jacob Peterson",
            "image": "./assets/jacob.png",  # path to Jacob's image
            "bio": """Jacob is a skilled data science student with experience in statistical analysis, machine learning, and data analytics. He works at the Port of Seattle, where he applies predictive modeling, providing critical insights for operational planning. This role involved building and refining data pipelines and dashboards in collaboration with the business intelligence team to optimize data-driven decision-making processes. Proficient in Python, SQL, and predictive analytics, Jacob excels at developing scalable data systems and impactful visualizations. He is particularly interested in healthcare, AI, and cloud computing, with a focus on leveraging LLMs, machine learning algorithms, and data pipelines to drive innovation in tech and business intelligence."""
        }
    ]
    
    # Display Team Members
    for member in team_members:
        with open(member['image'], "rb") as file:
            encoded_image = base64.b64encode(file.read()).decode()
        st.markdown(
            f"""
            <div class='team-container'>
                <img class='team-image' src='data:image/png;base64,{encoded_image}' alt='Photo of {member["name"]}' />
                <div class='team-text'>
                    <b class='team-title'>{member['name']}</b><br>
                    <div class='team-description'>{member['bio']}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.write("")
    
    # Sponsors Acknowledgment
    st.markdown("## Sponsors:")
    
    st.markdown("""
    We extend a special thank you to our sponsors, **Wu-Jung Lee** and **Aditya Krishna**, for their invaluable mentorship. Their countless hours of guidance on the complexities of audio signal processing helped us overcome challenges and discover the best solutions every step of the way.
    
    We also acknowledge UW-Echospace for their support and collaboration. Their commitment to advancing acoustic research has been instrumental in the development and success of our project.
    """)
    
    st.write("")
    
    # References Section
    st.markdown("## References")
    st.markdown("""
    [1] Kahl, S., et al. BirdNET-Analyzer. GitHub. https://github.com/kahst/BirdNET-Analyzer.  
    [2] Zinke, R., et al. Batty-BirdNET-Analyzer. GitHub. https://github.com/rdz-oss/BattyBirdNET-Analyzer.  
    [3] Mac Aodha, O., et al. BatDetect2. GitHub. https://github.com/macaodha/batdetect2.  
    [4] Jameson, J. (n.d.). Buzzfindr. GitHub. https://github.com/joelwjameson/buzzfindr.  
    [5] Code Author of Batdetect2 Activity Pictures: Aditya Krishna, UW Echospace.
    """)
    
    st.write("")
    
    st.write(" *For questions, feedback, or to report issues, please visit our [**GitHub Issues page**](https://github.com/uw-echospace/EcoAcousticAI/issues) to connect with the team directly.* ")

else:
    st.write("Page not found. Please use the navigation links above.")

