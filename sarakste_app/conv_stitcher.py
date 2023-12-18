import os
import django
import easyocr
import sys
from django.db.models import Max
import re
from django.db.models import Q
from datetime import datetime, timedelta
import cv2
import numpy as np
from skimage.metrics import structural_similarity as compare_ssim

from django.conf import settings
# Configure Django settings
sys.path.append('C:\\Users\\db533\\PycharmProjects\\sarakste\\sarakste\\sarakste')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sarakste.settings')  # Replace with your project's settings
django.setup()

# Launch options
delete_overlaps = False
delete_all = False
update_local_database = False



import environ
from django.conf import settings
from sarakste_app.models import *  # Replace 'myapp' with your app name

env = environ.Env()
environ.Env.read_env(overwrite=True)
# Get the IP address of this host
DEBUG = env.bool('debug', default=False)
RUN_REMOTE = env.bool('RUN_REMOTE', default=False)
REMOTE_IP = env.str('REMOTE_IP')
import socket
hostname = socket.gethostname()
IP = socket.gethostbyname(hostname)
HOSTED = env.bool('HOSTED', default=False)
print('HOSTED:',HOSTED)
if HOSTED:
    if RUN_REMOTE == True:
        host_ip = '212.7.207.88'
    else:
        host_ip = IP
    db_name = env.str('MYSQL_PROD_DB_NAME')
    db_user = env.str('MYSQL_PROD_DB_USER')
    db_pwd = env.str('MYSQL_PROD_PWD')
else:
    host_ip = '127.0.0.1'
    db_name = env.str('MYSQL_LOCAL_DB_NAME')
    db_user = env.str('MYSQL_LOCAL_DB_USER')
    db_pwd = env.str('MYSQL_LOCAL_PWD')

import tkinter as tk
from tkinter import Toplevel  # Add this line to import Toplevel
from PIL import Image, ImageTk, ImageChops, ImageStat
import os
import time

# Function to convert hex code to BGR color format
def hex_to_bgr(hex_code):
    # Remove the '#' character if it's present
    hex_code = hex_code.lstrip('#')
    # Convert the hex code to an integer
    hex_int = int(hex_code, 16)
    # Extract the B, G, and R components
    b = (hex_int >> 16) & 255
    g = (hex_int >> 8) & 255
    r = hex_int & 255
    return (b, g, r)

# Define specific colors in hex format
speaker_color1_hex = "#DCF8C6"  # Light Green
speaker_color2_hex = "#F8F8F8"  # Whitish
text_color_hex = "#000000"  # Black

speaker_color1 = hex_to_bgr(speaker_color1_hex)
speaker_color2 = hex_to_bgr(speaker_color2_hex)
text_color = hex_to_bgr(text_color_hex)

# Function to calculate the quantity of pixels that match a specific color
def count_matching_color_pixels(image, color):
    lower_bound = np.array(color) - np.array([10, 10, 10])  # Tolerance for color matching
    upper_bound = np.array(color) + np.array([10, 10, 10])
    mask = cv2.inRange(image, lower_bound, upper_bound)
    return np.sum(mask > 0)

def update_best_row_records(mse, ssim, top_row, later_segment_height, five_best_row, mse_for_best_rows, ssim_for_best_rows, best_match_count, initial_row_matching):
    if best_match_count < 5 and initial_row_matching == True:
        # Since fewer than 5 rows have been added to best row list, add this one too.
        five_best_row.append(top_row)
        mse_for_best_rows[top_row]=[mse]
        ssim_for_best_rows[top_row] = [ssim]
        best_match_count +=1
        top_five_row = True
    else:
        # Need to check if an existing row should be pushed out.
        initial_row_matching = False
        if later_segment_height < 7:
            # Comparison is done using mse
            # Get the most recent mse values for all 5 rows.
            worst_mse = 0
            worst_row_number = None
            for key, value in mse_for_best_rows.items():
                if value[-1] > worst_mse:
                    worst_row_number = key
                    worst_mse = value[-1]
            if mse < worst_mse:
                # Remove the mse records for this row
                mse_for_best_rows.pop(worst_row_number)
                ssim_for_best_rows.pop(worst_row_number)
                # Remove the row from the list of best rows.
                five_best_row.remove(worst_row_number)
                # Add in this row as it has a better mse score.
                if top_row not in five_best_row:
                    five_best_row.append(top_row)
                    mse_for_best_rows[top_row] = [mse]
                    ssim_for_best_rows[top_row] = [ssim]
                else:
                    # This tow is already in five_best_row so just append the new mse and ssim values.
                    mse_for_best_rows[top_row].append(mse)
                    ssim_for_best_rows[top_row].append(ssim)
                top_five_row = True
            elif top_row not in five_best_row:
                top_five_row = False
        else:
            # Comparison is done with ssim
            # Get the most recent ssim values for all 5 rows.
            worst_ssim = 1  # Perfect score
            worst_row_number = None
            for key, value in ssim_for_best_rows.items():
                if value[-1] < worst_ssim:
                    worst_row_number = key
                    worst_ssim = value[-1]
            if ssim > worst_ssim:
                # Remove the mse records for this row
                ssim_for_best_rows.pop(worst_row_number)
                # Remove the row from the list of best rows.
                five_best_row.remove(worst_row_number)
                if top_row not in five_best_row:
                    five_best_row.append(top_row)
                    mse_for_best_rows[top_row] = [mse]
                    ssim_for_best_rows[top_row] = [ssim]
                else:
                    mse_for_best_rows[top_row].append(mse)
                    ssim_for_best_rows[top_row].append(ssim)
                top_five_row = True
            elif ssim <= worst_mse and len(five_best_row) < 5:
                top_five_row = False
            else:
                top_five_row = True
            if top_row in five_best_row:
                mse_for_best_rows[top_row].append(mse)
                ssim_for_best_rows[top_row].append(ssim)
    return five_best_row, mse_for_best_rows, ssim_for_best_rows, best_match_count, top_five_row, initial_row_matching

