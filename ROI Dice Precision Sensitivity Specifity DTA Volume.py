# Provides a user interface for calculating various statistical comparisons of ROIs in RayStation.
#
# Authors:
# Robert Hoggard
# Helse Møre og Romsdal HF
# Raystation 2024B

import tkinter as tk
from tkinter import ttk, messagebox
from connect import *

# Connect to the current RayStation case
case = get_current("Case")

def get_available_structure_sets(case):
    """
    Get a list of all available structure sets for the current case, sorted alphabetically.
    """
    structure_sets = [ss.OnExamination.Name for ss in case.PatientModel.StructureSets]
    return sorted(structure_sets)

def get_available_rois(structure_set_name):
    """
    Get a list of all available ROIs for the selected structure set, sorted alphabetically.
    """
    structure_set = next(ss for ss in case.PatientModel.StructureSets if ss.OnExamination.Name == structure_set_name)
    return sorted([roi.OfRoi.Name for roi in structure_set.RoiGeometries])

def calculate_roi_comparison(structure_set_name, roi1_name, roi2_name, compute_dta):
    """
    Calculate comparison metrics between two ROIs using RayStation's `ComparisonOfRoiGeometries` function.

    Args:
        structure_set_name (str): Name of the structure set (examination name).
        roi1_name (str): Name of the first ROI.
        roi2_name (str): Name of the second ROI.
        compute_dta (bool): Whether to compute distance-to-agreement measures.

    Returns:
        dict: Results of the ROI comparison.
    """
    structure_set = next(ss for ss in case.PatientModel.StructureSets if ss.OnExamination.Name == structure_set_name)

    comparison_results = structure_set.ComparisonOfRoiGeometries(
        RoiA=roi1_name,
        RoiB=roi2_name,
        ComputeDistanceToAgreementMeasures=compute_dta
    )
    return comparison_results

def update_roi_lists(event):
    """
    Update the ROI dropdown lists based on the selected structure set.
    """
    selected_structure_set = structure_set_dropdown.get()
    if selected_structure_set == "Select Structure Set":
        return

    # Get ROIs for the selected structure set
    roi_list = get_available_rois(selected_structure_set)
    primary_roi["values"] = roi_list
    secondary_roi["values"] = roi_list
    primary_roi.set("Select ROI")
    secondary_roi.set("Select ROI")

def calculate_and_display_comparison():
    """
    Get selected structure set and ROIs, calculate comparison metrics, and display the results.
    """
    structure_set_name = structure_set_dropdown.get()
    roi1_name = primary_roi.get()
    roi2_name = secondary_roi.get()
    compute_dta = compute_dta_var.get()

    if structure_set_name == "Select Structure Set" or roi1_name == "Select ROI" or roi2_name == "Select ROI":
        messagebox.showwarning("Input Error", "Please select a structure set and both ROIs before calculating.")
        return

    try:
        # Get the selected structure set
        structure_set = next(ss for ss in case.PatientModel.StructureSets if ss.OnExamination.Name == structure_set_name)

        # Retrieve ROI volumes
        roi1_geometry = next(roi for roi in structure_set.RoiGeometries if roi.OfRoi.Name == roi1_name)
        roi2_geometry = next(roi for roi in structure_set.RoiGeometries if roi.OfRoi.Name == roi2_name)
        roi1_volume = roi1_geometry.GetRoiVolume()  # Volume of primary ROI
        roi2_volume = roi2_geometry.GetRoiVolume()  # Volume of secondary ROI

        # Calculate comparison metrics
        results = calculate_roi_comparison(structure_set_name, roi1_name, roi2_name, compute_dta)

        # Add ROI volumes to the results
        results["\nPrimary ROI Volume (cc)"] = roi1_volume
        results["Secondary ROI Volume (cc)"] = roi2_volume

        # Format results, 1 decimal place for volume, otherwise 3
        results_text = "\n".join(
            f"{key}: {value:.1f}" if "Volume" in key else f"{key}: {value:.3f}" if isinstance(value, (float, int)) else f"{key}: {value}"
            for key, value in results.items()
        )

        # Display the results
        messagebox.showinfo("ROI Comparison Results", f"Comparison results:\n\n{results_text}")
    except Exception as e:
        print(f"Unexpected Error: {e}")  # Log error to console
        messagebox.showerror("Error", f"An error occurred: {e}")

# Create the GUI
root = tk.Tk()
root.title("ROI Comparison Tool")

# Get structure sets
structure_set_list = get_available_structure_sets(case)
structure_set_list.insert(0, "Select Structure Set")

# Dropdown for structure set selection
ttk.Label(root, text="Select Structure Set:").grid(row=0, column=0, padx=10, pady=10)
structure_set_dropdown = ttk.Combobox(root, values=structure_set_list, state="readonly", width=30)
structure_set_dropdown.grid(row=0, column=1, padx=10, pady=10)
structure_set_dropdown.current(0)
structure_set_dropdown.bind("<<ComboboxSelected>>", update_roi_lists)

# Dropdown for primary ROI
ttk.Label(root, text="Select Primary ROI:").grid(row=1, column=0, padx=10, pady=10)
primary_roi = ttk.Combobox(root, values=[], state="readonly", width=30)
primary_roi.grid(row=1, column=1, padx=10, pady=10)

# Dropdown for secondary ROI
ttk.Label(root, text="Select Secondary ROI:").grid(row=2, column=0, padx=10, pady=10)
secondary_roi = ttk.Combobox(root, values=[], state="readonly", width=30)
secondary_roi.grid(row=2, column=1, padx=10, pady=10)

# Checkbox for computing distance-to-agreement measures
compute_dta_var = tk.BooleanVar(value=False)
ttk.Checkbutton(root, text="Compute Distance-To-Agreement Measures", variable=compute_dta_var).grid(row=3, column=0, columnspan=2, pady=10)

# Calculate button
calculate_button = ttk.Button(root, text="Calculate Comparison", command=calculate_and_display_comparison)
calculate_button.grid(row=4, column=0, columnspan=2, pady=20)

# Run the GUI
root.mainloop()
