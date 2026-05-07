# ------------------------------------------------------------------------------
# Plan Complexity Analysis Script for RayStation
#
# Description:
# This script calculates various plan and beam-level complexity metrics for the
# currently loaded plan in RayStation. The metrics include:
#   - Total MU and MU per Gy
#   - Total and average MLC leaf travel
#   - Modulation Complexity Score (MCS)
#   - Edge Metric (EM)
#   - Aperture Area Variation (AAV)
#
# Each beam is evaluated individually, and MU-weighted averages are computed.
# The results are printed in both a readable format and a copy-paste friendly
# tab-separated format with Norwegian decimal formatting (comma as decimal separator).
#
# Output is suitable for direct pasting into Norwegian Excel (tab-separated columns).
#
# ------------------------------------------------------------------------------
# Authors:
# Robert Hoggard
# Helse Møre og Romsdal HF
# Raystation 2024B

from connect import *
import math
import statistics

plan = get_current("Plan")
beam_set = plan.BeamSets[0]

# --- Debug toggle ---
debug_mode = False

# --- Check beam set ---
if not beam_set.Beams:
    print("No beams found in this beam set.")
    exit()

# --- Dose prescription in Gy ---
prescription_dose_gy = beam_set.Prescription.PrimaryPrescriptionDoseReference.DoseValue / 100

# --- Total MU ---
total_mu = sum(beam.BeamMU for beam in beam_set.Beams)

# --- MU per Gy ---
mu_per_gy = total_mu / prescription_dose_gy if prescription_dose_gy != 0 else None

# --- Init variables ---
total_leaf_travel_mm = 0.0
total_active_leaf_moves = 0
num_transitions = 0
mcs_components = []
mu_weighted_sum = 0.0
mu_total_weight = 0.0
aperture_areas = []
edge_metrics = []
mu_weighted_em_sum = 0.0
mu_weight_total = 0.0
beam_results = {}

leaf_width_cm = 0.5
leaf_width_mm = leaf_width_cm * 10

def compute_edge_metric_from_leaf_positions(lefts, rights, leaf_width_cm=0.5, leaf_range=None, debug=False):
    indices = list(range(len(lefts))) if leaf_range is None else list(range(leaf_range[0], leaf_range[1] + 1))
    open_indices = [i for i in indices if rights[i] > lefts[i]]
    if not open_indices:
        return 0.0, 0.0, 0.0

    total_perimeter = 0.0
    total_area = 0.0
    num_open_leaves = len(open_indices)

    for i in open_indices:
        width = rights[i] - lefts[i]
        area = width * leaf_width_cm
        total_area += area
        if debug:
            print(f"Leaf {i:2d}: Left={lefts[i]:6.2f}, Right={rights[i]:6.2f}, Width={width:6.2f}, Area={area:6.2f}")

    top_leaf = open_indices[0]
    bottom_leaf = open_indices[-1]
    top_width = rights[top_leaf] - lefts[top_leaf]
    bottom_width = rights[bottom_leaf] - lefts[bottom_leaf]
    total_perimeter += top_width + bottom_width

    for i in range(1, len(open_indices)):
        prev = open_indices[i - 1]
        curr = open_indices[i]
        d_left = abs(lefts[curr] - lefts[prev])
        d_right = abs(rights[curr] - rights[prev])
        total_perimeter += d_left + d_right
        if debug:
            print(f"ΔLeaf {prev}-{curr}: ΔL = {d_left:.2f}, ΔR = {d_right:.2f}")

    vertical_contrib = 2 * num_open_leaves * leaf_width_cm
    total_perimeter += vertical_contrib

    edge_metric = total_perimeter / total_area if total_area > 0 else 0.0
    return total_perimeter, total_area, edge_metric