def find_best_row(five_best_row, mse_for_best_rows, ssim_for_best_rows, best_match_count):
    # Function to find the row with the best ssim score
    best_ssim = -1
    best_row_counter = None
    best_mse_sequence = None
    for key, value in ssim_for_best_rows.items():
        if value[-1] > best_ssim:
            best_row_counter = key
            best_ssim = value[-1]
            best_mse_sequence = mse_for_best_rows[best_row_counter]
    return best_row_counter, best_ssim, best_mse_sequence

def find_matching_rows(earlier_image, later_image, best_ssim_score=2, best_mse_score = 150):
    if earlier_image.height < 1335:
        # Dainis' images = 1334 height
        header_size = 130
        footer_size = 90
    else:
        # Dacite's images = 1920 height
        header_size = 187
        footer_size = 163

    earlier_image = Image.open(os.path.join(image_folder, earlier_image))
    later_image = Image.open(os.path.join(image_folder, later_image))
    #earlier_image.show()
    #later_image.show()

    earlier_height = earlier_image.height
    #print('earlier_height:',earlier_height)
    later_height = later_image.height
    #print('later_height:', later_height)

    feasible_rows = list(range(header_size, later_height - footer_size))

    five_best_row = []
    mse_for_best_rows = {}
    ssim_for_best_rows = {}
    best_match_count=0
    best_ssim_score = -1
    initial_row_matching = True

    #max_overlap = 0
    #best_match_score = 999999999
    #prior_match_score = best_match_score
    #match_barrier = 999  # * (1.5 ** earlier_segment.height)

    for bottom_row in range(earlier_height - footer_size, footer_size-1, -1):  # Start from 90th row from bottom, up to the 90th row
        segment_displayed = False
        min_overlap = 999999999
        earlier_segment = earlier_image.crop((0, bottom_row, earlier_image.width, earlier_height-footer_size+1))

        #print('match_barrier:',match_barrier)
        # Display the earlier_segment image
        #earlier_segment.show()

        # Convert PIL Image objects to NumPy arrays
        earlier_segment_np = np.array(earlier_segment)

        # Calculate the quantity of pixels matching the specific colors
        #earlier_segment_np_color1_count = count_matching_color_pixels(earlier_segment_np, speaker_color1)
        #earlier_segment_np_color2_count = count_matching_color_pixels(earlier_segment_np, speaker_color2)

        if len(feasible_rows) > 0:
            for top_row in feasible_rows[:]:
                later_segment_height = earlier_segment.height
                later_segment = later_image.crop((0, top_row, later_image.width, top_row + later_segment_height))

                # Convert PIL Image objects to NumPy arrays
                later_segment_np = np.array(later_segment)

                # Calculate the quantity of pixels matching the specific colors
                #later_segment_np_color1_count = count_matching_color_pixels(later_segment_np, speaker_color1)
                #later_segment_np_color2_count = count_matching_color_pixels(later_segment_np, speaker_color2)

                # Compare segments
                #match_score = is_match(earlier_segment, later_segment) / (later_segment_height)
                mse, ssim = cv2_is_match(earlier_segment_np, later_segment_np,later_segment_height)
                # Now update the records for the 5 best rows.
                five_best_row, mse_for_best_rows, ssim_for_best_rows, best_match_count, top_five_row, initial_row_matching = update_best_row_records(mse, ssim, top_row, later_segment_height, five_best_row, mse_for_best_rows, ssim_for_best_rows, best_match_count, initial_row_matching)
                print('Rows matched:', later_segment.height, 'mse:', mse, 'ssim:',ssim, 'top_five_row:', top_five_row)
                print('five_best_row:',five_best_row,'mse_for_best_rows:',mse_for_best_rows,'ssim_for_best_rows',ssim_for_best_rows,'best_match_count:',best_match_count)

                if top_five_row == False and len(feasible_rows) > 5 or (ssim > -1 and ssim < 0.7 and len(feasible_rows) > 1):
                    feasible_rows.remove(top_row)

                if len(feasible_rows) == 1:
                    print('1 feasible row...')
                    break

    #            ssim = 1-ssim # Normalise so that best score is 0. So ssim now ranges from 0 to 2. 2 is worst match.

                #print('Rows matched:', later_segment.height, 'mse:', mse, 'ssim:',ssim, 'match_barrier:',match_barrier)
    #            if later_segment_height == 7:
                    # Reset the prior_match_score as now computing ssim.
                    #best_earlier_segment.show()
                    #best_later_segment.show()
    #                prior_match_score = best_ssim_score
    #                best_match_score = best_ssim_score
    #            if later_segment_height > 6:
    #                match_score = ssim
    #            else:
    #                match_score = (mse * 1)
    #            if later_segment_height > 6 and best_ssim_score < 2:
    #                match_barrier = min(best_ssim_score, best_match_score)  * 1.5
                #elif best_mse_score < 150:
                #    match_barrier = min(best_match_score, best_mse_score) * 1.5
                #else:
    #            match_barrier = min(best_match_score, best_mse_score) * 1.5

                #match_score = (mse * 0.01) + (abs(ssim) * 1)
    #            if match_score < prior_match_score:
    #                best_matched_segment = later_segment
    #                best_match_rows = later_segment.height
    #                best_earlier_segment = earlier_segment
    #                best_later_segment = later_segment
                #if len(feasible_rows) < 5:
                #print('Rows matched:', later_segment.height, 'total match_score:', match_score*later_segment_height,'match_score:',match_score, 'match_barrier:',match_barrier)
    #            if match_score < prior_match_score:
    #                best_match_score = match_score
    #                best_matched_segment = later_segment
                    #best_matched_segment.show()
                    #earlier_segment.show()
    #            if match_score < match_barrier:
    #                max_overlap = max(max_overlap, later_segment_height)
    #                prior_match_score = match_score
    #            else:
                    #print('Dropping row',top_row)
    #                feasible_rows.remove(top_row)
            feasible_rows = [x - 1 for x in feasible_rows]
            new_best_rows = []
            new_mse_for_best_rows = {}
            new_ssim_for_best_rows = {}
            for best_row in five_best_row:
                new_best_rows.append(best_row-1)
                new_mse_for_best_rows[best_row-1] = mse_for_best_rows[best_row]
                new_ssim_for_best_rows[best_row - 1] = ssim_for_best_rows[best_row]
            five_best_row = new_best_rows
            mse_for_best_rows = new_mse_for_best_rows
            ssim_for_best_rows = new_ssim_for_best_rows
            if ssim < best_ssim_score:
                print('ssim starting to fall.')
                feasible_rows.remove(top_row)

    best_match_rows = five_best_row[0]
    best_ssim = ssim_for_best_rows[best_match_rows]
    best_mse_sequence = mse_for_best_rows[best_match_rows]

            #print('Rows matched:', later_segment.height)
    #    else:
    #        break
    #if best_match_rows == 15 or best_match_rows == 85:
    best_matched_segment.show()
    #print('best_match_rows:', best_match_rows, 'best_match_score:',best_match_score)

    #best_match_rows, best_ssim, best_mse_sequence = find_best_row(five_best_row, mse_for_best_rows, ssim_for_best_rows, best_match_count)
    print('Best row count:',best_match_rows, 'best_ssim:',best_ssim, 'best_mse_sequence:',best_mse_sequence)

    best_earlier_segment.show()
    best_later_segment.show()
    return best_match_rows, best_match_score, mse

