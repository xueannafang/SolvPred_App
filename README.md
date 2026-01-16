# SolvPred_App

SolvPred_App is the **code-free desktop GUI** for SolvPred (co-solvent prediction using Hansen Solubility Parameters).

This repo is intended to provide a **step-wise, modern, user-friendly workflow** analogous to the existing `SolvPred_Web` prototype, but as a standalone app that is easier to distribute and extend.

---

## Planned User Workflow (Step-wise)

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

---

## Architecture (GUI-Friendly, Future-Proof)

Recommended layering:

- **UI layer (Views / Pages)**: step screens, widgets, theming
- **ViewModel / Controller layer**: state machine for steps, validation, commands
- **Service layer**:
  - `SolventRepository`: loads solvent DB + default list
  - `CalculationService`: calls the existing model/algorithm without UI coupling
  - `ExportService`: saves results/reports
- **Model layer (existing)**: algorithm + data structures (keep unchanged unless bugs)

Key goals:
- No algorithm logic inside UI code
- State is centralized (selected solvents, HSP params, results)
- Easy to add new steps later (e.g., “Constraints”, “Feasibility checks”, “Visualization”)

---

## Data Sources (expected)

- Solvent DB JSON (CAS, Name, HSP components, miscibility/boiling point metadata if present)
- Default solvent candidate list JSON

(Exact file locations will be wired once the repository structure is finalized.)

---

## Next Implementation Steps

- [ ] Add app entrypoint + GUI framework scaffold (multi-page wizard)
- [ ] Implement Solvent selection page (search/filter + selected list)
- [ ] Implement HSP/params page (validation + advanced options)
- [ ] Integrate calculation service (calls existing algorithm)
- [ ] Implement results viewer + export
- [ ] Implement advanced filtering page + export

---

## Notes

- The existing `SolvPred_Web` project is used only as a **reference for UX and workflow**.
- This desktop app should remain modular to support future features (plots, mixture ranking, templates, saved sessions).
