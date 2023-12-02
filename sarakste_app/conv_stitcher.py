import environ
from django.conf import settings
from myapp.models import Snippet  # Replace 'myapp' with your app name

env = environ.Env()
environ.Env.read_env(overwrite=True)
# Get the IP address of this host
DEBUG = env.bool('debug', default=False)
import socket
hostname = socket.gethostname()
IP = socket.gethostbyname(hostname)
HOSTED = env.bool('HOSTED', default=False)
print('HOSTED:',HOSTED)
if HOSTED:
    # .envfilestatesthisenvironmentishosted,sousetheretrievedIPaddress.
    host_ip = IP
    db_name = env.str('MYSQL_PROD_DB_NAME')
    db_user = env.str('MYSQL_PROD_DB_USER')
    db_pwd = env.str('MYSQL_PROD_PWD')
else:
    host_ip = '127.0.0.1'
    db_name = env.str('MYSQL_LOCAL_DB_NAME')
    db_user = env.str('MYSQL_LOCAL_DB_USER')
    db_pwd = env.str('MYSQL_LOCAL_PWD')





import csv
import tkinter as tk
from tkinter import Toplevel  # Add this line to import Toplevel
from PIL import Image, ImageTk, ImageChops, ImageStat
import os
import time

def find_matching_rows(earlier_image_path, later_image_path):
    header_size = 130
    footer_size = 90

    earlier_image = Image.open(earlier_image_path)
    later_image = Image.open(later_image_path)
    earlier_image.show()
    later_image.show()

    earlier_height = earlier_image.height
    #print('earlier_height:',earlier_height)
    later_height = later_image.height
    #print('later_height:', later_height)

    feasible_rows = list(range(header_size, later_height - footer_size))
    max_overlap = 0
    best_match_score = 999999999


    for bottom_row in range(earlier_height - footer_size, footer_size-1, -1):  # Start from 90th row from bottom, up to the 90th row
        segment_displayed = False
        min_overlap = 999999999
        earlier_segment = earlier_image.crop((0, bottom_row, earlier_image.width, earlier_height-footer_size+1))
        match_barrier = 10000 #* (1.5 ** earlier_segment.height)
        #print('match_barrier:',match_barrier)
        # Display the earlier_segment image
        #earlier_segment.show()

        if len(feasible_rows) > 0:
            for top_row in feasible_rows[:]:
                later_segment_height = earlier_segment.height
                #print('top_row + later_segment_height:', top_row + later_segment_height)
                #print('later_height - footer_size:', later_height - footer_size)
                #print('Later segment from row', top_row, 'to row', top_row + later_segment_height)
                #if top_row + later_segment_height > later_height - footer_size:
                #    feasible_rows.remove(top_row)
                #    print('Dropped row',top_row)
                #    continue

                later_segment = later_image.crop((0, top_row, later_image.width, top_row + later_segment_height))
                #print('later_segment.height:', later_segment.height)
                #print('later_segment.width:', later_segment.width)

                # Compare segments
                match_score = is_match(earlier_segment, later_segment)/later_segment_height
                if match_score < best_match_score:
                    best_matched_segment = later_segment
                    best_match_rows = later_segment.height
                if len(feasible_rows) < 5:
                    print('Rows matched:', later_segment.height, 'match_score:',match_score, 'match_barrier:',match_barrier)
                    if match_score < best_match_score:
                        best_match_score = match_score
                        best_matched_segment = later_segment
                        #best_matched_segment.show()
                        #earlier_segment.show()
                if match_score < match_barrier:
                    #print('Found a matching segment!')
                        #print('New lowest match_score', min_overlap)
                    #if segment_displayed == False and later_segment.height > 30:
                    #    earlier_segment.show()
                    #    segment_displayed = True
                    #print('match_score:',match_score)
                    #print('Matching row count:', later_segment.height)

                    #print('bottom_row:',bottom_row)
                    #print('top_row:', top_row)
                    max_overlap = max(max_overlap, later_segment_height)
                else:
                    #print('Dropping row',top_row)
                    feasible_rows.remove(top_row)
                pass
            feasible_rows = [x - 1 for x in feasible_rows]
            #print('Rows matched:', later_segment.height)
        else:
            break
    best_matched_segment.show()
    print('best_match_rows:', best_match_rows, 'best_match_score:',best_match_score)
    return best_match_rows

def is_match(segment1, segment2):
    # Simple pixel-wise comparison; can be replaced with more sophisticated methods
    diff = ImageChops.difference(segment1, segment2)
    stat = ImageStat.Stat(diff)
    result = sum(stat.sum)
    #print('sum(stat.sum):',result)
    return result