def is_match(segment1, segment2):
    # Simple pixel-wise comparison; can be replaced with more sophisticated methods
    diff = ImageChops.difference(segment1, segment2)
    stat = ImageStat.Stat(diff)
    result = sum(stat.sum)
    #print('sum(stat.sum):',result)
    return result

# Function to calculate both MSE and SSIM for a pair of image segments
def cv2_is_match(earlier_segment_np, later_segment_np, height):
    # Your existing implementation
    mse = np.mean((earlier_segment_np - later_segment_np) ** 2)

    # Convert images to grayscale for SSIM calculation
    earlier_gray = cv2.cvtColor(earlier_segment_np, cv2.COLOR_RGB2GRAY)
    later_gray = cv2.cvtColor(later_segment_np, cv2.COLOR_RGB2GRAY)

    # Calculate SSIM
    if height > 6:
        ssim = compare_ssim(earlier_gray, later_gray)
    else:
        ssim = -1

    return mse, ssim


def find_matching_rows2(earlier_image, later_image, speaker_color1, speaker_color2, text_color, first_snippet, second_snippet):
    earlier_image = Image.open(os.path.join(image_folder, earlier_image))
    later_image = Image.open(os.path.join(image_folder, later_image))

    if earlier_image.height < 1335:
        # Dainis' images = 1334 height
        header_size = 130
        footer_size = 90
    else:
        # Dacite's images = 1920 height
        header_size = 187
        footer_size = 163

    # Step 1: Identify 5 Best Rows for Potential Match
    five_best_rows, offset = find_five_best_matching_rows(earlier_image, later_image, header_size, footer_size, speaker_color1, speaker_color2, text_color)

    # Step 2: Image Comparisons for Each Best Row
    best_match_info = compare_for_best_match(earlier_image, later_image, five_best_rows, header_size, footer_size, offset, first_snippet, second_snippet)

    # Step 3: Selecting the Best Match
    best_row, best_ssim, best_mse, best_height = select_best_match(best_match_info)

    return best_row, best_ssim, best_mse, best_height

def find_bottom_row_with_colours(earlier_image, earlier_height, footer_size, earlier_width, speaker_color1, speaker_color2, text_color):
    # Look for a row from bottom that has black from text of a message and either white or green from the text bubble.
    if earlier_image.height < 1335:
        # Dainis' images = 1334 height
        max_offset = 50
        pixel_threshold = 100
    else:
        # Dacite's images = 1920 height
        max_offset = 72
        pixel_threshold = 150

    for offset in range(0, max_offset):
        # Extract the bottom row (excluding the footer)
        bottom_row = earlier_image.crop(
            (0, earlier_height - footer_size - offset, earlier_width, earlier_height - footer_size + 1 - offset))
        bottom_row_pixels = np.array(bottom_row)
        #bottom_row.show()

        # Count matching pixels for the specified colors
        color1_count = count_matching_color_pixels(bottom_row_pixels, speaker_color1)
        color2_count = count_matching_color_pixels(bottom_row_pixels, speaker_color2)
        text_color_count = count_matching_color_pixels(bottom_row_pixels, text_color)

        if (color1_count > pixel_threshold or color2_count > pixel_threshold) and text_color_count >pixel_threshold:
            return bottom_row_pixels, offset

    # If we reach here, none of the rows had sufficient black and text bubble colour to look like a good comparison row
    # Use the lowest row.
    offset = 0
    bottom_row = earlier_image.crop(
        (0, earlier_height - footer_size - offset, earlier_width, earlier_height - footer_size + 1 - offset))
    bottom_row_pixels = np.array(bottom_row)
    return bottom_row_pixels, offset

