# Github Actions Workflows

## Part 1 of the Workflow 

This workflow automates instance management and data processing in the **EcoAcousticAI** pipeline. It performs the following key actions:

### **Schedule and Trigger Conditions**
- **Scheduled Automation:**  
  - **Unshelve instance** on **Monday at 8 AM PT**  
  - **Shelve instance** on **Tuesday at 6 PM PT**  
- **Manual Trigger:** Supports manual execution through `workflow_dispatch`.

### **Key Steps**
1. **Install OpenStack CLI**  
   - Installs the OpenStack CLI to manage Jetstream2 instances.

2. **Authenticate with OpenStack**  
   - Uses credentials stored in GitHub Secrets to authenticate.

3. **Unshelve the Instance**  
   - Ensures the instance is active before running models.  
   - Waits for the instance to reach `ACTIVE` state.

4. **Start the Instance**  
   - Starts the instance if it’s not already active.

5. **Set Up SSH Key**  
   - Configures a secure SSH key to connect remotely.

6. **Mount OSN Storage**  
   - Mounts the OSN bucket using `rclone` for data synchronization.

7. **Mount Manila Storage**  
   - Connects persistent storage in Manila to manage result files.

8. **Run Models in Docker**  
   The workflow executes the following models:
   - **BuzzFindr** — Identifies rapid sequences in bat echolocation indicative of feeding behavior.
   - **FrogNet** — Adapts BirdNET to detect frog vocalizations.
   - **BatDetect** — Uses a deep neural network to classify bat echolocation.

This automated process ensures efficient model execution, storage management, and consistent updates to the data pipeline. 

## **Model Run Part 2 (Resume)**

This workflow is designed to **resume model execution** following the completion of the **Model Run to Manila Mount** workflow. It can also be triggered manually via `workflow_dispatch`.

### **Trigger Conditions**
- **Automatic Trigger:** Runs immediately after the **Model Run to Manila Mount** workflow is completed.
- **Manual Trigger:** Can be initiated manually if needed.

### **Key Steps**
1. **Set up SSH Key for Remote Access**  
   - Configures an SSH key to securely connect to the Jetstream2 instance.

2. **Resume Model Run**  
   - Establishes an SSH connection to the instance.  
   - Navigates to the `EcoAcousticAI` directory.  
   - Displays the contents of `new_directories.txt` to confirm new data paths.  
   - Executes the script:
   - **`run_docker_part2.sh`** — Continues bat detection and related model processes.

---

This workflow ensures seamless continuation of the data pipeline by automatically handling the next steps after the initial model run which is needed since Github Actions can only run for 6 hours. Some models such as batdetect2 can take longer than 6 hours to run depending on how many files are ran at once.

## **Model Run Part 3 (Resume)**

This workflow handles the **final stage** of the model pipeline, resuming processing from Part 2 and shelving the Jetstream2 instance when completed. It can also be triggered manually via `workflow_dispatch`.

### **Trigger Conditions**
- **Automatic Trigger:** Runs immediately after the **Model Run Part 2 (Resume)** workflow is completed.
- **Manual Trigger:** Can be initiated manually if needed.

---

### **Key Steps**
1. **Set up SSH Key for Remote Access**  
   - Configures an SSH key for secure access to the Jetstream2 instance.

2. **Resume Model Run**  
   - Establishes an SSH connection to the instance.  
   - Navigates to the `EcoAcousticAI` directory.  
   - Displays the contents of `new_directories.txt` to confirm new data paths.  
   - Executes the script:
   - **`run_docker_part3.sh`** — Completes bat detection and final model processing.  
   - **Removes** `new_directories.txt` to clean up the workspace.  
   - **Unmounts** `/tmp/osn_bucket/` to safely detach the mounted storage.

---

### **Shelve the Instance**
3. **Install OpenStack CLI**  
   - Installs the OpenStack client to manage the Jetstream2 instance.

4. **Authenticate with OpenStack**  
   - Uses credentials stored in GitHub Secrets to authenticate.

5. **Shelve the Instance**  
   - Monitors the instance status to ensure it’s no longer in a **transitioning state** (e.g., `BUILD`, `REBOOT`, `UNSHELVING`).  
   - If the instance is in `ACTIVE` status, it proceeds to shelve it.  
   - If the instance is **not ready** for shelving, it provides a status update.

---

This workflow is the last of the main pipeline and ensures the instance is properly shelved to conserve resources.


## **Organize Manila Files**

This workflow is designed to **clean up and organize output files** in the Manila storage system. It is independent of the main pipeline but runs on a regular schedule to maintain file structure and improve storage management.

### **Trigger Conditions**
- **Scheduled Automation:** Runs **daily at midnight UTC**.
- **Manual Trigger:** Can be executed manually via `workflow_dispatch`.

---

### **Key Steps**
1. **Checkout Repository**  
   - Retrieves the latest version of the repository from GitHub.

2. **Set up Python Environment**  
   - Configures Python **3.10** for running the cleanup script.  
   - The dependency installation step is commented out but can be activated if needed.

3. **SSH into Jetstream2 and Run Script**  
   - Establishes an SSH connection to the Jetstream2 instance.  
   - Activates the virtual environment.  
   - Executes the **`move_manila_files.py`** script, which organizes the Manila storage output.

---

This workflow helps maintain an organized folder structure by automatically moving and managing files in the Manila storage system for Streamlit app directory structure.

## **Sync Selected Files from BattyBirdNET-Analyzer**

This workflow is designed to **sync selected files** from the **BattyBirdNET-Analyzer** repository to the **EcoAcousticAI** repository. It keeps essential files updated on a scheduled basis or when triggered manually.

### **Trigger Conditions**
- **Scheduled Automation:** Runs **every Monday at midnight UTC**.
- **Manual Trigger:** Can be executed manually via `workflow_dispatch`.

---

### **Key Steps**
1. **Checkout EcoAcousticAI Repository**  
   - Clones the EcoAcousticAI repository using the provided GitHub token.

2. **Ensure Clean Clone in a Temporary Directory**  
   - Ensures a clean environment by removing any pre-existing `/tmp/battybirdnet_clone/`.  
   - Clones the **BattyBirdNET-Analyzer** repository.  
   - Adds the upstream repository to pull in updates.  
   - Merges the latest updates from the upstream repository’s `main` branch.  
   - Pushes the merged changes back to the EcoAcousticAI fork using the provided `PAT_TOKEN`.

3. **Copy Selected Files and Folders**  
   The following files and folders are copied into `BattyBirdNET-Analyzer/`:
   - **`checkpoints/`**
   - **`labels/`**
   - **`put-your-files-here/`**
   - **`audio.py`**
   - **`bat_ident.py`**
   - **`config.py`**
   - **`model.py`**
   - **`species.py`**
   - **`utils.py`**

4. **Set Git User Info**  
   - Configures GitHub Actions with a bot username and email for automated commits.

5. **Commit and Push Changes**  
   - Adds the copied files to the staging area.  
   - Commits the changes with the message:  
     _"Automated sync of selected files from BattyBirdNET-Analyzer"_  
   - Pushes changes back to the repository unless no changes are detected.

---

This workflow ensures selected BattyBirdNET-Analyzer files remain updated within the EcoAcousticAI project to maintain synchronization across repositories.









