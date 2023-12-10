import os
import django
import easyocr
import sys
from django.db.models import Max
import re
from django.db.models import Q
from datetime import datetime

from django.conf import settings
# Configure Django settings
sys.path.append('C:\\Users\\db533\\PycharmProjects\\sarakste\\sarakste\\sarakste')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sarakste.settings')  # Replace with your project's settings
django.setup()

# Launch options
delete_overlaps = False
delete_all = True
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

import csv
import tkinter as tk
from tkinter import Toplevel  # Add this line to import Toplevel
from PIL import Image, ImageTk, ImageChops, ImageStat
import os
import time

def find_matching_rows(earlier_image, later_image):
    header_size = 130
    footer_size = 90

    earlier_image = Image.open(os.path.join(image_folder, earlier_image))
    later_image = Image.open(os.path.join(image_folder, later_image))
    #earlier_image.show()
    #later_image.show()

    earlier_height = earlier_image.height
    #print('earlier_height:',earlier_height)
    later_height = later_image.height
    #print('later_height:', later_height)

    feasible_rows = list(range(header_size, later_height - footer_size))
    max_overlap = 0
    best_match_score = 999999999
    prior_match_score = best_match_score


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
                match_score = is_match(earlier_segment, later_segment)/(later_segment_height)
                if match_score < prior_match_score:
                    best_matched_segment = later_segment
                    best_match_rows = later_segment.height
                    best_earlier_segment = earlier_segment
                    best_later_segment = later_segment
                if len(feasible_rows) < 5:
                    print('Rows matched:', later_segment.height, 'match_score:',match_score, 'match_barrier:',match_barrier)
                    if match_score < prior_match_score:
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
                    prior_match_score = match_score
                else:
                    #print('Dropping row',top_row)
                    feasible_rows.remove(top_row)
                pass
            feasible_rows = [x - 1 for x in feasible_rows]
            #print('Rows matched:', later_segment.height)
        else:
            break
    #if best_match_rows == 15 or best_match_rows == 85:
    #best_matched_segment.show()
    #print('best_match_rows:', best_match_rows, 'best_match_score:',best_match_score)
    best_earlier_segment.show()
    best_later_segment.show()
    return best_match_rows, best_match_score

def is_match(segment1, segment2):
    # Simple pixel-wise comparison; can be replaced with more sophisticated methods
    diff = ImageChops.difference(segment1, segment2)
    stat = ImageStat.Stat(diff)
    result = sum(stat.sum)
    #print('sum(stat.sum):',result)
    return result



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

def filter_text_above_threshold(ocr_results, y_threshold):
    filtered_results = []

    for bounding_box, text, confidence in ocr_results:
        # Check if all y-coordinates in the bounding box are above the threshold
        if all(y > y_threshold for x, y in bounding_box):
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
    cleaned_time_string = time_string.replace('.', ':')

    pattern = r'^([01]?[0-9]|2[0-3]):([0-5][0-9])$'
    result = bool(re.match(pattern, cleaned_time_string))

    #print('Tested',time_string,'. Is a time?',result)

    if result == True:
        returned_text = cleaned_time_string
    else:
        returned_text = time_string

    if len(time_string) <4:
        #print('= text =: =',time_string,'=')
        pattern = r'^[0-2][0-9]:'
        if bool(re.match(pattern, time_string[:3])):
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