def find_five_best_matching_rows(earlier_image, later_image, header_size, footer_size, speaker_color1, speaker_color2, text_color):
    later_height = later_image.height
    later_width = later_image.width
    earlier_height = earlier_image.height
    earlier_width = earlier_image.width
    if earlier_height < 1335:
        # Dainis' images = 1334 height
        pixel_threshold = 100
    else:
        # Dacite's images = 1920 height
        pixel_threshold = 150

    # Find a row near bottom to use for looking for a match in other images.
    bottom_row_pixels, offset = find_bottom_row_with_colours(earlier_image, earlier_height, footer_size, earlier_width, speaker_color1,
                                 speaker_color2, text_color)

    # Initialize a list to store MSE, row index, and color counts
    mse_list = []

    # Compare the bottom row with every other row (excluding the header and footer)
    for row in range(header_size, later_height - footer_size):
        current_row_pixels = np.array(later_image.crop((0, row, later_width, row + 1)))
        mse = np.mean((bottom_row_pixels - current_row_pixels) ** 2)

        # Count matching pixels for the specified colors
        color1_count = count_matching_color_pixels(current_row_pixels, speaker_color1)
        color2_count = count_matching_color_pixels(current_row_pixels, speaker_color2)

        mse_list.append((mse, row, color1_count, color2_count))

    # Sort the list by MSE
    mse_list.sort(key=lambda x: x[0])

    # Select the best rows ensuring color criteria
    best_rows = []
    for mse, row, color1_count, color2_count in mse_list:
        if len(best_rows) < 5:
            if color1_count > pixel_threshold or color2_count > pixel_threshold or len(best_rows) < 3:
                best_rows.append(row)
        else:
            break

    return best_rows, offset

def compare_for_best_match(earlier_image, later_image, best_rows, header_size, footer_size, offset, first_snippet, second_snippet):
    comparison_results = []

    for row in best_rows:
        # Create image segments
        later_segment = later_image.crop((0, header_size, later_image.width, row + 1 + offset))
        later_segment_height = later_segment.height
        earlier_segment = earlier_image.crop((0, earlier_image.height - later_segment.height - footer_size, earlier_image.width, earlier_image.height- footer_size))
        #earlier_segment.show()
        #later_segment.show()

        # Convert PIL Image objects to NumPy arrays
        earlier_segment_np = np.array(earlier_segment)
        later_segment_np = np.array(later_segment)

        # Calculate MSE and SSIM
        mse, ssim = cv2_is_match(earlier_segment_np, later_segment_np, later_segment.height)
        print('rows:',row,'mse:',mse, 'ssim:',ssim)

        # Append results to the list
        comparison_results.append((row, ssim, mse, later_segment_height))
        #SnippetOverlap.objects.create(first_snippet=first_snippet, second_snippet=second_snippet,
        #                              overlaprowcount=later_segment_height, mse_score=mse, ssim_score=ssim)

    return comparison_results

def select_best_match(comparison_results):
    # Check if all segments are at least 7 pixels in height
    all_segments_tall_enough = all(row + 1 >= 7 for row, _, _, _ in comparison_results)

    # Initialize variables to store the best match information
    best_row = None
    best_ssim = -1 if all_segments_tall_enough else None  # Only relevant if all segments are tall enough
    best_mse = float('inf')
    best_height = 0

    for row, ssim, mse, height in comparison_results:
        # Use SSIM for comparison if all segments are at least 7 pixels high
        if all_segments_tall_enough:
            if ssim > best_ssim:
                best_ssim = ssim
                best_mse = mse
                best_row = row
                best_height = height
        else:
            # Otherwise, use MSE for all comparisons
            if mse < best_mse:
                best_mse = mse
                best_row = row
                best_ssim = ssim  # Storing the corresponding SSIM score for reference
                best_height = height

    return best_row, best_ssim, best_mse, best_height


# Function to display two images side by side for sequence confirmation
def display_images_for_confirmation(image_path1, image_path2, overlap=True, confirm_callback=None, not_in_sequence_callback=None, show_next_callback=None):
    def close_window():
        root.destroy()

    def confirm_and_proceed():
        if confirm_callback:
            confirm_callback()
        root.destroy()

    def not_in_sequence():
        if not_in_sequence_callback:
            not_in_sequence_callback()
        root.destroy()

    def show_next():
        if show_next_callback:
            show_next_callback()
        root.destroy()

    root = tk.Tk()
    root.title("Image Comparison")

    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()


    image1 = Image.open(os.path.join(image_folder, image_path1))
    image2 = Image.open(os.path.join(image_folder, image_path2))

    if overlap:
        # [Overlap logic here - same as before]
        overlap_fraction = 0.25  # 20% overlap
        overlap_height = int(min(image1.height, image2.height) * overlap_fraction)

        total_width = image1.width + image2.width
        # Height of the new image is the height of the first image plus the non-overlapping part of the second image
        max_height = image1.height + image2.height - overlap_height

        # Create a new image with enough space to accommodate both images
        new_im = Image.new('RGB', (total_width, max_height))

        # Paste the first image at the top-left
        new_im.paste(image1, (0, 0))

        # Calculate the y-offset for the second image
        y_offset = image1.height - overlap_height

        # Paste the second image on the right, aligned to the overlap
        new_im.paste(image2, (image1.width, y_offset))
        pass
    else:
        # Side by side mode without overlap
        total_width = image1.width + image2.width
        max_height = max(image1.height, image2.height)
        new_im = Image.new('RGB', (total_width, max_height))
        new_im.paste(image1, (0, 0))
        new_im.paste(image2, (image1.width, 0))

    # Estimate the space for the button (adjust this value as needed)
    estimated_button_height = 50  # pixels

    # Calculate scaling factor to fit the image and button on the screen
    scale_width = screen_width / new_im.width
    scale_height = (screen_height - estimated_button_height) / (new_im.height*1.1)
    scale_factor = min(scale_width, scale_height)

    # Resize the image using the scale factor
    resized_im = new_im.resize((int(new_im.width * scale_factor), int(new_im.height * scale_factor)),
                                   Image.Resampling.LANCZOS)

    # Image Label
    tk_image = ImageTk.PhotoImage(resized_im)
    label = tk.Label(root, image=tk_image)
    label.pack(side="top", fill="both", expand=True)

    # Buttons "Show next" or "Not in sequence" or "Correct sequence"

    show_next_button = tk.Button(root, text="Show next", command=show_next)
    show_next_button.pack(side="bottom")

    # Not In Sequence Button
    not_in_sequence_button = tk.Button(root, text="Not in Sequence", command=not_in_sequence)
    not_in_sequence_button.pack(side="bottom")

    # Confirm Button
    confirm_button = tk.Button(root, text="Correct sequence", command=confirm_and_proceed)
    confirm_button.pack(side="bottom")

    root.geometry("+1200+0")

    root.mainloop()

