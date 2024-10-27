import os
import re
import cv2
import sys
import json
import datetime
import pytesseract
import tkinter as tk
from tkinter import messagebox
from pdf2image import convert_from_path

# Set the path to the Tesseract executable
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Blobal text array to store the dictionary entries
entries = []

def save_page(text):
    if text[0][0] == '@' and entries:
        entries[-1] += text[0][1:]
        text = text[1:]
        if entries[-1].count(r'%%%') > 0 and entries[-1].count(r'%%%') % 3 != 0:
            print(f"\nInvalid translation delimiter count for '{entries[-1][0]}': {entries[-1].count(r'%%%')} -- Fixing in manual editor")
            updated_text = create_manual_editor([entries[-1]], "Manual Text Editor")
            entries[-1] = updated_text.strip()

    entries.extend(text)


def parse_text_entries(entry_string):
    full_entry = entry_string.strip()
    key = ""
    pronunciation = ""
    value = ""
    locales = ""
    extracted_french_texts = []
    extracted_english_texts = []

    if '[' in full_entry or 'see' in full_entry:
        key, value = re.split(r'(?=\[)|(?=see)', full_entry, maxsplit=1)
        key = key[:-1].strip()

        if ']' in value:
            pronunciation, value = re.split(r'(?<=\])', value, maxsplit=1)
            pronunciation = pronunciation.strip()
            value = value.strip()
        
        if value.count('<Loc:') == 1:
            value, locales = re.split(r'(?=<Loc:)', value, maxsplit=1)
            value = value.strip()
            locales = locales.strip()
        elif value.count('<Loc:') > 1:
            print(f"\nMultilple locale arrays: {full_entry}")
        
        if value.count(r'%%%') > 0 and value.count(r'%%%') % 3 == 0:
            pattern = re.compile(r'%%%(.+?)%%%(.+?)%%%')
            matches = pattern.findall(value)
            for match in matches:
                extracted_french_texts.append(match[0].strip())
                extracted_english_texts.append(match[1].strip())
        elif value.count(r'%%%') > 0 and value.count(r'%%%') % 3 != 0:
            print(f"\nInvalid translation delimiter count for '{key}': {value.count(r'%%%')}")

    else:
        print(f"\nInvalid entry error - cannot parse: {full_entry}\n\n This entry will need to be added manually in the JSON file\n")

    entry_dict = {
            'Pronunciation': pronunciation,
            'Definitions': value,
            'Locales': locales,
            'Extracted French Texts': extracted_french_texts,
            'Extracted English Texts': extracted_english_texts,
            'Full Entry': full_entry
        }
        
    return key, entry_dict


def save_to_file(entry_array, file_path):
    # Read the existing JSON file
    with open(file_path, 'r', encoding='utf-8') as json_file:
        json_data = json.load(json_file)

    # Handle partial first entry
    if json_data['Data'] and entry_array[0][0] == '@':
        last_key = list(json_data['Data'].keys())[-1]
        full_entry = json_data['Data'][last_key]['Full Entry'] + " " + entry_array[0][1:].strip()
        
        _, entry_dict = parse_text_entries(full_entry)
        json_data['Data'][last_key] = entry_dict
        entry_array = entry_array[1:]
    
    def handle_duplicate_key(key):
        key_list = list(json_data['Data'].keys())
        matching_keys = [k for k in key_list if k.startswith(f"{key}^")]
        match_count = len(matching_keys)
        return f"{key}^{match_count + 1}"

    # Append full entries to the JSON data
    for entry in entry_array[:-1]:
        key, entry_dict = parse_text_entries(entry)
        key = key if key not in json_data['Data'] else handle_duplicate_key(key)
        json_data['Data'][key] = entry_dict

    # Handle partial last entry
    while entry_array[-1].count(r'<Loc:') > 1 and (entry_array[-1].count(r'[') != 0 or entry_array[-1].count(r'see') != 0):
        print(f"\nMultiple locale arrays in entry '{entry_array[-1][0]}' OR Invalid entry (No '[' or 'see') -- Fixing in manual editor")
        new_string = create_manual_editor([entry_array[-1]], "Manual Text Editor")
        entry_array[-1] = new_string

    if entry_array[-1].count(r'%%%') > 0 and entry_array[-1].count(r'%%%') % 3 != 0:
        key, value = re.split(r'(?=\[)|(?=see)', entry_array[-1], maxsplit=1)
        partial_entry_dict = {
            'Pronunciation': "",
            'Definitions': "",
            'Locales': "",
            'Extracted French Texts': [],
            'Extracted English Texts': [],
            'Full Entry': value
        }

        key = key if key not in json_data['Data'] else handle_duplicate_key(key)
        json_data['Data'][key] = partial_entry_dict
    else:
        key, entry_dict = parse_text_entries(entry_array[-1])
        key = key if key not in json_data['Data'] else handle_duplicate_key(key)
        json_data['Data'][key] = entry_dict

    # Write the updated JSON back to the file
    json_data['LastModified'] = datetime.datetime.now().strftime("%m-%d-%Y %H:%M:%S")
    with open(file_path, 'w', encoding='utf-8') as json_file:
        json.dump(json_data, json_file, ensure_ascii=False, indent=4)


