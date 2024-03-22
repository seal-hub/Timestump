from enum import Enum


class A11yFocusedStatus(Enum):
    BEFORE = 1
    ON = 2
    AFTER = 3
    UNCERTAIN =4
    def __str__(self):
        return self.name
class Node:
    def __init__(self, element):
        self.text = element.attrib.get('text', '')
        self.content_description = element.attrib.get('content-desc', '')
        self.class_name = element.attrib.get('class', '')
        self.resource_id = element.attrib.get('resource-id', '')
        self.bounds = element.attrib.get('bounds', '')
        self.size = self.calculate_size(self.bounds)
        self.a11yFocused = element.attrib.get('a11yFocused', '')
        self.liveRegion = element.attrib.get('liveRegion', '')
        self.visible = element.attrib.get('visible', '')
        self.checked = element.attrib.get('checked', '')
        self.moving_from_above_to_below = False
        self.is_changed = None
        self.is_appearing = None
        self.is_disappearing = None
        self.is_short_lived = None
        self.is_moving = None
        self.index = element.attrib.get('index', '')
        self.action_list = element.attrib.get('actionList', '')
        self.a11yFocusedStatus = A11yFocusedStatus.ON if self.a11yFocused == "true" else A11yFocusedStatus.UNCERTAIN
        self.clickable = element.attrib.get('clickable', '')
        self.important_for_accessibility = element.attrib.get('importantForAccessibility', '')
        self.selected = element.attrib.get('selected', '')
        self.focusable = element.attrib.get('focusable', '')
        self.enabled = element.attrib.get('enabled', '')
        self.drawing_order = element.attrib.get('drawingOrder', '')
        self.identifier_group = tuple([self.resource_id, self.class_name, self.index, self.content_description, self.text, self.bounds])
        self.moving_direction = None
        self.identifier_group_alternative = tuple([self.class_name, self.resource_id, self.text, self.index,
                                                   self.clickable, self.important_for_accessibility, self.liveRegion, self.content_description, self.drawing_order])
        self.identifier_group_alternative_2 = tuple([self.class_name, self.resource_id, self.content_description, self.text])
        self.parent = None
        self.is_ancestor_live_region = None

    @staticmethod
    def calculate_size(bounds_str):
        if bounds_str:
            try:
                x1, y1, x2, y2 = map(int, bounds_str.replace('[', '').replace(']', ',').split(',')[:-1])
                return abs(x2 - x1), abs(y2 - y1)
            except ValueError:
                # Handle parsing error
                return None
        return None

    def important_attributes(self):
        return {
            'text': self.text,
            'content_description': self.content_description,
            'class_name': self.class_name,
            'resource_id': self.resource_id,
            'bounds': self.bounds,
            'liveRegion': self.liveRegion,
            'visible': self.visible,
            'a11yFocusedStatus': str(self.a11yFocusedStatus),
            'clickable': self.clickable,
            'important_for_accessibility': self.important_for_accessibility,
            'moving_direction': self.moving_direction
        }

    def check_live_region_ancestors(self):
        """
        Checks if any of the ancestors of the given node has a liveRegion attribute that is not "0".

        :param node: The starting node for checking ancestors' liveRegion.
        :return: True if any ancestor has a liveRegion not "0", False otherwise.
        """
        current_node = self.parent  # Start with the parent of the given node
        while current_node is not None:  # Traverse up until there are no more ancestors
            if current_node.liveRegion != "0":
                return True
            current_node = current_node.parent  # Move to the next ancestor
        return False