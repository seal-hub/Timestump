import imagehash
from PIL import Image, ImageDraw, ImageGrab


def are_images_similar(image_path1, image_path2, threshold=0.95):
    """
    Compares two images using perceptual hash to determine if they are similar.
    Returns:
    - True if images are considered the same, False otherwise.
    """
    # Open the images
    image1 = Image.open(image_path1)
    image2 = Image.open(image_path2)

    # Calculate hash for both images
    hash1 = imagehash.phash(image1)
    hash2 = imagehash.phash(image2)

    # Calculate the similarity (normalized Hamming distance)
    # Normalize by dividing by the maximum possible Hamming distance (64 for phash)
    similarity = 1 - (hash1 - hash2) / 64.0

    return similarity >= threshold


def overlay_boxes_on_image(image_path, blue_boxes, red_boxes, green_boxes, purple_boxes, black_boxes, output_path):
    # Open the image
    with Image.open(image_path) as image:
        # Prepare for drawing on the image
        draw = ImageDraw.Draw(image)

        # Draw green boxes
        if len(green_boxes) != 0:
            for box in green_boxes:
                top_left, bottom_right = box
                draw.rectangle([top_left, bottom_right], outline="orange", width=3)

        # Draw red boxes
        for box in red_boxes:
            top_left, bottom_right = box
            draw.rectangle([top_left, bottom_right], outline="red", width=3)

        # Draw blue boxes
        for box in blue_boxes:
            top_left, bottom_right = box
            draw.rectangle([top_left, bottom_right], outline="blue", width=3)

        for box in purple_boxes:
            top_left, bottom_right = box
            draw.rectangle([top_left, bottom_right], outline="purple", width=3)

        for box in black_boxes:
            top_left, bottom_right = box
            draw.rectangle([top_left, bottom_right], outline="black", width=3)



        # Save the resulting image
        image.save(output_path)


# Displaying stuff
def compare_images(file1, file2, threshold=0.9, target_size=(8, 8)):
    """Compares images using image hashing (average hash).
    Returns:
        A boolean indicating whether the images are similar above the specified threshold.
    """
    # Open the images
    if isinstance(file1, str):
        image1 = Image.open(file1)
    else:
        image1 = Image.open(file1)

    if isinstance(file2, str):
        image2 = Image.open(file2)
    else:
        image2 = Image.open(file2)

    # Resize the images
    image1 = image1.resize(target_size)
    image2 = image2.resize(target_size)

    # Calculate the average hash for each image
    hash1 = imagehash.average_hash(image1)
    hash2 = imagehash.average_hash(image2)

    # Calculate the similarity and convert it to a percentage
    similarity = hash1 - hash2
    similarity_percentage = similarity / 64.0

    # Return True if the similarity is above the threshold
    return 1- similarity_percentage >= threshold