def create_manual_editor(text, name="Manual Text Editor"):
    root = tk.Tk()
    root.title(name)
    
    # Position the window on the right half of the screen
    window_width = int(root.winfo_screenwidth() * 0.5)
    window_height = int(root.winfo_screenheight() * 0.925)
    root.geometry(f"{window_width}x{window_height}+{window_width}+0")

    # Define the text widget
    text_widget = tk.Text(root, wrap='word', font=('Bookman Old Style', 11), padx=10, pady=10, undo=True, autoseparators=True)
    text_widget.pack(expand=True, fill='both')
    text_widget.tag_configure("bold", font=('Bookman Old Style', 11, 'bold'))
    edited_text = tk.StringVar()

    # Insert the text and apply the bold tag to words preceded by two line breaks
    for entry in text:
        if entry.strip():
            words = entry.split()
            if words:
                text_widget.insert(tk.END, words[0], "bold")
                text_widget.insert(tk.END, ' ' + ' '.join(words[1:]) + '\n\n')
            else:
                text_widget.insert(tk.END, '\n\n')
        else:
            text_widget.insert(tk.END, '\n\n')

    # Remove the last two line breaks and add edit separators for undo/redo
    text_widget.edit_separator()
    text_widget.delete("end-3c", "end-1c")
    text_widget.edit_separator()

    def insert_translation_delimiter(event=None):
        text_widget.mark_set(tk.INSERT, f"@{event.x},{event.y}")
        text_widget.edit_separator()
        text_widget.insert(tk.INSERT, '%%%')
        text_widget.edit_separator()

    def close_editor(event=None):
        root.destroy()
        sys.exit(0)

    def save_and_close(event=None):
        widget_text = text_widget.get("1.0", tk.END)
        
        text_check_array = widget_text.strip().split('\n\n')
        for entry in text_check_array[1:]:
            entry_word = entry.split()[0]
            if entry.count(r'[') == 0 and entry.count(r'see') == 0 and entry.count(r'@') == 0:
                messagebox.showerror("Invalid Entry Error", f"Cannot save: {entry_word} -- cannot separate at '[' or 'see' -- Fix before saving")
                return
            if entry.count(r'<Loc:') > 1:
                messagebox.showerror("Multiple Locale Arrays Error", f"Multiple locale arrays in entry '{entry_word}' -- Fix before saving")
                return
            if entry.count(r'%%%') > 0 and entry.count(r'%%%') % 3 != 0:
                messagebox.showerror("Invalid Translation Delimiter Error", f"Invalid translation delimiter count in entry '{entry_word}': {entry.count(r'%%%')} -- Fix before saving")
                return
                
        edited_text.set(widget_text)
        root.destroy()
    
    text_widget.bind("<Control-y>", lambda event: text_widget.edit_redo())
    text_widget.bind("<Control-z>", lambda event: text_widget.edit_undo())
    text_widget.bind("<Control-Button-1>", insert_translation_delimiter)
    root.bind("<Escape>", close_editor)
    root.bind("<Control-s>", save_and_close)
    root.mainloop()

    return edited_text.get()