# Function to display two images side by side for sequence confirmation
def display_images_for_confirmation(image_path1, image_path2, overlap=True, confirm_callback=None, not_in_sequence_callback=None):
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

    root = tk.Tk()
    root.title("Image Comparison")

    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    image1 = Image.open(image_path1)
    image2 = Image.open(image_path2)

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

    # Not In Sequence Button
    not_in_sequence_button = tk.Button(root, text="Not in Sequence", command=not_in_sequence)
    not_in_sequence_button.pack(side="bottom")

    # Confirm Button
    confirm_button = tk.Button(root, text="Confirm and Proceed", command=confirm_and_proceed)
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

def on_not_in_sequence_confirmed():
    print("The images are indicated to NOT be in sequence.")
    global images_in_sequence
    images_in_sequence = False


# Function to save confirmed sequences to CSV
def save_confirmed_sequences_to_csv(confirmed_sequences, csv_file_path):
    with open(csv_file_path, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        for key, value in confirmed_sequences.items():
            writer.writerow([key] + value)

# Function to load confirmed sequences from CSV
def load_confirmed_sequences_from_csv(csv_file_path):
    confirmed_sequences = {}
    try:
        with open(csv_file_path, mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                key = int(row[0])
                confirmed_sequences[key] = row[1:]
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"An error occurred while reading the CSV file: {e}")
    print('confirmed_sequences:')
    print(confirmed_sequences)
    return confirmed_sequences

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
                                                not_in_sequence_callback=on_not_in_sequence_confirmed)
                return seq_num, 'follows'
            # Check if the new image precedes the first image in the sequence
            overlap_height = find_matching_rows(image_path, first_image_path)
            if overlap_height > 3:
                print(f"The new image precedes the sequence {seq_num}.")
                display_images_for_confirmation(last_image_path, image_path, overlap=True,
                                                confirm_callback=on_comparison_confirmed,
                                                not_in_sequence_callback=on_not_in_sequence_confirmed)

                return seq_num, 'precedes'
    if images_in_sequence == False:
        sequence_number += 1
        confirmed_sequences[sequence_number] = []
        confirmed_sequences[sequence_number].append(image_path)
        pass

    print('The new image was not matched to any existing sequence.')
    return None, None

# Main logic
image_folder = "C:\\Users\\db533\\OneDrive\\Koris\\Dacīte - Dainis"
csv_file_path = 'confirmed_sequences.csv'  # Path to your CSV file
confirmed_sequences = load_confirmed_sequences_from_csv(csv_file_path)
image_files = [(os.path.join(image_folder, filename), os.path.getmtime(os.path.join(image_folder, filename)))
               for filename in os.listdir(image_folder) if filename.endswith(".png")]
image_files_sorted = sorted(image_files, key=lambda x: x[1])
image_count = len(image_files)

# User interaction loop
sequence_number = len(confirmed_sequences) + 1
i = 0
while i < len(image_files_sorted) - 1:
    last_image_path = image_files_sorted[i][0]
    next_image_path = image_files_sorted[i + 1][0]
    print('Comparing images', i, 'and', i+1, 'of', image_count)
    images_in_sequence = False
    overlap_height = find_matching_rows(last_image_path, next_image_path)
    if overlap_height >3:
        images_in_sequence = True
    display_images_for_confirmation(last_image_path, next_image_path, overlap=True, confirm_callback=on_comparison_confirmed, not_in_sequence_callback=on_not_in_sequence_confirmed)
    if images_in_sequence == False:
        # Automatically compare the image with the beginning and end of each sequence
        matching_sequence, position = find_matching_sequence(last_image_path, confirmed_sequences, sequence_number)
        if matching_sequence:
            if position == 'follows':
                confirmed_sequences[matching_sequence].append(image_files_sorted[i][0])
            elif position == 'precedes':
                confirmed_sequences[matching_sequence].insert(0, image_files_sorted[i][0])
            print(f"Image was added to sequence {matching_sequence} as it {position} the sequence.")
        else:
            # Start a new sequence
            confirmed_sequences[sequence_number] = [image_files_sorted[i][0]]
            sequence_number += 1
        i += 1
    else:
        if sequence_number not in confirmed_sequences:
            confirmed_sequences[sequence_number] = []
        confirmed_sequences[sequence_number].append(image_files_sorted[i][0])
        if i + 1 < len(image_files_sorted):
            confirmed_sequences[sequence_number].append(image_files_sorted[i + 1][0])
        i += 1  # Increment by 1 to keep the second image as the first of the next pair

    save_confirmed_sequences_to_csv(confirmed_sequences, csv_file_path)

# Handle the last image if it hasn't been processed
if i == len(image_files_sorted) - 1:
    # Logic to handle the last image
    pass

# No stitching and saving to a single image file in this version, since we're handling sequences