for beam in beam_set.Beams:
    beam_mu = beam.BeamMU
    beam_name = beam.Name
    beam_mcs_list = []
    beam_edge_list = []
    beam_aperture_areas = []
    beam_weighted_mcs_sum = 0.0
    beam_weighted_em_sum = 0.0
    beam_weight_total = 0.0

    if debug_mode:
        print(f"\n== Beam: {beam_name} ==")

    segments = beam.Segments
    for i in range(1, len(segments)):
        prev_leaf_pos = segments[i - 1].LeafPositions
        curr_leaf_pos = segments[i].LeafPositions

        y1 = segments[i].JawPositions[2]
        y2 = segments[i].JawPositions[3]
        y_min = min(y1, y2)
        y_max = max(y1, y2)

        num_leaves = len(prev_leaf_pos[0])
        center_index = num_leaves // 2
        leaf_start = int(center_index + y_min / leaf_width_cm)
        leaf_end = int(center_index + y_max / leaf_width_cm)
        leaf_start = max(0, leaf_start)
        leaf_end = min(num_leaves - 1, leaf_end)

        leaf_widths = []

        for leaf_index in range(leaf_start, leaf_end + 1):
            left_prev = prev_leaf_pos[0][leaf_index]
            right_prev = prev_leaf_pos[1][leaf_index]
            left_curr = curr_leaf_pos[0][leaf_index]
            right_curr = curr_leaf_pos[1][leaf_index]

            travel_left = abs(left_curr - left_prev)
            travel_right = abs(right_curr - right_prev)
            total_leaf_travel_mm += travel_left + travel_right
            total_active_leaf_moves += 2

            opening_width = max(0.0, right_curr - left_curr)
            leaf_widths.append(opening_width)

        num_transitions += 1

        mean_width = sum(leaf_widths) / len(leaf_widths) if leaf_widths else 0.0
        std_width = statistics.pstdev(leaf_widths) if leaf_widths else 0.0
        shape_score = max(0.0, min(1.0, 1 - (std_width / mean_width))) if mean_width > 0 else 0.0

        mcs_components.append(shape_score)

        segment_mu = beam_mu * segments[i].RelativeWeight
        mu_weighted_sum += segment_mu * shape_score
        mu_total_weight += segment_mu

        segment_area = sum(opening_width * leaf_width_cm for opening_width in leaf_widths)
        aperture_areas.append(segment_area)

        _, _, edge_metric = compute_edge_metric_from_leaf_positions(
            segments[i].LeafPositions[0],
            segments[i].LeafPositions[1],
            leaf_width_cm=leaf_width_cm,
            leaf_range=(leaf_start, leaf_end),
            debug=debug_mode
        )
        edge_metrics.append(edge_metric)

        mu_weighted_em_sum += segment_mu * edge_metric
        mu_weight_total += segment_mu

        beam_mcs_list.append(shape_score)
        beam_edge_list.append(edge_metric)
        beam_aperture_areas.append(segment_area)
        beam_weighted_mcs_sum += segment_mu * shape_score
        beam_weighted_em_sum += segment_mu * edge_metric
        beam_weight_total += segment_mu

    if beam_weight_total > 0:
        beam_results[beam_name] = {
            "MU": beam_mu,
            "Avg MCS": sum(beam_mcs_list) / len(beam_mcs_list) if beam_mcs_list else 0.0,
            "MU-weighted MCS": beam_weighted_mcs_sum / beam_weight_total,
            "Avg EM": sum(beam_edge_list) / len(beam_edge_list) if beam_edge_list else 0.0,
            "MU-weighted EM": beam_weighted_em_sum / beam_weight_total,
            "AAV": (statistics.pstdev(beam_aperture_areas) / (sum(beam_aperture_areas) / len(beam_aperture_areas))) if beam_aperture_areas else 0.0
        }

# --- Final calculations ---
avg_leaf_travel_mm = total_leaf_travel_mm / num_transitions if num_transitions > 0 else 0
avg_leaf_travel_per_leaf_per_segment = (total_leaf_travel_mm / total_active_leaf_moves) if total_active_leaf_moves > 0 else 0.0
mcs_score = sum(mcs_components) / len(mcs_components) if mcs_components else 0
mu_weighted_mcs = mu_weighted_sum / mu_total_weight if mu_total_weight > 0 else 0
avg_edge_metric = sum(edge_metrics) / len(edge_metrics) if edge_metrics else 0
mu_weighted_edge_metric = mu_weighted_em_sum / mu_weight_total if mu_weight_total > 0 else 0
aav_score = (statistics.pstdev(aperture_areas) / (sum(aperture_areas) / len(aperture_areas))) if aperture_areas else 0

