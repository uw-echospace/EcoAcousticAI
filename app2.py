import os
import streamlit as st
import pandas as pd

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
    st.title("🤖 Models")
    st.write("Our models include:")
    st.markdown("""
    - **Buzzfindr**: Insect sound detection
    - **BatDetect2**: Advanced bat call identification
    - **Batty-BirdNET**: Bird and bat detection model
    - **BirdNET-Analyzer**: Bird call analysis with fine-grain accuracy
    """)

elif page == "dashboard":
    st.title("📊 Dashboard")

    # Path to the Manila storage folder
    MANILA_STORAGE_PATH = "/mnt/ecoacoustic-storage"

    st.title("📂 Manila Storage File Browser")

    # Check if the Manila storage path exists
    if os.path.exists(MANILA_STORAGE_PATH):
        st.write("✅ Manila storage is detected.")

        all_items = os.listdir(MANILA_STORAGE_PATH)
        files = [f for f in all_items if os.path.isfile(os.path.join(MANILA_STORAGE_PATH, f))]

        if files:
            selected_file = st.selectbox("📑 Select a file:", files, index=0)
            file_path = os.path.join(MANILA_STORAGE_PATH, selected_file)

            with open(file_path, "rb") as f:
                st.download_button(label="⬇️ Download File", data=f, file_name=selected_file)

            if selected_file.endswith(".csv"):
                df = pd.read_csv(file_path)
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

            else:
                st.warning("⚠️ Selected file is not a supported format for preview. Download it to view.")
        else:
            st.warning("⚠️ No files found in Manila storage.")

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

