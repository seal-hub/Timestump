import glob
import hashlib
import xml.etree.ElementTree as ET
import re
from typing import List
from collections import Counter
import os
import chardet
from consts import BOUNDS_REGEX, SCREEN_BOUNDS, BOTTOM_NAV_BAR_BOUNDS, TOP_NAV_BAR_BOUNDS
from node import Node, A11yFocusedStatus
from GUI_utils import *


def define_a11y_focus(elements: List[Node], last_focused_bounds: str, accessibility_focuses) -> None:
    # Adjust accessibility focus status based on vertical position relative to the minimum focus.
    if last_focused_bounds == "Bounds not found.":
        pivot_y = max((i[0][1] for i in accessibility_focuses), default=float('inf'))
    else:
        _, pivot_y, _, _ = last_focused_bounds
    for element in elements:
        # Decide based on the top edge of the element
        (_, y1), (_, y2) = element.bounds
        if y2 <= pivot_y:
            element.a11yFocusedStatus = A11yFocusedStatus.BEFORE
        elif y1 >= pivot_y:
            element.a11yFocusedStatus = A11yFocusedStatus.AFTER
        else:
            element.a11yFocusedStatus = A11yFocusedStatus.AFTER

def define_a11y_focus_appearing_disappearing(elements: List[Node], last_focused_bounds: str, accessibility_focuses, last_clicked_bounds) -> None:
    if last_focused_bounds == "Bounds not found.":
        pivot_y = max((i[0][1] for i in accessibility_focuses), default=float('inf'))
    else:
        _, pivot_y, _, _ = last_focused_bounds
    if last_clicked_bounds != "Bounds not found.":
        _, pivot_y, _, _ = last_clicked_bounds
    for element in elements:
        # Extract the top-left and bottom-right y-coordinates of the element
        (_, y1), (_, y2) = element.bounds
        if y2 <= pivot_y:
            element.a11yFocusedStatus = A11yFocusedStatus.BEFORE
        elif y1 >= pivot_y:
            element.a11yFocusedStatus = A11yFocusedStatus.AFTER
        else:
            element.a11yFocusedStatus = A11yFocusedStatus.AFTER

def bounds_near_each_other(bound1: tuple, bound2: tuple, error=100) -> bool:
    bound1_lt, bound1_rb = bound1
    bound2_lt, bound2_rb = bound2

    return (abs(bound1_lt[0] - bound2_lt[0]) <= error and
            abs(bound1_lt[1] - bound2_lt[1]) <= error and
            abs(bound1_rb[0] - bound2_rb[0]) <= error and
            abs(bound1_rb[1] - bound2_rb[1]) <= error)

def is_within_refreshed_area(element, refreshed_areas):
    # Check if any corner of the element's bounds is within any refreshed area.
    # Adjusted to correctly unpack element.bounds
    (ex1, ey1), (ex2, ey2) = element.bounds  # Correct unpacking based on provided structure
    for rx1, ry1, rx2, ry2 in refreshed_areas:
        # Check if the element overlaps any refreshed area
        if not (ex2 < rx1 or ex1 > rx2 or ey2 < ry1 or ey1 > ry2):
            return True
    return False

def is_within_nav_bars(element_bounds):
    """Check if element is within top or bottom navigation bars."""
    (x1, y1), (x2, y2) = element_bounds
    # Check against top navigation bar
    if y1 >= TOP_NAV_BAR_BOUNDS[1] and y2 <= TOP_NAV_BAR_BOUNDS[3]:
        return True
    # Check against bottom navigation bar
    if y1 >= BOTTOM_NAV_BAR_BOUNDS[1] and y2 <= BOTTOM_NAV_BAR_BOUNDS[3]:
        return True
    return False

