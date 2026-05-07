"""
Checks if ROIs in the current plan receive unexpected dose levels and verifies
that they have active optimization objectives. Flags ROIs missing objectives
or with zero objective values.
"""
# Authors:
# Robert Hoggard
# Helse Møre og Romsdal HF
# Raystation 2024B

# Import RS resources
from connect import *

# Get current patient, case, plan, examination, and beamset
patient, case, plan, examination, beamset = get_current("Patient"), get_current('Case'), get_current('Plan'), get_current('Examination'), get_current('BeamSet')

# List of ROIs to check for
roi_list = [
    # For Prostata/LK
    'Bladder',
    'BowelBag',
    'CaudaEquina',
    'Rectum',
    'AnalCabal',
    'Testis_L',
    'Testis_R',
    'FemurHeadNeck_L',
    'FemurHeadNeck_R',
    'Kidney_L',
    'Kidney_R',
    'Liver',
    'PenileBulb',
    'BowelBag',
    'zBladder',
    'zBowelBag',
    'zRectum',
    'Bone',
    
    # From RSL Head and Neck CT
    'Brain',
    'Brainstem',
    'Cochlea_L',
    'Cochlea_R',
    'Esophagus',
    'Eye_L',
    'Eye_R',
    'LacrimalGland_L',
    'LacrimalGland_R',
    'Lens_L',
    'Lens_R',
    'Lung_L',
    'OpticChiasm',
    'OpticNerve_L',
    'OpticNerve_R',
    'OralCavity',
    'Parotid_L',
    'Parotid_R',
    'Pituitary',
    'SpinalCanal',
    'SpinalCord',
    'SubmandGland_L',
    'SubmandGland_R',
    'ThyroidGland',
    'Trachea',
    
    # From RSL Thorax-Abdomen CT
    'A_LAD',
    'Esophagus',
    'Heart',
    'Kidney_L',
    'Kidney_R',
    'Liver',
    'Lung_L',
    'Lung_R',
    'Pancreas',
    'SpinalCanal',
    'Spleen',
    'Sternum',
    'Stomach',
    'ThyroidGland',
    'Trachea',
    
    # From St.Olavs-Alesund Breast CT
    'A_LAD',
    'Esophagus',
    'Heart',
    'HumeralHead_L',
    'HumeralHead_R',
    'Lung_L',
    'Lung_R',
    'SpinalCanal',
    'SpinalCanalFull',
    'Sternum',
    'ThyroidGland',
    'Trachea'
]

# Retrieve existing ROIs in the patient model
existing_rois = {roi.Name for roi in case.PatientModel.RegionsOfInterest}

# Filter the roi_list to include only existing ROIs and remove duplicates
filtered_roi_list = list(set([roi_name for roi_name in roi_list if roi_name in existing_rois]))

# Get the current prescription dose
prescription = beamset.Prescription.PrimaryPrescriptionDoseReference.DoseValue

# List to store ROIs that need attention
rois_needing_attention = []

# Loop through each existing ROI to check for dose
for roi_name in filtered_roi_list:
    # Get the maximum and minimum dose statistics for the ROI
    MaxDose = plan.TreatmentCourse.TotalDose.GetDoseStatistic(RoiName=roi_name, DoseType='Max')
    MinDose = plan.TreatmentCourse.TotalDose.GetDoseStatistic(RoiName=roi_name, DoseType='Min')
    
    # Check if the MaxDose is over 30% of the prescription and MinDose is less than 94% of the prescription
    if MaxDose > 0.3 * prescription and MinDose < 0.94 * prescription:
        # Add ROI to the list if both conditions are met
        rois_needing_attention.append(roi_name)

# Check if there are optimization functions for the ROIs that need attention
objectives_found = []
objectives_zero_value = []

for roi_name in rois_needing_attention:
    for func in plan.PlanOptimizations[0].Objective.ConstituentFunctions:
        # Get the name of the ROI associated with the current optimization function
        objective_roi_name = func.ForRegionOfInterest.Name
        # print(objective_roi_name)
        # print(func.FunctionValue.FunctionValue)
        # print('')
        # Check if this ROI is in the list of ROIs needing attention
        if roi_name == objective_roi_name:
            objectives_found.append(roi_name)
            
            # Check if the objective value is 0
            if func.FunctionValue.FunctionValue == 0:
                objectives_zero_value.append(roi_name)
            break  # Stop checking further if an objective for this ROI is found

# Create a list of ROIs needing attention and without objectives
rois_without_objectives = [roi_name for roi_name in rois_needing_attention if roi_name not in objectives_found]

# Print a summary message
if rois_without_objectives or objectives_zero_value:
    print("The following ROIs may need attention:")
    for roi_name in rois_without_objectives:
        print(f"- {roi_name}: No objective function found. Please review.")
    for roi_name in objectives_zero_value:
        print(f"- {roi_name}: Objective function value is 0. Please review.")
else:
    print("All ROIs that need attention have corresponding objective functions with non-zero values.")

# The list of ROIs needing attention and without objectives
print("\nList of ROIs without objectives:", rois_without_objectives)
