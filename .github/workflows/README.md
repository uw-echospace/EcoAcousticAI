# Github Actions Workflows

## Parallel Model Run (parallel_wf.yml)

This workflow automates instance management and data processing in the **EcoAcousticAI** pipeline. It contains two jobs performing the following key actions:

### **Schedule and Trigger Conditions**
- **Scheduled Automation:**  
  - **Unshelve instance** on **Sunday at 12 AM PT**  
  - **Shelve instance** on **Sunday at 8 PM PT**  
- **Manual Trigger:** Supports manual execution through `workflow_dispatch`.

### **Key Steps**
### Job 1: Unshelve and Ready Instance
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

7. **Run Script to Detect New Data in OSN Bucket**
   - Runs `new_data1.py` to detect whether any new files have been added to the OSN Bucket.
   - If no new data has been added, the job errors out through `sys.exit(1)` and triggers the shleve-instance job located in the same workflow. However, if new data is detected, the following steps occur.

8. **Mount Manila Storage**  
   - Connects persistent storage in Manila to manage result files.
   - Build docker images for each model. The birdnet and frognet models are contained in one docker image because they both stem from the same birdNET model and share underlying code in the repository. 

9. **Run Models in Docker**  
   There are separate jobs within the workflow to run each model in its docker container in parallel:
   - **BuzzFindr** — Identifies rapid sequences in bat echolocation indicative of feeding behavior.
   - **BirdNet** - Detects bird vocalizations using deep learning model.  
   - **FrogNet** — Adapts BirdNET to detect frog vocalizations.
   - **BatDetect** — Uses a deep neural network to classify bat echolocation.  

### Job 2: Shelve the Instance
   - Scheduled to start 20 hours after the unshelve instance job starts to give models adequate time to run. OR it is triggered if the first job fails (whether the pipeline broke or no new data was detected).
   - Install the OpenStack client to manage the Jetstream2 instance.
   - Uses credentials stored in GitHub Secrets to authenticate.
   - Monitors the instance status to ensure it’s no longer in a **transitioning state** (e.g., `BUILD`, `REBOOT`, `UNSHELVING`).  
   - If the instance is in `ACTIVE` status, it proceeds to shelve it.  
   - If the instance is **not ready** for shelving, it provides a status update.

---

This automated process ensures efficient model execution, storage management, and consistent updates to the data pipeline and ensures the instance is properly shelved to conserve resources.


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