def filter_contained_elements(moving_elements):
    """Filter out elements that act as containers for other elements based solely on bounds."""

    # Helper function to determine if one element's bounds are within another's
    def is_container(container_bounds, child_bounds):
        return (container_bounds[0][0] < child_bounds[0][0] and
                container_bounds[0][1] < child_bounds[0][1] and
                container_bounds[1][0] > child_bounds[1][0] and
                container_bounds[1][1] > child_bounds[1][1])

    # Determine containers by comparing bounds of all elements
    containers = set()
    for i, element in enumerate(moving_elements):
        for j, other_element in enumerate(moving_elements):
            if i != j and is_container(element.bounds, other_element.bounds):
                containers.add(i)  # Mark the index of the container element

    # Filter out the containers, keeping elements not identified as containers
    filtered_elements = [element for index, element in enumerate(moving_elements) if index not in containers]

    return filtered_elements

    # Helper function to compare and mark moving elements

    # Helper function to compare and mark moving elements

def filter_elements(elements_1, elements_2):
    resource_ids = {e.resource_id for e in elements_2}
    texts = {e.text for e in elements_2}
    content_descriptions = {e.content_description for e in elements_2}
    filtered_elements = [e for e in elements_1 if
                         e.resource_id not in resource_ids or e.text not in texts or e.content_description not in content_descriptions]
    return filtered_elements

def hash_nodes(nodes):
    hashed = {}
    nodes_by_resource_id = {}
    duplicate_resource_ids = set()  # Track duplicate resource IDs
    for node in nodes:
        resource_id = node.resource_id
        if resource_id:
            if resource_id not in hashed and resource_id not in duplicate_resource_ids:
                hashed[resource_id] = hash_node_attributes(node)
                nodes_by_resource_id[resource_id] = node
            else:
                # Mark as duplicate and remove if previously added
                duplicate_resource_ids.add(resource_id)
                if resource_id in hashed:
                    del hashed[resource_id]
                    del nodes_by_resource_id[resource_id]
    return hashed, nodes_by_resource_id

def hash_node_attributes(node: Node):
    # Concatenate the string representations of the specified attributes
    attributes_str = f"{node.text}{node.content_description}{node.class_name}{node.visible}{node.clickable}{node.important_for_accessibility}{node.enabled}{node.checked}{node.selected}"

    # Use hashlib's sha256 function to create a hash object
    hash_object = hashlib.sha256(attributes_str.encode())

    # Return the hexadecimal representation of the digest
    return hash_object.hexdigest()


def nodes_to_important_attrs_list(nodes: List[Node], is_moving=False):
    if is_moving:
        updated_nodes = [{**node.important_attributes(), "moving_from_above_to_below": node.moving_from_above_to_below}
                         for node in nodes]
        return updated_nodes
    else:
        return [node.important_attributes() for node in nodes]


def filter_nodes_by_resource_id(nodes: List[Node]):
    filtered_nodes = []
    seen_resource_ids = set()
    for node in nodes:
        resource_id = node.resource_id  # Assuming each node is a dict with a 'resource_id' key
        if resource_id not in seen_resource_ids:
            filtered_nodes.append(node)
            seen_resource_ids.add(resource_id)
    return filtered_nodes


def filter_attributes_changed_nodes(nodes):
    return [node for node in nodes if node.liveRegion == '0' and not node.is_ancestor_live_region and (
                node.focusable == 'true' or node.important_for_accessibility == 'true')]


def filter_moving_nodes(nodes):
    return [node for node in nodes if node.a11yFocusedStatus == A11yFocusedStatus.BEFORE]


def filter_short_lived_nodes(nodes, excluded_nodes):
    filtered_nodes = [node for node in nodes if node.clickable == 'true' or (
                node.liveRegion == '0' and not node.is_ancestor_live_region and node.important_for_accessibility == 'true' and node.visible == 'true')]
    return [node for node in filtered_nodes if node not in excluded_nodes]


def filter_disappearing_nodes(nodes, excluded_nodes, additional_nodes, target_elements):
    nodes = [node for node in nodes if node not in excluded_nodes and node.visible == 'true' and (
                node.important_for_accessibility == 'true' or node.focusable == 'true' or node.text != "" or node.content_description != "")]
    if additional_nodes:
        nodes = filter_elements(nodes, additional_nodes)
    return filter_nodes_based_on_target_elements(nodes, target_elements)


