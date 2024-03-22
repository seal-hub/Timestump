import json
import logging
import shutil
from collections import Counter
from utils import *
from node import Node, A11yFocusedStatus
import os
import pickle
from consts import DATASET_FOLDER, RESULTS_FOLDER, RESULTS_PICKLE
from GUI_utils import *

save_only_on_error = True
logging.basicConfig(level=logging.INFO)

def get_short_lived_elements() -> list:
    """Returns a list of short-lived elements"""
    # Create sets for quick lookup of elements by their unique identifiers in the first and last frames.
    unique_identifiers_first = {element.identifier_group_alternative for element in target_elements_1}
    unique_identifiers_last = {element.identifier_group_alternative for element in target_elements_2}

    # Paper definition: "If the element S1 is not present in the first frame, and its container is observed
    # in the second frame"
    potential_short_lived = [element for element in target_element_middle
                             if element.identifier_group_alternative not in unique_identifiers_first and
                             element.identifier_group_alternative not in unique_identifiers_last and
                             element.parent.identifier_group_alternative in unique_identifiers_last]

    # Further refine potential short-lived elements by considering refreshed areas.
    refreshed_areas = {(e[4][0], e[4][1], e[4][2], e[4][3]) for e in events if e[2] == 'TYPE_WINDOW_CONTENT_CHANGED'}

    # Filter elements by whether they are within refreshed areas.
    short_lived_elements = [element for element in potential_short_lived if is_within_refreshed_area(element, refreshed_areas)]
    define_a11y_focus(short_lived_elements, last_focused_bounds, accessibility_focuses)
    return short_lived_elements


def get_disappearing_elements(is_scrolling_new_content: bool, is_click_new_window: bool, is_significant_content: bool,
                              is_focus_changed: bool) -> list:
    """Returns a list of elements that are present in the initial state but not in the middle or final states."""
    # Identifiers for elements in the final state for quick lookup
    identifiers_in_final = {i.identifier_group for i in target_elements_2}

    # Find refreshed areas from events
    refreshed_areas = {((e[4][0], e[4][1]), (e[4][2], e[4][3])) for e in events if
                       e[2] == 'TYPE_WINDOW_CONTENT_CHANGED'}

    disappearing_content = []
    if (is_significant_content and not is_focus_changed) or not is_significant_content:
        if is_click_new_window:
            # If the screen is different, focus on elements disappearing from the middle to the final frame
            disappearing_content = [element for element in target_element_middle
                                    if element.identifier_group not in identifiers_in_final and
                                    in_bounds_2(refreshed_areas, element.bounds[0])]
        elif is_scrolling_new_content == False and is_click_new_window == False:
            # Elements in the initial state that do not appear in the final state
            disappearing_content = [element for element in target_elements_1
                                    if element.identifier_group not in identifiers_in_final and
                                    in_bounds_2(refreshed_areas, element.bounds[0])]
        # Adjust accessibility focus status if needed
        if disappearing_content and accessibility_focuses:
            define_a11y_focus_appearing_disappearing(disappearing_content, last_focused_bounds, accessibility_focuses, last_clicked_bounds)
        disappearing_content = filter_contained_elements(disappearing_content)
    return disappearing_content