def add_sentences(new_snippet, sentence_results, filename):
    # Loop through each sentence found in the image and create a sentence in the database.
    print('Looping through OCR text to create sentences...')
    new_setence = False
    sequence = 0
    most_recent_time = None
    sentence_text = ""
    min_confidence = 1
    speaker = None
    for bounding_box, text, confidence in sentence_results:
        #print('bounding_box:',bounding_box,'text:', text, 'confidence:',confidence)
        # Determine the type of text box based on location:
        # text is formatted as a time = time
        # (x1 + x2) is between 740 and 760 = Day of week
        # x1 > 150 = Dainis
        # x1 < 50 = Dacīte

        # First check if this looks like a date.
        text, text_as_time = is_valid_24_hour_time(text)
        centerpoint = (bounding_box[0][0] + bounding_box[1][0]) / 2
        #print('centerpoint:',centerpoint)
        if text_as_time == True:
            # This text box is a timestamp for a sentence.
            # Check if there is text for a sentence to save
            if len(sentence_text) > 0:
                # We have some text for a sentence, so need to save it with the time.
                # Compute average confidence of the scanned text.
                #print('Creating sentence with time',text,'. Sentence:',sentence_text)
                most_recent_sentence = Sentence.objects.create(speaker=speaker, text=sentence_text, snippet=new_snippet,
                                                               sequence=sequence, confidence=min_confidence)
                if text != "":
                    most_recent_sentence.time = text
                    most_recent_sentence.save()
                    most_recent_time = text
                sequence += 1
                sentence_text = ""
                # most_recent_sentence.time = text
                # most_recent_sentence.save()
                speaker = None
                min_confidence = 1
            if new_snippet.first_time is None:
                new_snippet.first_time = text
                new_snippet.save()

        # Is the text box located where a new day might be communicated?
        # Look at x1 and x2 of the bounding box and determin if it is centered.
        elif centerpoint > 370 and centerpoint < 380:
            # textbox is centered.
            #print('Appears to be a centred textbox...')
            day_of_week = read_dow(text)
            new_snippet.weekday = day_of_week
            new_snippet.save()
        elif speaker is None:
            if bounding_box[0][0] > 130:
                #print('Speaker: Dainis')
                speaker = "1"
            else:
                #print('Speaker: Dacīte')
                speaker = "0"
            sentence_text = text
            if confidence < min_confidence:
                min_confidence = confidence
        elif speaker is not None:
            sentence_text = sentence_text + ' ' + text
            if confidence < min_confidence:
                min_confidence = confidence
            #else:
            #    # This is the start of a new sentence and prior sentence has not been saved yet.
            #    print('No time, but new speaker. Creating sentence:', sentence_text)
            #    most_recent_sentence = Sentence.objects.create(speaker=speaker, text=sentence_text, snippet=new_snippet,
            #                                                       sequence=sequence, confidence=min_confidence)
            #    sequence += 1
            #    # Start a fresh sentence
            #    sentence_text = text
            #    min_confidence = confidence
            #    speaker = "1"
        #elif bounding_box[0][0] < 70:
        #    print('Speaker: Dacīte')
        #    if speaker is None or speaker == "0":
        #        if len(sentence_text) > 0:
        #            sentence_text = sentence_text + ' ' + text
        #        else:
        #            sentence_text = text
        #        speaker = "0"
                # Check if this text has lower confidence
        #        if confidence < min_confidence:
        #            min_confidence = confidence
        #    else:
        #        # This is the start of a new sentence and prior sentence has not been saved yet.
        #        print('No time, but new speaker. Creating sentence:', sentence_text)
        #        most_recent_sentence = Sentence.objects.create(speaker=speaker, text=sentence_text, snippet=new_snippet,
        #                                                           sequence=sequence, confidence=min_confidence)
        #        sequence += 1
        #        # Start a fresh sentence
        #        sentence_text = text
        #        min_confidence = confidence
        #        speaker = "0"
        else:
            print('Text box did not match any expected positions.')
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

