import os
import streamlit as st
import pandas as pd

# Path to the Manila storage folder
MANILA_STORAGE_PATH = "/mnt/manila"

st.title("📂 Manila Storage File Browser")

# Check if the Manila storage path exists
if os.path.exists(MANILA_STORAGE_PATH):
    files = [f for f in os.listdir(MANILA_STORAGE_PATH) if os.path.isfile(os.path.join(MANILA_STORAGE_PATH, f))]

    if files:
        selected_file = st.selectbox("📑 Select a file:", files)

        file_path = os.path.join(MANILA_STORAGE_PATH, selected_file)

        # Allow file download
        with open(file_path, "rb") as f:
            st.download_button(label="⬇️ Download File", data=f, file_name=selected_file)

        # Display CSV or Excel content
        if selected_file.endswith(".csv"):
            df = pd.read_csv(file_path)
            st.write("### 📊 CSV Preview")
            st.dataframe(df)

        elif selected_file.endswith((".xls", ".xlsx")):
            df = pd.read_excel(file_path)
            st.write("### 📊 Excel Preview")
            st.dataframe(df)

        elif selected_file.endswith((".xls", ".xlsx")):
            df = pd.read_excel(file_path)
            st.write("### 📊 Excel Preview")
            st.dataframe(df)

        elif selected_file.endswith(".txt"):
            st.write("### 📜 Text File Preview")
            with open(file_path, "r", encoding="utf-8") as f:
                text_content = f.read()
                st.text_area("📄 File Contents", text_content, height=300)

        else:
            st.write("📎 Selected file is not a CSV or Excel file. Download it to view.")

    else:
        st.warning("⚠️ No files found in Manila storage.")

else:
    st.error("🚫 Manila storage path does not exist. Make sure it is mounted correctly.")
