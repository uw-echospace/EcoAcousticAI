import os
import streamlit as st
import pandas as pd

# Path to the Manila storage folder
MANILA_STORAGE_PATH = "/mnt/ecoacoustic-storage"

st.title("📂 Manila Storage File Browser")

# Debugging output
st.write("🔍 Checking Manila storage path:", MANILA_STORAGE_PATH)

# Check if the Manila storage path exists
if os.path.exists(MANILA_STORAGE_PATH):
    st.write("✅ Manila storage is detected.")

    # List all items in the storage path
    all_items = os.listdir(MANILA_STORAGE_PATH)
    st.write("📂 All files & folders found:", all_items)

    # Filter only files
    files = [f for f in all_items if os.path.isfile(os.path.join(MANILA_STORAGE_PATH, f))]
    
    if files:
        st.write("📑 Files found:", files)
        
        # Dropdown for file selection
        selected_file = st.selectbox("📑 Select a file:", files, index=0)

        file_path = os.path.join(MANILA_STORAGE_PATH, selected_file)

        # Allow file download
        with open(file_path, "rb") as f:
            st.download_button(label="⬇️ Download File", data=f, file_name=selected_file)

        # Display CSV, Excel, or Text File Content
        if selected_file.endswith(".csv"):
            df = pd.read_csv(file_path)
            st.write("### 📊 CSV Preview")
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
            st.warning("⚠️ Selected file is not a supported format for preview. Download it to view.")

    else:
        st.warning("⚠️ No files found in Manila storage.")

else:
    st.error("🚫 Manila storage path does not exist. Make sure it is mounted correctly.")