# --- Console Output ---
print("\n==== Plan Complexity Summary ====")
print(f"Total MU: {total_mu:.2f}")
print(f"MU per Gy: {mu_per_gy:.2f}")
print(f"Total Leaf Travel (mm): {total_leaf_travel_mm:.2f}")
print(f"Average Leaf Travel per Segment Transition (mm): {avg_leaf_travel_mm:.2f}")
print(f"Average Travel per Leaf per Segment (mm): {avg_leaf_travel_per_leaf_per_segment:.2f}")
print(f"Modulation Complexity Score (MCS): {mcs_score:.4f}")
print(f"MU-weighted MCS: {mu_weighted_mcs:.4f}")
print(f"Aperture Area Variation (AAV): {aav_score:.4f}")
print(f"Average Edge Metric (EM): {avg_edge_metric:.4f}")
print(f"MU-weighted Edge Metric (EM): {mu_weighted_edge_metric:.4f}")

print("\n==== Per-Beam Complexity Breakdown ====")
for beam_name, metrics in beam_results.items():
    print(f"\n-- Beam: {beam_name} --")
    print(f"MU: {metrics['MU']:.2f}")
    print(f"Average MCS: {metrics['Avg MCS']:.4f}")
    print(f"MU-weighted MCS: {metrics['MU-weighted MCS']:.4f}")
    print(f"Average Edge Metric (EM): {metrics['Avg EM']:.4f}")
    print(f"MU-weighted Edge Metric (EM): {metrics['MU-weighted EM']:.4f}")
    print(f"Aperture Area Variation (AAV): {metrics['AAV']:.4f}")

# === Excel-friendly Output ===
export_headers = True
include_beam_metrics = True

plan_headers = [
    "PlanName", "Total MU", "MU per Gy", "Total Leaf Travel (mm)",
    "Avg Leaf Travel/Transition (mm)", "Avg Travel/Leaf/Segment (mm)",
    "MCS", "MU-weighted MCS", "AAV", "Avg EM", "MU-weighted EM"
]
plan_values = [
    plan.Name,
    f"{total_mu:.2f}", f"{mu_per_gy:.2f}", f"{total_leaf_travel_mm:.2f}",
    f"{avg_leaf_travel_mm:.2f}", f"{avg_leaf_travel_per_leaf_per_segment:.2f}",
    f"{mcs_score:.4f}", f"{mu_weighted_mcs:.4f}", f"{aav_score:.4f}",
    f"{avg_edge_metric:.4f}", f"{mu_weighted_edge_metric:.4f}"
]

beam_rows = []
beam_headers = [
    "PlanName", "Beam Name", "MU",
    "Avg MCS", "MU-weighted MCS", "Avg EM", "MU-weighted EM", "AAV"
]

for beam_name, metrics in beam_results.items():
    row = [
        plan.Name,
        beam_name,
        f"{metrics['MU']:.2f}",
        f"{metrics['Avg MCS']:.4f}",
        f"{metrics['MU-weighted MCS']:.4f}",
        f"{metrics['Avg EM']:.4f}",
        f"{metrics['MU-weighted EM']:.4f}",
        f"{metrics['AAV']:.4f}"
    ]
    beam_rows.append(row)

def to_norwegian_tab_format(value):
    return str(value).replace('.', ',')

# Convert values
plan_values_tab = [to_norwegian_tab_format(v) for v in plan_values]
beam_rows_tab = [[to_norwegian_tab_format(v) for v in row] for row in beam_rows]

# Output with tab separator and comma decimals
print("\n==== Excel-formated data, tab seperated but comma instead of decimal ====")
if export_headers:
    print("\t".join(plan_headers))
print("\t".join(plan_values_tab))

if include_beam_metrics:
    print("\n-- Per beam Complexity --")
    if export_headers:
        print("\t".join(beam_headers))
    for row in beam_rows_tab:
        print("\t".join(row))
