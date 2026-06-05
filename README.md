# SolvPred_App

SolvPred_App is the **code-free desktop GUI** for SolvPred (co-solvent prediction using Hansen Solubility Parameters).

This repo is intended to provide a **step-wise, modern, coding-free and user-friendly workflow** of SolvPred.

To download SolvPred App, go to your desired directory, using git to clone this repo:

`git clone https://github.com/xueannafang/SolvPred_App.git`

To prepare the envirnoenment with `conda`:

`conda env create --file environment.yml`.

Use `python run_app.py` to launch.

Alternatively, to install app with an executable using `pyinstaller`:

 `pyinstaller --onefile --name=SolvPredApp --add-data "app/data;app/data" --add-data "app/assets;app/assets" --collect-all numpy run_app.py`

---

## User Workflow (Step-wise)

1. **Home / Start**
   - Brief instructions and what inputs are needed.
2. **Select Solvents**
   - Search by **CAS** or **Name**
   - Quick actions: **Select All**, **Select Default List**
   - Review/remove selected solvents
3. **Input Target HSP + Parameters**
   - Target: δD / δP / δH
   - Acceptable errors: errD / errP / errH
   - Redundant solvent threshold
   - Advanced options: working temperature, perturbation parameters, number of co-solvents
4. **Run Calculation**
   - Progress indicator + cancellation (future)
5. **Results Review**
   - Show valid combinations
   - Highlight “best” combination
   - Export results to TXT/CSV/JSON
6. **Advanced Filtering**
   - Label/sort by boiling point + miscibility where available
   - Export advanced filter report