def display_image_segments_for_confirmation(img_segment1, img_segment2):
    secondary_root = Toplevel()  # Use Toplevel for secondary windows
    secondary_root.title("Image Segment Comparison")

    tk_image1 = ImageTk.PhotoImage(img_segment1)
    tk_image2 = ImageTk.PhotoImage(img_segment2)

    label1 = tk.Label(secondary_root, image=tk_image1)
    label1.image = tk_image1
    label1.pack(side="left", fill="both", expand=True)

    label2 = tk.Label(secondary_root, image=tk_image2)
    label2.image = tk_image2
    label2.pack(side="left", fill="both", expand=True)

    secondary_root.geometry("+0+0")  # Set initial position

    # Update the root to draw the window, but don't block the script
    secondary_root.update_idletasks()
    secondary_root.update()

    return secondary_root  # Return the root object to be able to close it later

def on_comparison_confirmed():
    # Code to handle what happens after the comparison is confirmed
    print(f"The image sequence was confirmed as part of the sequence.")
    global images_in_sequence
    images_in_sequence = True
    awaiting_user_feedback = False

def on_not_in_sequence_confirmed():
    print("The images are indicated to NOT be in sequence.")
    global images_in_sequence
    images_in_sequence = False
    awaiting_user_feedback = False

def on_show_next():
    print("Show next comparison images.")
    global show_next
    show_next = True
    awaiting_user_feedback = False


def get_image_part(image, part='top', strip_height=50):
    """
    Get the top or bottom part of an image, cropping the first 100 and last 100 pixels.
    """
    if part == 'top':
        return image.crop((0, 140, image.width, 140 + strip_height))
    elif part == 'bottom':
        return image.crop((0, image.height - 90 - strip_height, image.width, image.height - 90))
    else:
        raise ValueError("Part must be 'top' or 'bottom'")

def compare_image_parts(img_part1, img_part2, img_path1, img_path2):
    """
    Compare two image parts to check if they are similar enough to be considered as continuous.
    Return the comparison result and the Tkinter window.
    """
    # This threshold can be adjusted based on how sensitive you want the comparison to be
    difference_threshold = 5
    diff = ImageChops.difference(img_part1, img_part2)
    stat = ImageStat.Stat(diff)

    # Sum the differences across all channels
    total_difference = sum(stat.sum)

    # Display the images using Tkinter and get the window object
    #image_window = display_image_segments_for_confirmation(img_part1, img_part2)

    # Return the comparison result (True if the difference is less than the threshold) and the Tkinter window
    return total_difference < difference_threshold


def find_matching_sequence(image_path, confirmed_sequences, sequence_number, strip_height=50):
    """
    Find the matching sequence for the given image and display images being compared.
    """
    print('Visual comparison with prior sequences...')
    new_image = Image.open(image_path)
    images_in_sequence = False
    #new_image_top = get_image_part(new_image, 'top', strip_height)
    #new_image_bottom = get_image_part(new_image, 'bottom', strip_height)

    for seq_num, seq_images in confirmed_sequences.items():
        last_image_path = seq_images[-1]
        last_image = Image.open(last_image_path)
        #last_image_bottom = get_image_part(last_image, 'bottom', strip_height)

        first_image_path = seq_images[0]
        first_image = Image.open(first_image_path)
        #first_image_top = get_image_part(first_image, 'top', strip_height)

        # Check that this is not a comparison between identical images.
        if first_image_path != last_image_path:
            # Display and then check if the new image follows the last image in the sequence
            overlap_height = find_matching_rows(last_image_path, image_path)
            if overlap_height > 3:
                print(f"The new image follows the sequence {seq_num}.")
                display_images_for_confirmation(last_image_path, image_path, overlap=True,
                                                confirm_callback=on_comparison_confirmed,
                                                not_in_sequence_callback=on_not_in_sequence_confirmed,
                                                show_next_callback=on_show_next)
                return seq_num, 'follows'
            # Check if the new image precedes the first image in the sequence
            overlap_height = find_matching_rows(image_path, first_image_path)
            if overlap_height > 3:
                print(f"The new image precedes the sequence {seq_num}.")
                display_images_for_confirmation(last_image_path, image_path, overlap=True,
                                                confirm_callback=on_comparison_confirmed,
                                                not_in_sequence_callback=on_not_in_sequence_confirmed,
                                                show_next_callback=on_show_next)

                return seq_num, 'precedes'
    if images_in_sequence == False:
        sequence_number += 1
        confirmed_sequences[sequence_number] = []
        confirmed_sequences[sequence_number].append(image_path)
        pass

    print('The new image was not matched to any existing sequence.')
    return None, None

def filter_text_above_threshold(ocr_results, y_threshold, image_height):
    filtered_results = []

    for bounding_box, text, confidence in ocr_results:
        # Check if all y-coordinates in the bounding box are above the threshold
        if all(y > y_threshold for x, y in bounding_box) and all(y < (image_height - y_threshold) for x, y in bounding_box):
            filtered_results.append((bounding_box, text, confidence))

    return filtered_results

def ocr_image(filename, image_folder):
    filename_with_path = os.path.join(image_folder, filename)
    raw_path = filename_with_path.replace('\\', '\\\\')
    print('OCR being performed on', filename)
    #img = cv2.imread(raw_path)
    #if img is None:
    #    raise ValueError(f"Unable to open image file: {raw_path}")

    reader = easyocr.Reader(['lv'])  # Latvian language

    # Perform OCR
    result = reader.readtext(raw_path)
    #print('result:',result)
    return result

