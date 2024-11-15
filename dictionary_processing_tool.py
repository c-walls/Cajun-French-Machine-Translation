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

# Global text array to store the dictionary entries
entries = []

def save_page(text):
    if text[0][0] == '@' and entries:
        entries[-1] += text[0][1:]
        text = text[1:]

    entries.extend(text)


def parse_text_entries(entry_string):
    full_entry = entry_string.strip()
    key = ""
    pronunciation = ""
    value = ""
    locales = ""
    def_segments = []
    extracted_translations = []

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
            print(f"\nMultilple locale arrays in:\n{full_entry}\n\nThis entry will need to be fixed manually.\n")
        
        def remove_irrelevant_info(seg):
            words = seg.split()
            segmentation_index = 0
            for i, word in enumerate(words):
                if word[-1] == ">":
                    segmentation_index = i + 1
                if word.count('.') > 1:
                    segmentation_index = i + 1

            for i, word in enumerate(words):
                if word[0].isupper() and i >= segmentation_index and word not in ['I', "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]:
                    segmentation_index = i
                    break
                elif len(word) > 1 and not word[0].isalpha() and word[1].isupper() and i >= segmentation_index:
                    words[i] = word[1:]
                    segmentation_index = i
                    break
            return ' '.join(words[segmentation_index:])
        
        def_segments = re.split(r'(?<=\))\s', value)
        def_segments = [seg.strip() for seg in def_segments if re.search(r'\((?=.*[A-Z]).*?\)', seg)]
        def_segments = [remove_irrelevant_info(seg) for seg in def_segments]

        #Extract French and English texts
        for seg in def_segments:
            # Get the location code for this translation segment
            if seg.count('(') > 0:
                seg_location = seg[seg.rfind('('):].strip()
            else:
                seg_location = ""
                print(f"\nFIX MANUALLY: No segment location found in segment: {seg} for entry {key}\n")

            # Find the middle punctuation mark to split French and English texts
            punctuation_array = [m.start() for m in re.finditer(r'[.!?;]', seg)]
            punctuation_count = len(punctuation_array)

            while punctuation_count % 2 != 0:
                new_string = create_manual_editor(seg, "Manual Text Editor - Fix Punctuation Count Error")
                punctuation_array = [m.start() for m in re.finditer(r'[.!?;]', new_string)]
                punctuation_count = len(punctuation_array)

            if punctuation_count > 0:
                french_seg = seg[:punctuation_array[(punctuation_count // 2) - 1] + 1].strip()
                english_seg = seg[punctuation_array[(punctuation_count // 2) - 1] + 1:punctuation_array[punctuation_count - 1] + 1].strip()

                translation_dict = {
                    "English": english_seg,
                    "Cajun French": french_seg,
                    "Location": seg_location
                }

                extracted_translations.append(translation_dict)
            else:
                print(f"\nNo segmentable punctuation in segment: {seg}")
    else:
        print(f"\nInvalid entry error - cannot parse: {full_entry}\n\n This entry will need to be added manually in the JSON file\n")

    entry_dict = {
            'Pronunciation': pronunciation,
            'Entry Segments': def_segments,
            'Locales': locales,
            'Extracted Translations': extracted_translations,
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
    for entry in entry_array:
        key, entry_dict = parse_text_entries(entry)
        key = key if key not in json_data['Data'] else handle_duplicate_key(key)
        json_data['Data'][key] = entry_dict

    # Write the updated JSON back to the file
    json_data['LastModified'] = datetime.datetime.now().strftime("%m-%d-%Y %H:%M:%S")
    with open(file_path, 'w', encoding='utf-8') as json_file:
        json.dump(json_data, json_file, ensure_ascii=False, indent=4)


def create_manual_editor(text, name="Manual Text Editor", type="simple"):
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
    text_widget.tag_configure("low-conf", foreground="red")
    edited_text = tk.StringVar()

    # Insert the text (For OCR Array: apply special formatting)
    if type == "simple":
        text_widget.insert(tk.END, text)

    elif type == "corpus":
        for entry in text:
            if entry.strip():
                words = entry.split()
                
                if words:
                    if words[0].startswith('%<>%'):
                        word = words[0].replace('%<>%', '')
                        text_widget.insert(tk.END, word, ("low-conf", "bold"))
                    else:
                        text_widget.insert(tk.END, words[0], "bold")
                    for word in words[1:]:
                        if word.startswith('%<>%'):
                            word = word.replace('%<>%', '')
                            text_widget.insert(tk.END, ' ' + word, "low-conf")
                        else:
                            text_widget.insert(tk.END, ' ' + word)
                    text_widget.insert(tk.END, '\n\n')
                else:
                    text_widget.insert(tk.END, '\n\n')
            else:
                text_widget.insert(tk.END, '\n\n')

        # Remove the last two line breaks and add edit separators for undo/redo
        text_widget.edit_separator()
        text_widget.delete("end-3c", "end-1c")
        text_widget.edit_separator()

    def close_editor(event=None):
        root.destroy()
        sys.exit(0)

    def save_and_close(event=None):
        widget_text = text_widget.get("1.0", tk.END)
        
        if type == "simple":
            edited_text.set(widget_text.strip())
        
        elif type == "corpus":
            text_check_array = widget_text.strip().split('\n\n')
            for entry in text_check_array:
                entry_word = entry.split()[0]
                if entry.count(r'[') == 0 and entry.count(r'see') == 0 and entry.count(r'@') == 0:
                    messagebox.showerror("Invalid Entry Error", f"Cannot save: {entry_word} -- cannot separate at '[' or 'see' or '@' -- Fix before saving")
                    return
                if entry.count(r'[') > 0 and entry.count(r']') == 0:
                    messagebox.showerror("Missing Closing Bracket Error", f"Missing closing bracket in pronunciation section of entry: '{entry_word}' -- Fix before saving")
                    return
                if entry.count(r'<Loc:') > 1:
                    messagebox.showerror("Multiple Locale Arrays Error", f"Multiple locale arrays in entry '{entry_word}' -- Fix before saving")
                    return
                if entry.count(r'see') > 0 and entry.count(r'<Loc:') > 0:
                    if entry.count(r'[') == 0 or (entry.index(r'see') < entry.index(r'[')):
                        messagebox.showerror("Invalid Entry Split Error", f"Cannot save: {entry_word} -- splits at 'see' but contains <Loc:> tag -- Fix before saving")
                        return
                    
            edited_text.set(widget_text)

        root.destroy()
    
    text_widget.bind("<Control-y>", lambda event: text_widget.edit_redo())
    text_widget.bind("<Control-z>", lambda event: text_widget.edit_undo())
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
        ocr_data = pytesseract.image_to_data(img_spliced, lang='fra', output_type=pytesseract.Output.DICT)
        
        # Extract text and confidence levels
        text_with_confidence = []
        for i in range(len(ocr_data['text'])):
            word = ocr_data['text'][i]
            confidence = ocr_data['conf'][i]
            text_with_confidence.append((word, confidence))

        # Frequent OCR errors
        frequent_errors = ['X', 'T', '1', "Y'm", "1'm", "Y’m", "1’m", "T’m", "l’m", "T'm", "l'm", "lm", "1m", '//', '}}', '/!', '11', '{1', '1]', '1l', '1!', '/]', 'I7', 'Z/', 'Z!', '7!', 'J!', 'J1', '/1', 'Jl', 'IT', '/l', '{1s', '//s', 'J{s', '{{s', '/{s', 'Jls']

        for i in range(len(text_with_confidence)):
            word, conf = text_with_confidence[i]
            conf = 74 if conf >= 75 and word in frequent_errors else conf
            if conf < 75 and conf != -1:
                word = word if not word.startswith("*") else word.replace("*", "")
                if word in ['X', 'T', '1']:
                    text_with_confidence[i] = ('%<>%' + 'I', conf)
                elif word in ["Y'm", "1'm", "Y’m", "1’m", "T’m", "l’m", "T'm", "l'm", "lm", "1m"]:
                    text_with_confidence[i] = ('%<>%' + "I'm", conf)
                elif word in ['//', '}}', '/!', '11', '{1', '1]', '1l', '1!', '/]', 'I7', 'Z/', 'Z!', '7!', 'J!', 'J1', '/1', 'IT', '/l', 'Jl']:
                    text_with_confidence[i] = ('%<>%' + 'Il', conf)
                elif word in ['{1s', '//s', 'J{s', '{{s', '/{s', 'Jls']:
                    text_with_confidence[i] = ('%<>%' + 'Ils', conf)
                else:
                    text_with_confidence[i] = ('%<>%' + word, conf)

        text_concat = ' '.join([data[0] for data in text_with_confidence]).strip()
        text = re.sub('   ', '\n\n', text_concat)
        text = re.sub('  ', '\n', text)
        text = re.sub(r'\n{4,}', '', text)
        text = re.sub(r'-\n', '', text) # fix hyphenated words
        text = re.sub(r'(?<!\s)%<>%', '', text) # remove extra confidence markers
        text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text) # replace single line breaks with spaces
        text = re.sub(r'(<Loc:[^>]*>) +(?!\n)', r'\1\n\n', text) # add line breaks after locale arrays as needed
        text = text.strip().split('\n\n')

        if text[0] and text[0].count('see') == 0 and text[0].count('[') == 0:
            text[0] = '@' + text[0]

        edited_text = create_manual_editor(text, image_path.split("\\")[-1], type="corpus")
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

def convert_to_parallel_corpus(json_file):
    french_texts = []
    english_texts = []
    
    with open(json_file, 'r', encoding='utf-8') as file:
        json_data = json.load(file)

    file_name = json_data['FileName']
    source = json_data['Source']
    Seg_details = json_data['SegmentationDetails']
    data = json_data['Data']

    for key in data.keys():
        french_texts.extend(data[key]['Extracted French Texts'])
        english_texts.extend(data[key]['Extracted English Texts'])

    print(f"\nLength of French Texts: {len(french_texts)}\nLength of English Texts: {len(english_texts)}\n")


def main():
    base_dir = os.environ.get("PROCESSING_DIR")
    if not base_dir:
        print("\nError: 'PROCESSING_DIR' environment variable not set.\nSet the variable from the terminal first. (Temp variable assignment in powershell -> $env:PROCESSING_DIR='" + r"C:\path\to\directory" + "')\n")
        exit(1)
    elif not os.path.exists(base_dir):
        print("\nError: Directory does not exist.\nPlease check the path and try again.\n Reset the variable from the terminal first. (Temp variable assignment in powershell -> $env:PROCESSING_DIR='" + r"C:\path\to\directory" + "')\n")
        exit(1)
    else:
        confirmation = input(f"Would you like to continue processing:\n'{base_dir}'\n([Y]/n)")
        if confirmation.lower() != 'y' and confirmation.lower() != 'yes' and confirmation != '':
            print("\nChange the variable from the terminal before running. (Temp variable assignment in powershell -> $env:PROCESSING_DIR='" + r"C:\path\to\directory" + "')\n")
            exit(1)

    output_path = os.path.join(base_dir, "Preprocessed_Images")
    potential_outputs = [output for output in os.listdir(base_dir) if output.endswith(".json")]
    
    if len(potential_outputs) > 1:
        print("\nMultiple JSON files found in the selected directory. Please remove or consolidate all but one JSON file before running the script again.\n")
        exit(1)
    elif len(potential_outputs) == 1:
        json_file = os.path.join(base_dir, potential_outputs[0])
    else:
        json_file = os.path.join(base_dir, base_dir.split("\\")[-1] + ".json")
        create_json_file(json_file)

    #Helper function to convert the JSON file to a parallel corpus
    if len(sys.argv) > 1 and sys.argv[1] == "convert":
        convert_to_parallel_corpus(json_file)
        exit(0)

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