def filter_appearing_nodes(nodes, excluded_nodes, additional_nodes, target_elements):
    nodes = [node for node in nodes if node not in excluded_nodes and node.visible == 'true' and (
                node.important_for_accessibility == 'true' or node.focusable == 'true' or node.text != "" or node.content_description != "")]
    if additional_nodes:
        nodes = filter_elements(nodes, additional_nodes)
    return filter_nodes_based_on_target_elements(nodes, target_elements, before_focus=True)


def filter_nodes_based_on_target_elements(nodes, target_elements, before_focus=False):
    resource_id_counts = Counter(element.resource_id for element in target_elements)
    unique_resource_ids = {resource_id for resource_id, count in resource_id_counts.items() if count == 1}
    text_list = [element.text for element in target_elements if element.text != ""]
    content_description_list = [element.content_description for element in target_elements if
                                element.content_description != ""]

    focus_status_check = (lambda node: node.a11yFocusedStatus == A11yFocusedStatus.BEFORE) if before_focus else (
        lambda node: node.a11yFocusedStatus == A11yFocusedStatus.AFTER)

    return [node for node in nodes if
            focus_status_check(node) and node.liveRegion == '0' and node.resource_id not in unique_resource_ids and (
                        node.text not in text_list) and (node.content_description not in content_description_list)]


def get_problematic_dynamic_content_changes(attributes_changed_nodes, moving_nodes, short_lived_nodes,
                                            disappearing_nodes, appearing_nodes, target_elements_1, target_elements_2):
    attributes_changed_nodes = filter_attributes_changed_nodes(attributes_changed_nodes)
    attributes_changed_nodes = filter_nodes_by_resource_id(attributes_changed_nodes)

    moving_nodes = filter_moving_nodes(moving_nodes)

    short_lived_nodes = filter_short_lived_nodes(short_lived_nodes, attributes_changed_nodes)

    disappearing_nodes = filter_disappearing_nodes(disappearing_nodes, moving_nodes + short_lived_nodes,
                                                   appearing_nodes, target_elements_2)

    appearing_nodes = filter_appearing_nodes(appearing_nodes, moving_nodes + short_lived_nodes, disappearing_nodes,
                                             target_elements_1)

    return attributes_changed_nodes, moving_nodes, short_lived_nodes, disappearing_nodes, appearing_nodes

def load_xml(path: str):
    try:
        tree = ET.parse(path)
        nodes = []
        root = tree.getroot()
        # Initialize the stack with the children of the root node and None as their parent
        stack = [(child, None) for child in list(root)]
        while stack:
            element, parent_node = stack.pop()
            current_node = Node(element)
            if parent_node != None:
                current_node.parent = parent_node
            nodes.append(current_node)
            # Extend the stack with the children of the current element and the current node as their parent
            stack.extend([(child, current_node) for child in list(element)])
    except Exception as e:
        print(f"Error: Failed to load the XML file {path}.")
        print(e)
        return []
    for node in nodes:
        node.is_ancestor_live_region = node.check_live_region_ancestors()
    return nodes

# Functions for loading the event log
def load_event_log(path: str):
    line_regex = r'(\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}.\d{3}).*EventType: (\S*);.*EventTime: (\d*);.*boundsInScreen: ([^;]*);'
    rect_regex = r'Rect\((\d+), (\d+) - (\d+). (\d+)\)'
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    events = []
    for line in lines:
        # If the line matches the regex, add all captured groups to the event list as a tuple
        match = re.match(line_regex, line)
        if match:
            elems = list(match.groups())
            rect = elems[-1]
            match_rect = re.match(rect_regex, rect)
            if match_rect:
                elems[-1] = tuple([int(i) for i in match_rect.groups()])
                events.append(elems + [line])
    return events