def is_valid_24_hour_time(time_string):
    # Regular expression for matching 24-hour time format (HH:MM)
    #cleaned_time_string = time_string.replace('.', ':')
    #cleaned_time_string = time_string.replace(',', ':')
    returned_text = time_string

    pattern = r'^([01]?[0-9]|2[0-3])[:.;80oOB%@&]([0-5][0-9])$'
    result = bool(re.match(pattern, time_string))

    if result == True:
        # Replace the third character with a colon.
        returned_text = re.sub(pattern, r'\1:\2', time_string)
    else:
        # Let's check if we have a malformed timestring with 1-2 digits, a separator and 1-2 digits and nothing more.
        pattern = r'^\d{1,2}[:.;%@&]\d{1,2}$'
        result = bool(re.match(pattern, time_string))
        if result == True:
            print('Malformed timestamp seen. Has 2-4 digits separated by some separator...')
            returned_text = ""

    if len(time_string) <4:
        #print('= text =: =',time_string,'=')
        pattern = r'^([01]?[0-9]|2[0-3])[:.;80oOB%@&]'
        if bool(re.match(pattern, time_string[:3])):
            print('3 character timestamp seen...')
            # we probably have a partial time_string.
            returned_text = ""
            result = True

    # Using regex to match the pattern with the input string
    return returned_text, result

def read_dow(text):
    # Function to determine which day of the week is being communicated in the text box.
    text_start = text[:3]
    if text_start == "Mon":
        dow = '1'
    elif text_start == "Tue":
        dow = '2'
    elif text_start == "Wed":
        dow = '3'
    elif text_start == "Thu":
        dow = '4'
    elif text_start == "Fri":
        dow = '5'
    elif text_start == "Sat":
        dow = '6'
    elif text_start == "Sun":
        dow = '7'
    else:
        dow = None
    #print('Tested', text, 'as a day of week. DOW=',dow)
    return dow

def add_sentences(new_snippet, sentence_results, image_saved_by):

    if image_saved_by == "Dainis":
        centerpoint_left = 370
        centerpoint_right = 380
        left_most_place_for_right_bubble = 90
        left_most_place_for_left_bubble = int((80/1080)*750)
        reply_offset = int((17/1080)*750)
    else:
        centerpoint_left = 530
        centerpoint_right = 550
        left_most_place_for_right_bubble = int(90*1080/750)
        left_most_place_for_left_bubble = 80
        reply_offset = 17

    # Loop through each sentence found in the image and create a sentence in the database.
    print_debug = True
    print('Looping through OCR text to create sentences...')
    new_setence = False
    sequence = 0
    most_recent_time = None
    sentence_text = ""
    replying_to_text = ""
    min_confidence = 1
    speaker = None
    largest_sentence_x = None
    weekday_text = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun', 'Pir', 'Otr', 'Tre', 'Cet', 'Pie', 'Ses', 'Svē']
    for bounding_box, text, confidence in sentence_results:
        if print_debug:
            print('bounding_box:',bounding_box,'text:', text, 'confidence:',confidence)
        # First check if this looks like a date.
        text, text_as_time = is_valid_24_hour_time(text)
        centerpoint = (bounding_box[0][0] + bounding_box[1][0]) / 2
        week_day_text = text[:3] in weekday_text
        if print_debug:
            print('centerpoint:',centerpoint)
        # Skip text box if it is clearly a label for a speaker's reply.
        if not(text == 'Koris Dainis' or text == 'Dacīte Pence (koris)'):
            if text_as_time == True:
                # This text box is a timestamp for a sentence.
                # Check if there is text for a sentence to save
                if len(sentence_text) > 0:
                    # We have some text for a sentence, so need to save it with the time.
                    # Compute average confidence of the scanned text.
                    if text != "":
                        # Check that the text is a valid date format:
                        pattern = r'^([01]?[0-9]|2[0-3])[:]([0-5][0-9])$'
                        result = bool(re.match(pattern, text))
                        if result == False:
                            # The time is not in correct format.
                            print('Aledgedly this is a time, but it is not formatted correctly. Wiping. Current format:', text,'.')
                            text = ""

                    if print_debug:
                        print('Creating sentence with time',text,'. Sentence:',sentence_text, '. Replying to:', replying_to_text)
                    most_recent_sentence = Sentence.objects.create(speaker=speaker, text=sentence_text, snippet=new_snippet,
                                                                   sequence=sequence, confidence=min_confidence, reply_to_text=replying_to_text)
                    if text != "":
                        most_recent_sentence.time = text
                        most_recent_sentence.save()
                        most_recent_time = text
                    sequence += 1
                    sentence_text = ""
                    replying_to_text = ""
                    # most_recent_sentence.time = text
                    # most_recent_sentence.save()
                    speaker = None
                    min_confidence = 1
                if new_snippet.first_time is None:
                    new_snippet.first_time = text
                    new_snippet.save()

            # Is the text box located where a new day might be communicated?
            # Look at x1 and x2 of the bounding box and determin if it is centered.

            elif centerpoint > centerpoint_left and centerpoint < centerpoint_right and week_day_text:
                # textbox is centered.
                if print_debug:
                    print('Appears to be a centred textbox and text starts with day of week text...')
                day_of_week = read_dow(text)
                new_snippet.weekday = day_of_week
                new_snippet.save()
            elif speaker is None:
                if bounding_box[0][0] > left_most_place_for_right_bubble:
                    if image_saved_by == "Dainis":
                        speaker = "1"
                    else:
                        speaker = "0"
                else:
                    if image_saved_by == "Dainis":
                        speaker = "0"
                    else:
                        speaker = "1"
                if print_debug and speaker == "0":
                    print('Speaker: Dacīte')
                elif print_debug and speaker == "1":
                    print('Speaker: Dainis')
                # Set the largest value of x to the that of this textbox as setence seems to be starting.
                largest_sentence_x = bounding_box[0][0]
                sentence_text = text
                if confidence < min_confidence:
                    min_confidence = confidence
            elif speaker is not None:
                current_x = bounding_box[0][0]
                if current_x < largest_sentence_x - reply_offset and replying_to_text == "":
                    # The x for this text box is more to the left, so we have been gathering text for a reply.
                    if print_debug:
                        print('Previous text seems to be a reply_to text item...')
                    replying_to_text = sentence_text
                    sentence_text = text
                else:
                    if print_debug:
                        print('Continuing current sentence...')
                    sentence_text = sentence_text + ' ' + text
                if confidence < min_confidence:
                    min_confidence = confidence
            else:
                print('Text box did not match any expected positions.')
        else:
            print('Text matched a speaker label in reply_to text. Skipping.')
    # Have completed looping through scanned text.
    # If sentence_text is not None, then there is unsaved sentence that needs to be saved.
    if len(sentence_text) > 0:
        most_recent_sentence = Sentence.objects.create(speaker=speaker, text=sentence_text, snippet=new_snippet, sequence=sequence,
                                                   confidence=min_confidence)
    new_snippet.last_time = most_recent_time
    new_snippet.save()
    return