# User interaction loop
#sequence_number = len(confirmed_sequences) + 1
i = 0
while i < len(image_files_sorted) - 1:
    # Update the first and last image names for each sequence.
    first_snippet_filenames, last_snippet_filenames = recompute_sequences()
    # Check if the image already is processed as a snippet in the database
    filename = image_files_sorted[i]

    # If we have no snippets saved, save it without attempting to visually sequence it.
    #if Snippet.objects.count() == 0:
    #    if Segment.objects.count() == 0:
    #        # No segment exists, so create the first segment.
    #        segment_for_snippet = Segment.objects.create(length=1)
    #    else:
    #        # Some segments exist in the database, so link the first snippet to the first segemnt
    #        segment_for_snippet = Segment.objects.get(id=1)
    #    # new_snippet = Snippet.objects.create(place=1, segment=segment_for_snippet, filename=filename)
    #    new_snippet.segment = segment_for_snippet

    # First check if the snippet has been saved and sentences detected.
    if not Snippet.objects.filter(filename=filename).exists():
        print('filename:',filename,'Snippet does not exist.')
        new_snippet = Snippet.objects.create(filename=filename)

        # Read the text on the image
        ocr_result = ocr_image(filename, image_folder)
        sentence_results = filter_text_above_threshold(ocr_result, 118)
        add_sentences(new_snippet, sentence_results, filename)

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
            overlaps_with_filename = []
            other_image_position = []
            count_matching_overlap_row_count=0
            # first try to match to the end of existing segments.
            print('Comparing to end of segments...')
            for last_filename in last_snippet_filenames:
                assumed_prior_snippet = Snippet.objects.get(filename=last_filename)
                matching_row_count, match_score =find_matching_rows(last_filename, filename)
                print('Comparing with', last_filename, ' matching_row_count =', matching_row_count, 'match_score =', match_score)
                # Save the overlap to the database.
                SnippetOverlap.objects.create(first_snippet=assumed_prior_snippet, second_snippet=new_snippet,
                                              overlaprowcount=matching_row_count)
                if matching_row_count > best_overlap_row_count:
                    count_matching_overlap_row_count = 1
                    best_overlap_row_count = matching_row_count
                    overlaps_with_filename = [last_filename]
                    other_image_position = ['prior']
                elif matching_row_count == best_overlap_row_count:
                    count_matching_overlap_row_count +=1
                    overlaps_with_filename.append(last_filename)
                    other_image_position.append('prior')

            # then try to match to the start of existing segments.
            print('Comparing to start of segments...')
            for first_filename in first_snippet_filenames:
                assumed_next_snippet = Snippet.objects.get(filename=first_filename)
                matching_row_count, match_score =find_matching_rows(filename, first_filename)
                print('Comparing with', first_filename, ' matching_row_count =', matching_row_count, 'match_score =', match_score)
                # Save the overlap to the database.
                SnippetOverlap.objects.create(first_snippet=new_snippet, second_snippet=assumed_next_snippet,
                                              overlaprowcount=matching_row_count)
                if matching_row_count > best_overlap_row_count:
                    count_matching_overlap_row_count = 1
                    best_overlap_row_count = matching_row_count
                    overlaps_with_filename = [first_filename]
                    other_image_position = ['next']
                elif matching_row_count == best_overlap_row_count:
                    count_matching_overlap_row_count +=1
                    overlaps_with_filename.append(first_filename)
                    other_image_position.append('next')
            resolve_multiple_matches_with_same_row_count = False
            if count_matching_overlap_row_count > 1 and resolve_multiple_matches_with_same_row_count == True:
                visual_compare = False
                # Several overlaps have same value.
                # Choose the one with the smallest time difference between last_time and first_time
                # Loop through each overlap with matching row count.
                print('Picking sequence based on time difference as multiple images have same overlapping row count.')
                best_j_overlap_time_difference = 24*60*60
                best_j = None
                removed_count=0
                time_compare = False
                if time_compare == True:
                    for j in len(overlaps_with_filename):
                        overlapping_filename = overlaps_with_filename[j]
                        overlap_sequence = other_image_position[j]
                        if overlap_sequence == "prior":
                            snippet1 = Snippet.objects.get(filename=overlapping_filename)
                            last_time_snippet1 = snippet1.last_time
                            first_time_snippet2 = new_snippet.first_time
                        else:
                            snippet2 = Snippet.objects.get(filename=overlapping_filename)
                            last_time_snippet1 = new_snippet.last_time
                            first_time_snippet2 = snippet2.first_time
                        time_format = '%H:%M'
                        last_time_snippet1_dt = datetime.strptime(last_time_snippet1.strftime(time_format), time_format)
                        first_time_snippet2_dt = datetime.strptime(first_time_snippet2.strftime(time_format),
                                                                   time_format)
                        time_difference = abs(first_time_snippet2_dt - last_time_snippet1_dt)
                        if time_difference > best_j_overlap_time_difference:
                            best_j_overlap_time_difference = time_difference
                            best_j = j
                    overlaps_with_filename = [overlaps_with_filename[j]]
                    other_image_position = [other_image_position[j]]
                # Now there is just one filename in overlaps_with_filename
                elif visual_compare == True:
                    # More than one snippet has the same number of overlapping rows. Need to visually compare to determine if any sequence should be determined.
                    # Might be no overlapping rows.
                    # First reset flag to indicate that should skip to next pair.
                    global show_next, awaiting_user_feedback
                    show_next = True
                    # Loop through each possible sequence of best matching images.
                    print('Visual comparison of',count_matching_overlap_row_count,'images needed for confirming sequence.')
                    i = 0
                    while True:
                        overlapping_filename = overlaps_with_filename[i]
                        overlap_sequence = other_image_position[i]
                        linked_snippet_instance = Snippet.objects.get(filename=overlapping_filename)  # Replace snippet_id with the actual id of the snippet
                        linked_segment_instance = linked_snippet_instance.segment
                        print('i:',i,'overlapping_filename:',overlapping_filename, 'overlap_sequence:',overlap_sequence)
                        if overlap_sequence == 'prior':
                            image1_time = linked_snippet_instance.last_time
                            image2_time = new_snippet.first_time
                            sequence_correct = image1_time <= image2_time
                            print('Last time on first image:',image1_time, 'First time on second image:', image2_time, 'Sequence correct?',sequence_correct)
                            display_images_for_confirmation(overlapping_filename, filename, overlap=True,
                                                    confirm_callback=on_comparison_confirmed,
                                                    not_in_sequence_callback=on_not_in_sequence_confirmed,
                                                    show_next_callback=on_show_next)
                        else:
                            image1_time = new_snippet.last_time
                            image2_time = linked_snippet_instance.first_time
                            sequence_correct = image1_time <= image2_time
                            print('Last time on first image:',image1_time, 'First time on second image:', image2_time, 'Sequence correct?',sequence_correct)
                            display_images_for_confirmation(filename, overlapping_filename, overlap=True,
                                                            confirm_callback=on_comparison_confirmed,
                                                            not_in_sequence_callback=on_not_in_sequence_confirmed,
                                                    show_next_callback=on_show_next)
                        print('Awaiting user feedback...')
                        while awaiting_user_feedback == True:
                            pass
                        if show_next == True:
                            # User asked to cycle to the next image for comparison.
                            i+=1
                            # Check if all viable matches have been shown, if so, start at the beginning.
                            if i == len(overlaps_with_filename):
                                i=0
                        elif images_in_sequence == False:
                            # User is has indicated that this is not a valid sequence.
                            # drop the filename from the list of viable sequences.
                            overlaps_with_filename.pop(i)
                            other_image_position.pop(i)
                            if len(overlaps_with_filename) == 0:
                                # All potential sequences have been rejected. Save the snippet as a new, separate segment.
                                new_snippet = start_new_segment(new_snippet)
                                break

                        elif images_in_sequence == True:
                            # User confirms this is a valid sequence.
                            if overlap_sequence == "prior":
                                # The new image is the final image in an existing segment.
                                print('Adding snippet to END of segment', segment_instance.id)
                                # Find the maximum place value for Snippets connected to this segment.
                                max_place = Snippet.objects.filter(segment=linked_segment_instance).aggregate(Max('place'))

                                # Extracting the maximum value
                                max_place_value = max_place['place__max']

                                # Set the place to be +1 to this max value.
                                new_snippet.place = max_place_value+1
                                new_snippet.segment=segment_instance

                            else:
                                # The new image is the first in an existing sequence.
                                # Need to update the place values for all existing snippets mapped to this segment.
                                print('Adding snippet to BEGINNING of segment',segment_instance.id)
                                existing_snippets = Snippet.objects.filter(segment=linked_segment_instance)
                                for existing_snippet in existing_snippets:
                                    existing_snippet.place = existing_snippet.place + 1
                                    existing_snippet.save()
                                new_snippet.place = 1
                                new_snippet.segment = segment_instance
                            new_snippet.save()
                            break

                        # Highlight if sequence of times for messages suggests correct sequence or wrong sequence.
                        # Buttons "Show next" or "Not in sequence" or "Correct sequence"
                    # If one sequence is confirmed, update the segment and place values to include the new image in the chosen sequence.
                    # If no seqeunce is confirmed i.e. all pairs are ruled out, then create a new segment for this image.
                    pass
                else:
                    # Neither time_compare, not visual_compare active.
                    # Since no one image had a greater number of matching rows, then place snippet in its own segment.
                    print('Saving snippet into a new segment.')
                    new_segment = Segment.objects.create(length=1)
                    new_snippet.segment = new_segment
                    new_snippet.place = 1
            # One snippet pair has a higher number of matching rows in the images.
            # update the segment and place values to include the new image in the chosen sequence.
            if best_overlap_row_count <4:
                # Too few rows to be a significant image overlap
                #new_snippet = Snippet.objects.create(place=1, filename=filename)     # Move to earlier part of loop
                new_snippet = start_new_segment(new_snippet)
            else:
                # Sufficient rows match.
                current_segment = new_snippet.segment
                if current_segment is not None:
                    count_in_current_segment = Snippet.objects.filter(segment=current_segment).count()
                else:
                    count_in_current_segment = 0
                if count_matching_overlap_row_count == 1:
                    # Only one image has the best row count.
                    # First check if the new_snippet is in a segment on its own (no other images).
                    if count_in_current_segment == 1:
                        # This image is the only one in this segment, so the segment will be empty once the image is attached to another segment.
                        print('Deleteing segment',current_segment.id, 'as this image was the only one in this segment and it is about to be attached to another segment.')
                        current_segment.delete()
                    other_snippet = Snippet.objects.get(filename=overlaps_with_filename[0])  # Replace snippet_id with the actual id of the snippet
                    segment_for_other_snippet = other_snippet.segment
                    if other_image_position[0] == "prior":
                        # The image that was compared comes before this new image. The new image is at the end of the sequence.
                        # Get the place of the compared image.
                        print('Adding snippet to END of segment',segment_for_other_snippet.id)
                        last_place = other_snippet.place
                        #new_snippet = Snippet.objects.create(place=int(last_place)+1, segment=segment_for_other_snippet, filename=filename)
                        new_snippet.place = int(last_place)+1
                        new_snippet.segment = segment_for_other_snippet
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
                else:
                    # Multiple images have matching row count.
                    if count_in_current_segment == 0:
                        print('Saving snippet into a new segment.')
                        new_segment = Segment.objects.create(length=1)
                        new_snippet.segment = new_segment
                        new_snippet.place = 1
                        new_snippet.save()
                    else:
                        print('Should already be in its own segment.')
        new_snippet.save()
    else:
        print('SnippetOverlaps exist, so not looking for overlaps or change of sequence.')
    i += 1