def load_all_events(path: str):
    ev_regex = r'EventType: (\S*);'
    rect_regex = r'Rect\((\d+), (\d+) - (\d+). (\d+)\)'

    with open(path, 'rb') as file:
        raw_data = file.read()

    # Detect the encoding
    detected = chardet.detect(raw_data)
    encoding = detected['encoding']

    try:
        with open(path, 'r', encoding = encoding) as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        print(f"Error: Failed to decode the file {path} with encoding {encoding}.")

    events = []
    for line in lines:
        match = re.search(ev_regex, line)
        if match != None:
            ev_type = match.groups(1)[0]
            if ev_type == 'TYPE_WINDOW_CONTENT_CHANGED':
                match_rect = re.search(rect_regex, line)
                if match_rect:
                    coords = tuple([int(i) for i in match_rect.groups()])
                    events.append((ev_type, coords))
                else:
                    events.append((ev_type, None))
            else:
                events.append((ev_type, None))

    return events  # List of event types

def in_bound(bound: tuple, coord: tuple):
    return bound[0][0] < coord[0] < bound[1][0] and bound[0][1] < coord[1] < bound[1][1]


def analyze_events_scroll_click(file_path: str) -> bool:
    # Define possible immediate follow-ups for each event of interest
    # (i.e., events that might occur immediately after the event of interest)
    follow_up_events_scroll = {"TYPE_WINDOW_STATE_CHANGED", "TYPE_WINDOW_CONTENT_CHANGED"}
    follow_up_events_click = {"TYPE_WINDOW_STATE_CHANGED", "TYPE_WINDOWS_CHANGED"}

    # Initialize booleans for scrolling and clicking
    is_scrolling_new_content = False
    is_click_new_window = False

    # Helper function to parse scroll details from a line
    def parse_scroll_details(line):
        details = {}
        parts = line.split(";")
        for part in parts:
            if ":" in part:
                key_value = part.split(":", 1)  # Split on first colon only
                if len(key_value) == 2:
                    key, value = key_value
                    key = key.strip()
                    value = value.strip()
                    # Try converting numeric values
                    if key in ['ScrollDeltaX', 'ScrollDeltaY', 'FromIndex', 'ToIndex']:
                        try:
                            details[key] = int(value.split(" ")[0])  # Assuming value might end with units or additional info
                        except ValueError:
                            pass
        return details

    # Helper function to check if a real scroll occurred
    def did_scroll_occur(scroll_details):
        scroll_delta_x = scroll_details.get('ScrollDeltaX', 0)
        scroll_delta_y = scroll_details.get('ScrollDeltaY', 0)
        from_index = scroll_details.get('FromIndex', -1)
        to_index = scroll_details.get('ToIndex', -1)

        return scroll_delta_x != 0 or scroll_delta_y != 0

    last_event_type = None
    last_scroll_details = {}

    try:
        with open(file_path, 'r') as file:
            for line in file:
                if "EventType: TYPE_VIEW_SCROLLED" in line:
                    last_event_type = "TYPE_VIEW_SCROLLED"
                    last_scroll_details = parse_scroll_details(line)
                elif "EventType: TYPE_VIEW_CLICKED" in line:
                    last_event_type = "TYPE_VIEW_CLICKED"
                elif "EventType:" in line:
                    current_event_type = line.split("EventType:")[1].split(";")[0].strip()
                    if last_event_type == "TYPE_VIEW_SCROLLED" and current_event_type in follow_up_events_scroll:
                        if did_scroll_occur(last_scroll_details):
                            is_scrolling_new_content = True
                    # elif last_event_type == "TYPE_VIEW_CLICKED" and (current_event_type in follow_up_events_click or (current_event_type == "TYPE_WINDOW_CONTENT_CHANGED" and "CONTENT_CHANGE_TYPE_SUBTREE" in line)):
                    elif last_event_type == "TYPE_VIEW_CLICKED" and (current_event_type in follow_up_events_click):
                        is_click_new_window = True
                    # Update last_event_type if it's not a follow-up event we are interested in
                    if "TYPE_VIEW_" not in current_event_type and last_event_type != "TYPE_VIEW_CLICKED":
                        last_event_type = None
    except Exception as e:
        print(f"Error: Failed to read the file {file_path}.")
        print(e)

    # If no matching pattern is found in the file, return False
    return is_scrolling_new_content, is_click_new_window