def page_segment(images):
    for image_path in images:
        # Load the image
        img = cv2.imread(image_path)
        if img is None:
            print(f"Error: Unable to load image {image_path}")
            continue
        else:
            print(f"Processing image: {image_path}")
        
        # Draw center segmentation line
        height, width = img.shape[:2]
        cv2.line(img, (width // 2, 0), (width // 2, height), (0, 0, 255), 2)

        # Draw outer segmentation lines
        header_line = int(height * 0.075)
        footer_line = int(height * 0.94)
        left_margin = int(width * 0.1)
        right_margin = int(width * 0.9)
        cv2.line(img, (0, header_line), (width, header_line), (0, 0, 255), 2)
        cv2.line(img, (0, footer_line), (width, footer_line), (0, 0, 255), 2)
        cv2.line(img, (left_margin, 0), (left_margin, height), (0, 0, 255), 2)
        cv2.line(img, (right_margin, 0), (right_margin, height), (0, 0, 255), 2)

        # Display the image
        window_name = 'Page Segment'
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, int(width * 0.49), int(height * 0.49))
        cv2.moveWindow(window_name, 70, 0)      
        cv2.imshow(window_name, img)

        # Handle key presses
        key = cv2.waitKey(0)
        if key == 27: # 'Esc' key to stop processing images completely
            break
        elif key == ord('t'): # 'T' key to terminate the process
            os.remove(image_path)
            cv2.destroyAllWindows()
            continue
        elif key == ord('s'): # 'S' key to skip the current image
            cv2.destroyAllWindows()
            continue

        # Remove margins
        img_cropped = img[header_line:footer_line, left_margin:right_margin]

        # Seperate columns
        mid_x = img_cropped.shape[1] // 2
        left_half = img_cropped[:, :mid_x]
        right_half = img_cropped[:, mid_x:]

        if left_half.shape[1] != right_half.shape[1]:
            if left_half.shape[1] < right_half.shape[1]:
                left_half = cv2.copyMakeBorder(left_half, 0, 0, 0, right_half.shape[1] - left_half.shape[1], cv2.BORDER_CONSTANT, value=[255, 255, 255])
            else:
                right_half = cv2.copyMakeBorder(right_half, 0, 0, 0, left_half.shape[1] - right_half.shape[1], cv2.BORDER_CONSTANT, value=[255, 255, 255])

        # Splice the two columns vertically
        img_spliced = cv2.vconcat([left_half, right_half])

        # OCR the spliced image
        text = pytesseract.image_to_string(img_spliced, lang='fra')
        text = re.sub(r'-\n', '', text)
        text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
        text = text.strip().split('\n\n')
        edited_text = create_manual_editor(text, image_path.split("\\")[-1])
        edited_text = edited_text.strip().split('\n\n')
        save_page(edited_text)

        os.remove(image_path)
        cv2.destroyAllWindows()


def create_json_file(file_path):
    file_name = file_path.split("\\")[-1]
    print(f"Please enter the metadata for this source below to create the JSON file: {file_name}\n")
    source = input("Source: ")
    segmentation_details = input("Segmentation Details: ")
    last_modified = datetime.datetime.now().strftime("%m-%d-%Y %H:%M:%S")

    # Create the initial JSON structure
    json_data = {
        "FileName": file_name,
        "Source": source,
        "SegmentationDetails": segmentation_details,
        "LastModified": last_modified,
        "Data": {}
    }

    # Write the JSON data to the file
    with open(file_path, 'w', encoding='utf-8') as file_path:
        json.dump(json_data, file_path, ensure_ascii=False, indent=4)
    
    print(f"JSON file created at {file_path}")


def handle_cleanup(output_path):
    if os.path.exists(output_path) and not os.listdir(output_path):
        os.rmdir(output_path)
    else:
        print(f"\nSaving the remaining {len(os.listdir(output_path))} images for processing later.\n")


def main():
    base_dir = os.environ.get("PROCESSING_DIR")
    if not base_dir:
        print("\nError: 'PROCESSING_DIR' environment variable not set.\nUse the 'set' command to set the variable. (i.e. set PROCESSING_DIR='" + r"C:\path\to\directory" + "')\n")
        exit(1)
    elif not os.path.exists(base_dir):
        print("\nError: Directory does not exist.\nPlease check the path and try again.\n Reset the 'PROCESSING_DIR' environment using the 'set' command. (i.e. set PROCESSING_DIR='" + r"C:\path\to\directory" + "')\n")
        exit(1)
    else:
        confirmation = input(f"Would you like to continue processing:\n'{base_dir}'\n([Y]/n)")
        if confirmation.lower() != 'y' and confirmation.lower() != 'yes' and confirmation != '':
            print("\nUse the 'set' command to change the 'PROCESSING_DIR' environment variable. (i.e. set PROCESSING_DIR='" + r"C:\path\to\directory" + "')\n")
            exit(1)

    output_path = os.path.join(base_dir, "Preprocessed_Images")
    potential_outputs = [output for output in os.listdir(base_dir) if output.endswith(".csv")]
    
    if len(potential_outputs) > 1:
        print("\nMultiple JSON files found in the selected directory. Please remove or consolidate all but one JSON file before running the script again.\n")
        exit(1)
    elif len(potential_outputs) == 1:
        json_file = os.path.join(base_dir, potential_outputs[0])
    else:
        json_file = os.path.join(base_dir, base_dir.split("\\")[-1] + ".json")
        create_json_file(json_file)

    if os.path.exists(output_path):
        images = os.listdir(output_path)
        images = [os.path.join(output_path, image) for image in images]
        
        if not images:
            print("\nImage folder is empty --> removing now, please run script again\n")
            os.rmdir(output_path)
            main()
    else:
        potential_inputs = [input for input in os.listdir(base_dir) if input.endswith(".pdf")]
        if not potential_inputs:
            print("\nNo PDF files found in the directory. Please add PDF files to the directory before running the script again.\n")
            exit(1)
        inputs_str = "\n".join([f"{i + 1}:  {file}" for i, file in enumerate(potential_inputs)])
        response = input("Please enter the number of the file you'd like to process next:\n" + inputs_str + "\n")
        
        if int(response) in range(1, len(potential_inputs) + 1):
            os.makedirs(output_path, exist_ok=True)
            selected_file = potential_inputs[int(response) - 1]
            input_pdf = os.path.join(base_dir, selected_file)          
            images = convert_from_path(input_pdf, output_folder=output_path, fmt='jpeg', paths_only=True)
        else:
            print("Invalid selection.")
            exit(1)
    
    page_segment(images)
    if entries:
        save_to_file(entries, json_file)
    handle_cleanup(output_path)

if __name__ == "__main__":
    main()