def get_appearing_elements(is_scrolling_new_content: bool, is_click_new_window: bool, is_significant_content: bool,
                           is_focus_changed: bool) -> list:
    """Returns a list of dynamically appearing elements that are not present in the initial state but appear in
    the middle or final states."""
    # Initial state identifiers for quick checks
    identifiers_in_initial = {i.identifier_group for i in target_elements_1}

    # Identifiers for elements that are in the middle state
    identifiers_in_middle = {i.identifier_group for i in target_element_middle}

    # Identifiers for elements that are in the final state
    identifiers_in_final = {i.identifier_group for i in target_elements_2}

    # Refreshed areas derived from events
    refreshed_areas = {((e[4][0], e[4][1]), (e[4][2], e[4][3])) for e in events if
                       e[2] == 'TYPE_WINDOW_CONTENT_CHANGED'}

    appearing_content = []
    if (is_significant_content and not is_focus_changed) or not is_significant_content:
        if is_click_new_window:
            # Consider elements appearing in the final state but not in the middle as appearing content
            appearing_content = [element for element in target_elements_2
                                 if element.identifier_group not in identifiers_in_middle and
                                 element.identifier_group in identifiers_in_final and
                                 in_bounds_2(refreshed_areas, element.bounds[0])]
        elif is_scrolling_new_content == False and is_click_new_window == False:
            # Elements not in the initial state but appear in the middle or final states
            appearing_content = [element for element in target_elements_2
                                 if element.identifier_group not in identifiers_in_initial and
                                 (
                                             element.identifier_group in identifiers_in_middle or element.identifier_group in identifiers_in_final) and
                                 in_bounds_2(refreshed_areas, element.bounds[0])]

        # Adjust accessibility focus if needed
        if appearing_content and accessibility_focuses:  # Check if not empty to avoid errors
            define_a11y_focus_appearing_disappearing(appearing_content, last_focused_bounds, accessibility_focuses, last_clicked_bounds)
        appearing_content = filter_contained_elements(appearing_content)
    return appearing_content


def get_moving_elements() -> list:
    """Return a list of moving elements"""
    moved_elements_set = set()

    refreshed_areas = {(e[4][0], e[4][1], e[4][2], e[4][3]) for e in events if e[2] == 'TYPE_WINDOW_CONTENT_CHANGED'}
    # Helper function to compare and mark moving elements
    def compare_and_mark_moving(element, comparison_element):
        error_margin = 100 if is_within_nav_bars(element.bounds) else 2000
        if element.identifier_group_alternative == comparison_element.identifier_group_alternative:
            if element.bounds != comparison_element.bounds and not bounds_near_each_other(element.bounds, comparison_element.bounds, error=error_margin):
                moved_elements_set.add(element.identifier_group_alternative)
                # Determine moving direction based on y-coordinate comparison
                current_y = element.bounds[0][1]
                previous_y = comparison_element.bounds[0][1]
                if current_y > previous_y:
                    element.moving_direction = 'Below'  # Moving downwards
                elif current_y < previous_y:
                    element.moving_direction = 'Above'  # Moving upwards
                if element.a11yFocusedStatus == A11yFocusedStatus.AFTER and comparison_element.a11yFocusedStatus == A11yFocusedStatus.BEFORE:
                    element.moving_from_above_to_below = True

    # Compare elements between frames to identify moving elements
    for element in target_elements_2:
        if wc:
            for element_middle in target_element_middle:
                compare_and_mark_moving(element, element_middle)
        else:
            for element_1 in target_elements_1:
                compare_and_mark_moving(element, element_1)

    # Filter moving elements based on the set of moved elements
    moving_content = [element for element in target_elements_2
                      if element.identifier_group_alternative in moved_elements_set
                      and element.important_for_accessibility == 'true' and is_within_refreshed_area(element, refreshed_areas)]
    if moving_content and accessibility_focuses:  # Check if not empty to avoid errors
        define_a11y_focus(moving_content, last_focused_bounds, accessibility_focuses)
    for element in target_elements_2:
        if element not in moving_content:
            element.moving_direction = None
    filtered_moving_elements = filter_contained_elements(moving_content)
    return filtered_moving_elements


def get_attributes_changed_elements(initial_screen_nodes, middle_screen_nodes, final_screen_nodes) -> list[Node]:
    """Return a list of content modification elements that have changed attributes"""

    # Hash all nodes from each screen and keep references to the nodes
    initial_hashes, initial_nodes = hash_nodes(initial_screen_nodes)
    middle_hashes, middle_nodes = hash_nodes(middle_screen_nodes)
    final_hashes, final_nodes = hash_nodes(final_screen_nodes)

    # Container for nodes with changed attributes
    changed_nodes = set()
    # Compare hash values across screens and identify changed nodes

    # Compare initial to middle and final
    for resource_id, hash_value in initial_hashes.items():
        if resource_id in middle_hashes and hash_value != middle_hashes[resource_id]:
            changed_nodes.add(initial_nodes[resource_id])
        if resource_id in final_hashes and hash_value != final_hashes[resource_id]:
            changed_nodes.add(initial_nodes[resource_id])

    # Compare middle to final
    for resource_id, hash_value in middle_hashes.items():
        if resource_id in final_hashes and hash_value != final_hashes[resource_id]:
            changed_nodes.add(middle_nodes[resource_id])

    define_a11y_focus(changed_nodes, last_focused_bounds, accessibility_focuses)
    return changed_nodes