def recompute_sequences():
    first_snippet_filenames = list(Snippet.objects.filter(place=1).values_list('filename', flat=True))

    # Get the largest place value for each segment
    max_place_per_segment = Snippet.objects.values('segment').annotate(max_place=Max('place'))

    # Iterate over the results to get the corresponding filename for each max place in each segment
    last_snippet_filenames = []
    for entry in max_place_per_segment:
        segment_id = entry['segment']
        max_place = entry['max_place']
        filename = Snippet.objects.filter(segment_id=segment_id, place=max_place).values_list('filename',
                                                                                              flat=True).first()
        if filename:
            last_snippet_filenames.append(filename)

    # Now look for orphans, with either no segment or no place
    snippets_with_either_condition = Snippet.objects.filter(Q(segment__isnull=True) | Q(place__isnull=True))

    # Add these snippets to the files to be compared against for both the start and end of the image.
    for snippet in snippets_with_either_condition:
        last_snippet_filenames.append(snippet.filename)
        first_snippet_filenames.append(snippet.filename)

    return first_snippet_filenames, last_snippet_filenames


def start_new_segment(new_snippet):
    segment_for_snippet = Segment.objects.create(length=1)
    new_snippet.segment = segment_for_snippet
    new_snippet.place = 1
    new_snippet.save()
    return new_snippet

# Main logic
if delete_all:
    # Delete existing records:
    input('You really want to delete all records? Press Enter to continue.')
    deletable_instances=Sentence.objects.all()
    deletable_instances.delete()
    deletable_instances = UserSnippet.objects.all()
    deletable_instances.delete()
    deletable_instances = SnippetOverlap.objects.all()
    deletable_instances.delete()
    deletable_instances = Snippet.objects.all()
    deletable_instances.delete()
    deletable_instances = Segment.objects.all()
    deletable_instances.delete()
    print('Deleted all existing records.')

elif delete_overlaps == True:
    deletable_instances = SnippetOverlap.objects.all()
    deletable_instances.delete()
    all_snippets = Snippet.objects.all()
    deletable_instances = Segment.objects.all()
    deletable_instances.delete()
    for snippet in all_snippets:
        new_segment = Segment.objects.create(length=1)
        snippet.segment = new_segment
        snippet.place = 1
        snippet.save()
    print('Deleted SnippetOverlap records.')

image_folder = "C:\\Users\\db533\\OneDrive\\Koris\\Dacite-Dainis"
print('Creating list of images to process')
#image_files_with_path = [(os.path.join(image_folder, filename), os.path.getmtime(os.path.join(image_folder, filename)))
#               for filename in os.listdir(image_folder) if filename.endswith(".png")]
image_files = [(filename)
                for filename in os.listdir(image_folder) if filename.endswith(".png")]
#image_files_with_path_sorted = sorted(image_files_with_path, key=lambda x: x[1])
image_files_sorted = sorted(image_files, key=lambda x: x[1])
image_count = len(image_files)

# Tests:
#image_files_sorted = [ 'Screenshot_20180224-234128.png']


