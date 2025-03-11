mport os
import streamlit as st
import pandas as pd

# Custom CSS for improved header design
st.markdown("""
    <style>
        .header-banner {
            background-color: #A8D5BA;  /* Light green for better aesthetics */
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
        <a class="nav-item" href="/?page=contact" target="_self">CONTACT</a>
    </div>
""", unsafe_allow_html=True)

# Navigation Logic
page = st.query_params.get("page", "home")

# Content for Each Page
if page == "home":
    st.title("🏡 Home")
    st.write("Welcome to the EcoAcoustic AI project portal!")
    st.write("Learn about our environmental sound detection technologies and conservation efforts.")

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
    st.title("📞 Contact")
    st.write("Meet the Team:")
    st.markdown("""
    - **Isha** - Data Scientist
    - **Jacob** - Data Scientist
    - **Lawrie** - Data Scientist
    """)
    st.write("For inquiries, reach out to us at **ecoacousticai@contact.com**.")

else:
    st.write("Page not found. Please use the navigation links above.")