if __name__ == "__main__":
    # Get all base paths
    base_paths = get_base_paths(DATASET_FOLDER)
    logging.info(f"Found {len(base_paths)} tests:")
    for base_path in base_paths:
        logging.info(base_path)

    if os.path.exists(RESULTS_FOLDER):
        shutil.rmtree(RESULTS_FOLDER)

    # Delete previous pickle file
    if os.path.exists(RESULTS_PICKLE):
        os.remove(RESULTS_PICKLE)

    results_dict = dict()

    for base_path in base_paths:
        events, full_events, target_elements_1, target_element_middle, target_elements_2, wc, af, isn, icn, last_focused_bounds, last_clicked_bounds, is_significant_content, is_focus_changed = import_data(
            base_path)

        # Find accessibility focuses
        accessibility_focuses = [i.bounds for i in target_elements_1 if i.a11yFocused == 'true']
        accessibility_focuses += [i.bounds for i in target_elements_2 if i.a11yFocused == 'true']
        if af:
            ally_focus = [i[4] for i in events if i[2] == 'TYPE_VIEW_ACCESSIBILITY_FOCUSED']
            ally_focus = [((i[0], i[1]), (i[2], i[3])) for i in ally_focus]
            accessibility_focuses += ally_focus

        # Find accessibility issues
        if len(target_elements_2) != 0 and (len(target_elements_1) != 0 or len(target_element_middle) != 0) and len(accessibility_focuses) != 0:
            appearing_nodes = get_appearing_elements(isn, icn, is_significant_content, is_focus_changed)
            moving_nodes = get_moving_elements()
            short_lived_nodes = get_short_lived_elements()
            attributes_changed_nodes = get_attributes_changed_elements(target_elements_1, target_element_middle,
                                                                           target_elements_2)
            disappearing_nodes = get_disappearing_elements(isn, icn, is_significant_content, is_focus_changed)
            attributes_changed_nodes, moving_nodes, short_lived_nodes, disappearing_nodes, appearing_nodes = get_problematic_dynamic_content_changes(attributes_changed_nodes,
                                                                                                                                                     moving_nodes,
                                                                                                                                                     short_lived_nodes, disappearing_nodes, appearing_nodes,
                                                                                                                                                     target_elements_1, target_elements_2)
        else:
            short_lived_nodes = []
            disappearing_nodes = []
            appearing_nodes = []
            moving_nodes = []
            attributes_changed_nodes = []
        results_dict[base_path] = (
        short_lived_nodes, disappearing_nodes, appearing_nodes, moving_nodes, attributes_changed_nodes)

        if save_only_on_error and len(short_lived_nodes) == 0 and len(disappearing_nodes) == 0 and len(
                appearing_nodes) == 0 and len(moving_nodes) == 0 and len(attributes_changed_nodes) == 0:
            logging.info(f"\nTest: {base_path}")
            logging.info("No accessibility issues found")
            continue
        # Announce results
        short_lived_regions = [i.bounds for i in short_lived_nodes]
        disappearing_regions = [i.bounds for i in disappearing_nodes]
        appearing_regions = [i.bounds for i in appearing_nodes]
        moving_regions = [i.bounds for i in moving_nodes]
        attributes_changed_regions = [i.bounds for i in attributes_changed_nodes]
        logging.info(f"\nTest: {base_path}")
        logging.info(f"Short-lived regions [{len(short_lived_nodes)}]: {short_lived_regions}")
        logging.info(f"Disappearing regions [{len(disappearing_nodes)}]: {disappearing_regions}")
        logging.info(f"Appearing regions [{len(appearing_nodes)}]: {appearing_regions}")
        logging.info(f"Moving regions [{len(moving_nodes)}]: {moving_regions}")
        logging.info(f"Attributes changed regions [{len(attributes_changed_nodes)}]: {attributes_changed_regions}")
        # Save results
        # Create folder in results folder
        folder_name = base_path.split('/')[-2]
        folder_name = f"{RESULTS_FOLDER}/{folder_name}"
        os.makedirs(folder_name, exist_ok=True)
        # Print results to text file
        has_error = False
        short_lived_nodes = nodes_to_important_attrs_list(short_lived_nodes)
        disappearing_nodes = nodes_to_important_attrs_list(disappearing_nodes)
        appearing_nodes = nodes_to_important_attrs_list(appearing_nodes)
        moving_nodes = nodes_to_important_attrs_list(moving_nodes, is_moving=True)
        attributes_changed_nodes = nodes_to_important_attrs_list(attributes_changed_nodes)
        with open(folder_name + "/results.txt", 'w', encoding="utf-8") as f:
            f.write(f"Test: {base_path}\n")
            f.write(f"Window changed: {'True' if wc else 'False'}\n")
            f.write(f"Short-lived Elements [{len(short_lived_nodes)}]: \n")
            for node in short_lived_nodes:
                json_dump = json.dumps(node)
                f.write(json_dump + "\n")
            f.write(f"Disappearing Elements [{len(disappearing_nodes)}]: \n")
            for node in disappearing_nodes:
                json_dump = json.dumps(node)
                f.write(json_dump + "\n")
            f.write(f"Appearing Elements [{len(appearing_nodes)}]: \n")
            for node in appearing_nodes:
                json_dump = json.dumps(node)
                f.write(json_dump + "\n")
            f.write(f"Moving Elements [{len(moving_nodes)}]: \n")
            for node in moving_nodes:
                json_dump = json.dumps(node)
                f.write(json_dump + "\n")
            f.write(f"Attributes Changed Elements [{len(attributes_changed_nodes)}]: \n")
            for node in attributes_changed_nodes:
                json_dump = json.dumps(node)
                f.write(json_dump + "\n")

            parts = base_path.split('/')
            # Rejoin the first parts up to the first three slashes
            base_path = '/'.join(parts[:3])
            # Print separate images
            img1 = glob.glob(f"{base_path}/*.1.png")[0]
            img2 = glob.glob(f"{base_path}/*.action.2.png")[0]
            img3 = glob.glob(f"{base_path}/*.3.png")[0]
            images = {"/sl_1_out.png": img1, "/sl_2_out.png": img2, "/sl_3_out.png": img3, "/d_1_out.png": img1,
                      "/d_2_out.png": img2, "/d_3_out.png": img3, "/a_1_out.png": img1, "/a_2_out.png": img2,
                      "/a_3_out.png": img3, "/m_1_out.png": img1, "/m_2_out.png": img2, "/m_3_out.png": img3,
                      "/ca_1_out.png": img1, "/ca_2_out.png": img2, "/ca_3_out.png": img3}
            for key, value in images.items():
                try:
                    if key.startswith("/sl") and len(short_lived_nodes) != 0:
                        overlay_boxes_on_image(value, short_lived_regions, [], [], [], [], folder_name + key)
                    elif key.startswith("/d") and len(disappearing_nodes) != 0:
                        overlay_boxes_on_image(value, [], disappearing_regions, [], [], [], folder_name + key)
                    elif key.startswith("/a") and len(appearing_regions) != 0:
                        overlay_boxes_on_image(value, [], [], appearing_regions, [], [], folder_name + key)
                    elif key.startswith("/m") and len(moving_regions) != 0:
                        overlay_boxes_on_image(value, [], [], [], moving_regions, [], folder_name + key)
                    elif key.startswith("/ca") and len(attributes_changed_regions) != 0:
                        overlay_boxes_on_image(value, [], [], [], [], attributes_changed_regions, folder_name + key)
                except:
                    logging.error(f"Error showing image {value}")
                    has_error = True
        if has_error:
            # Remove folder
            shutil.rmtree(folder_name)
            continue

    # Save results to pickle file
    with open(RESULTS_PICKLE, 'wb') as f:
        pickle.dump(results_dict, f)