def load_all_elements(file: str) -> list:
    # Processing XML dump of the UI hierarchy
    target_elements = load_xml(file)

    temp_elements = []
    for e in target_elements:
        temp_box = e.bounds
        match = re.match(BOUNDS_REGEX, temp_box)
        if not match:
            raise Exception(f"Bounds regex did not match: {temp_box}")
        altered_match = [int(match.group(i)) for i in range(1, 5)]
        if True in [i < 0 for i in altered_match]:
            continue
        if altered_match[3] < altered_match[1]:
            temp = altered_match[3]
            altered_match[3] = altered_match[1]
            altered_match[1] = temp
        if altered_match[2] < altered_match[0]:
            temp = altered_match[2]
            altered_match[2] = altered_match[0]
            altered_match[0] = temp
        # if not (in_bounds_1(set([screen_bounds]), (altered_match[0], altered_match[1])) and in_bounds_1(set([screen_bounds]), (altered_match[2], altered_match[3]))):
        #     continue
        if not in_bounds_1(set([SCREEN_BOUNDS]), (altered_match[0], altered_match[1])) or not in_bounds_1(
                set([SCREEN_BOUNDS]), (altered_match[2], altered_match[3])):
            continue
        coords = ((altered_match[0], altered_match[1]), (altered_match[2], altered_match[3]))
        e.bounds = coords
        temp_elements.append(e)


    return temp_elements


def check_event(path: str, events: list) -> bool:
    try:
        with open(path, 'r') as f:
            lines = f.readlines()
        for line in lines:
            for ev in events:
                if ev in line:
                    return True
    except Exception as e:
        print(f"Error: Failed to read the file {path}.")
        print(e)
        return False
    return False







def extract_bounds_of_last_focused_element(file_path):
    last_focused_element_bounds = None
    last_focused_element_info = None
    last_clicked_element_info = None
    last_clicked_element_bounds = None
    try:
        with open(file_path, 'r') as file:
            for line in file:
                if 'EventType: TYPE_VIEW_ACCESSIBILITY_FOCUSED' in line:
                    # Capture the line for further processing
                    last_focused_element_info = line
                if 'EventType: TYPE_VIEW_CLICKED' in line:
                    # Capture the line for further processing
                    last_clicked_element_info = line
    except Exception as e:
        print(f"Error: Failed to read the file {file_path}.")
        print(e)

    # Now, extract the bounds from the last focused element info
    if last_focused_element_info:
        # Find the part of the line that contains "boundsInScreen"
        start = last_focused_element_info.find('boundsInScreen: Rect(')
        if start != -1:
            # Extract the substring containing the bounds
            end = last_focused_element_info.find(')', start) + 1
            bounds_str = last_focused_element_info[start:end]
            # Extract just the numbers from the bounds string
            bounds = convert_to_tuple(bounds_str)
            last_focused_element_bounds = bounds

    if last_clicked_element_info:
        start = last_clicked_element_info.find('boundsInScreen: Rect(')
        if start != -1:
            end = last_clicked_element_info.find(')', start) + 1
            bounds_str = last_clicked_element_info[start:end]
            bounds = convert_to_tuple(bounds_str)
            last_clicked_element_bounds = bounds

    if not last_focused_element_bounds:
        last_focused_element_bounds = "Bounds not found."

    if not last_clicked_element_bounds:
        last_clicked_element_bounds = "Bounds not found."


    return last_focused_element_bounds, last_clicked_element_bounds
def convert_to_tuple(bounds_str):
    # Extract the substring that contains the numbers
    start_index = bounds_str.find('Rect(') + len('Rect(')
    numbers_str = bounds_str[start_index:-1]
    # Use regular expression to find all numbers, including negatives
    parts = re.findall(r'-?\d+', numbers_str)
    # Convert parts to integers and create a tuple
    bounds_tuple = tuple(int(part) for part in parts)
    return bounds_tuple