# User interaction loop
#sequence_number = len(confirmed_sequences) + 1
i = 0
while i < len(image_files_sorted) :
    # Update the first and last image names for each sequence.
    first_snippet_filenames, last_snippet_filenames = recompute_sequences()
    # Check if the image already is processed as a snippet in the database
    filename = image_files_sorted[i]

    # First check if the snippet has been saved and sentences detected.
    if not Snippet.objects.filter(filename=filename).exists():
        print('filename:',filename,'Snippet does not exist.')
        new_snippet = Snippet.objects.create(filename=filename)

        # Read the text on the image
        ocr_result = ocr_image(filename, image_folder)

        # Check size of image to determine where to start filtering
        image = Image.open(os.path.join(image_folder, filename))
        if image.height < 1335:
            filter_threshold = 118
        else:
            filter_threshold = 170

        if 'Screenshot' in filename:
            image_saved_by = 'Dacite'
        else:
            image_saved_by = 'Dainis'
        sentence_results = filter_text_above_threshold(ocr_result, filter_threshold, image.height)
        add_sentences(new_snippet, sentence_results, image_saved_by)

    # Check if overlaps not found. These may have been deleted.
    new_snippet = Snippet.objects.get(filename=filename)
    if not SnippetOverlap.objects.filter(first_snippet=new_snippet).exists():
        # We do not have snippet overlaps defined.
        # If this is the very first snippet, then this is OK.
        if i == 0:
            print('First snippet. Setting to a segment without looking for overlaps.')
            if Segment.objects.count() == 0:
                # No segment exists, so create the first segment.
                segment_for_snippet = Segment.objects.create(length=1)
                new_snippet.segment = segment_for_snippet
                new_snippet.place = 1
            #elif new_snippet.segment is None:
                # Some segments exist in the database, so link the first snippet to the first segemnt
            #    segment_for_snippet = Segment.objects.all().order_by('id').first()
            #else:

            # new_snippet = Snippet.objects.create(place=1, segment=segment_for_snippet, filename=filename)

        else:
            # There is at least 1 snippet already saved in at least 1 segment, but no SnippetOverlaps.
            best_overlap_row_count = 0
            best_ssim_score = -1
            best_mse_score = 999999
            #overlaps_with_filename = []
            #other_image_position = []
            count_matching_overlap_row_count=0
            # first try to match to the end of existing segments.
            print('Comparing to end of segments...')
            for last_filename in last_snippet_filenames:
                assumed_prior_snippet = Snippet.objects.get(filename=last_filename)
                matching_row_count, ssim_score, mse_score, best_height = find_matching_rows2(last_filename, filename, speaker_color1, speaker_color2, text_color, assumed_prior_snippet, new_snippet)
                print('Comparing with', last_filename, ' best_height =', best_height, 'ssim_score =', ssim_score, 'mse_score =',mse_score)
                # Save the overlap to the database.
                SnippetOverlap.objects.create(first_snippet=assumed_prior_snippet, second_snippet=new_snippet,
                                              overlaprowcount=best_height, mse_score=mse_score, ssim_score=ssim_score)
                if ssim_score > best_ssim_score:
                    #count_matching_overlap_row_count = 1
                    #best_overlap_row_count = matching_row_count
                    overlaps_with_filename = last_filename
                    other_image_position = 'prior'
                    best_ssim_score = ssim_score
                elif ssim_score == -1 and mse_score < best_mse_score:
                    overlaps_with_filename = last_filename
                    other_image_position = 'prior'
                    best_mse_score = mse_score
            # then try to match to the start of existing segments.
            print('Comparing to start of segments...')
            for first_filename in first_snippet_filenames:
                assumed_next_snippet = Snippet.objects.get(filename=first_filename)
                matching_row_count, ssim_score, mse_score, best_height =find_matching_rows2(filename, first_filename, speaker_color1, speaker_color2, text_color, new_snippet, assumed_next_snippet)
                print('Comparing with', first_filename, ' best_height =', best_height, 'ssim_score =', ssim_score, 'mse_score =',mse_score)
                # Save the overlap to the database.
                SnippetOverlap.objects.create(first_snippet=new_snippet, second_snippet=assumed_next_snippet,
                                              overlaprowcount=best_height, mse_score=mse_score, ssim_score=ssim_score)
                if ssim_score > best_ssim_score:
                    #count_matching_overlap_row_count = 1
                    #best_overlap_row_count = matching_row_count
                    overlaps_with_filename = first_filename
                    other_image_position = 'next'
                    best_ssim_score = ssim_score
                elif ssim_score == -1 and mse_score < best_mse_score:
                    overlaps_with_filename = first_filename
                    other_image_position = 'next'

            # One snippet pair has a higher number of matching rows in the images.
            # update the segment and place values to include the new image in the chosen sequence.
            if best_ssim_score < 0.7:
                print('No good match to existing segments. Creating new segment.')
                # Image match is poor reliability. Leave as a standalone segment.
                #new_snippet = Snippet.objects.create(place=1, filename=filename)     # Move to earlier part of loop
                new_snippet = start_new_segment(new_snippet)
            else:
                # Sufficient rows match. Should connect to the best matching segment.

                # The prior / next snippet may or may not have a segment associated with it.
                other_snippet = Snippet.objects.get(filename=overlaps_with_filename)  # Replace snippet_id with the actual id of the snippet
                segment_for_other_snippet = other_snippet.segment
                if segment_for_other_snippet is None:
                    # The matched snippet is not yet in a segment. Create a segment for both snippets.
                    segment_for_other_snippet = Segment.objects.create(length=1)
                    other_snippet.segment = segment_for_other_snippet
                    other_snippet.place = 1
                    other_snippet.save()
                if other_image_position == "prior":
                    # The image that was compared comes before this new image. The new image is at the end of the sequence.
                    # Get the place of the compared image.
                    print('Adding snippet to END of segment',segment_for_other_snippet.id)
                    last_place = other_snippet.place
                    #new_snippet = Snippet.objects.create(place=int(last_place)+1, segment=segment_for_other_snippet, filename=filename)
                    new_snippet.place = int(last_place)+1
                    new_snippet.segment = segment_for_other_snippet
                    segment_for_other_snippet.length += 1
                    segment_for_other_snippet.save()
                else:
                    # The new image needs to be placed before the image that it was compared to.
                    # Get all existing snippets for this segment.
                    print('Adding snippet to BEGINNING of segment', segment_for_other_snippet.id)
                    existing_snippets = Snippet.objects.filter(segment=segment_for_other_snippet)
                    for existing_snippet in existing_snippets:
                        existing_snippet.place = existing_snippet.place + 1
                        existing_snippet.save()
                    #new_snippet = Snippet.objects.create(place=1, segment=segment_for_other_snippet, filename=filename)
                    new_snippet.place = 1
                    new_snippet.segment = segment_for_other_snippet
                    segment_for_other_snippet.length += 1
                    segment_for_other_snippet.save()
        new_snippet.save()
    else:
        print('SnippetOverlaps exist, so not looking for overlaps or change of sequence.')

        # Check if time_diff is blank. Might mean that the snippetoverlay is older and needs to have time_diff added.
        current_overlaps = SnippetOverlap.objects.filter(first_snippet=new_snippet)
        for current_snippetoverlay in current_overlaps:
            if current_snippetoverlay.time_diff is None:
                current_snippetoverlay.save()
        current_overlaps = SnippetOverlap.objects.filter(second_snippet=new_snippet)
        for current_snippetoverlay in current_overlaps:
            if current_snippetoverlay.time_diff is None:
                current_snippetoverlay.save()

    i += 1