def in_bounds_1(areas: set, coord: tuple):
    for a in areas:
        if a[0] <= coord[0] <= a[2] and a[1] <= coord[1] <= a[3]:
            return True
    return False


def in_bounds_2(areas: set, coord: tuple):
    for a in areas:
        if in_bound(a, coord):
            return True
    return False

def is_accessibility_focus_changed_after_clicking(file_path : str) -> bool:
    print()
    is_accessibility_focus_changed = False
    last_event_type = None

    try:
        with open(file_path, 'r') as file:
            for line in file:
                if "EventType: TYPE_VIEW_CLICKED" in line:
                    last_event_type = "TYPE_VIEW_CLICKED"
                elif "EventType:" in line:
                    current_event_type = line.split("EventType:")[1].split(";")[0].strip()
                    if last_event_type == "TYPE_VIEW_CLICKED" and (current_event_type == "TYPE_VIEW_ACCESSIBILITY_FOCUSED"):
                        is_accessibility_focus_changed = True
                        break
    except:
        print(f"Error: Failed to read the file {file_path}.")
        return False

    return is_accessibility_focus_changed




def get_base_paths(dataset_dir: str) -> list:
    """Returns a list of base paths for all datasets in the given directory"""
    result = []
    for app_name in os.listdir(dataset_dir):
        if app_name.startswith('.'):
            continue
        for test_result in os.listdir(dataset_dir + "/" + app_name):
            if test_result.startswith('.'):
                continue
            result.append(dataset_dir + "/" + app_name + "/" + test_result + "/" + test_result)
    return result


def import_data(base_path: str) -> tuple:
    """Imports all related data in the given directory"""
    # Load events from event log
    parts = base_path.split('/')
    # Rejoin the first parts up to the first three slashes
    base_path = '/'.join(parts[:3])
    events = load_event_log(glob.glob(f"{base_path}/*-ev.txt")[0])
    full_events = load_all_events(glob.glob(f"{base_path}/*-ev.txt")[0])
    # Import ally node elements
    target_elements_1 = load_all_elements(glob.glob(f"{base_path}/*.1-a11y.xml")[0])
    image_initial = glob.glob(f"{base_path}/*.1.png")[0]
    image_final = glob.glob(f"{base_path}/*.3.png")[0]
    is_scrolling_new_content, is_click_new_window = analyze_events_scroll_click(glob.glob(f"{base_path}/*-ev.txt")[0])
    target_elements_middle = load_all_elements(glob.glob(f"{base_path}/*.action-a11y.xml")[0])

    target_elements_2 = load_all_elements(glob.glob(f"{base_path}/*.3-a11y.xml")[0])
    last_focused_bounds, last_clicked_bounds = extract_bounds_of_last_focused_element(glob.glob(f"{base_path}/*-ev.txt")[0])
    # Check if window change occurred
    w_changed = check_event(glob.glob(f"{base_path}/*-ev.txt")[0], ['TYPE_WINDOWS_CHANGED', 'TYPE_WINDOW_STATE_CHANGED'])
    # Check if accessibility focus occurred
    has_accessibility_focus = True in [True for i in events if i[2] == 'TYPE_VIEW_ACCESSIBILITY_FOCUSED']
    is_significant_new_content = False
    if not is_scrolling_new_content and not is_click_new_window:
        if not compare_images(image_initial, image_final):
            is_significant_new_content = True
    is_accessibility_focus_changed = False
    if is_significant_new_content:
        is_accessibility_focus_changed = is_accessibility_focus_changed_after_clicking(glob.glob(f"{base_path}/*-ev.txt")[0])

    return events, full_events, target_elements_1, target_elements_middle, target_elements_2, w_changed, has_accessibility_focus, is_scrolling_new_content, is_click_new_window, last_focused_bounds, last_clicked_bounds, is_significant_new_content, is_accessibility_focus_changed
