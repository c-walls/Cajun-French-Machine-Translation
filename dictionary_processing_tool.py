import os
import re
import cv2
import sys
import json
import datetime
import pytesseract
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
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
                elif len(word) > 1 and word[1].isupper() and word[0] in ('“', '‘', '"') and i >= segmentation_index:
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
        def_segments = [seg for seg in def_segments if not seg.endswith("*(XX)")]

        #Extract French and English texts
        for seg in def_segments:
            # Get the location code for this translation segment
            if seg.count('(') > 0:
                seg_location = seg[seg.rfind('('):].strip()
            else:
                seg_location = ""
                print(f"\nFIX MANUALLY: No segment location found in segment: {seg} for entry {key}\n")

            # Find the middle punctuation mark to split French and English texts
            punctuation_array = [m.start() for m in re.finditer(r'(?<!\bMr)(?<!\bMrs)[.!?;]', seg)]
            punctuation_count = len(punctuation_array)

            while punctuation_count % 2 != 0:
                seg = create_manual_editor(seg, f"Manual Text Editor - Fix Punctuation Count Error - {key}")
                punctuation_array = [m.start() for m in re.finditer(r'(?<!\bMr)(?<!\bMrs)[.!?;]', seg)]
                punctuation_count = len(punctuation_array)

            if punctuation_count > 0 and seg[punctuation_array[(punctuation_count // 2) - 1] + 1] in ['"', '”', '’']:
                french_seg = seg[:punctuation_array[(punctuation_count // 2) - 1] + 2].strip()
                english_seg = seg[punctuation_array[(punctuation_count // 2) - 1] + 2:punctuation_array[punctuation_count - 1] + 2].strip()
                
                translation_dict = {
                    "English": english_seg,
                    "Cajun French": french_seg,
                    "Location": seg_location
                }

                extracted_translations.append(translation_dict)
            
            elif punctuation_count > 0:
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
            'Full Entry': full_entry,
            'Pronunciation': pronunciation,
            'Locales': locales,
            'Entry Segments': def_segments,
            'Extracted Translations': extracted_translations
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

    # Print corpus metrics
    entry_count = len(json_data['Data'].keys())
    segment_count = 0
    translation_count = 0
    for key in json_data['Data'].keys():
        segment_count += len(json_data['Data'][key]['Entry Segments'])
        translation_count += len(json_data['Data'][key]['Extracted Translations'])
    
    print(f"\nEntries: {entry_count}\nTotal Segments: {segment_count}\nTotal Translation Count: {translation_count}\n")


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

    # Insert the text (Apply special 'corpus' formatting if receiving OCR data)
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

    elif type == "ocr_compare":
        text_data = text[0]
        img = text[1]
        images = []

        for i in range(len(text_data)):
            idx, word, _, bbox, is_fixed_error = text_data[i]

            cropped_img = img[bbox[1]:bbox[3], bbox[0]:bbox[2]]
            pil_img = Image.fromarray(cv2.cvtColor(cropped_img, cv2.COLOR_BGR2RGB))
            pil_img.resize((pil_img.width * 2, pil_img.height * 2))
            tk_img = ImageTk.PhotoImage(pil_img)

            if not i == 0 and idx < text_data[i - 1][0]:
                text_widget.insert(tk.END, '_' * 75 + '\n\n')

            text_widget.insert(tk.END, str(idx) + ':\t\t'  + word + '\t\t')
            text_widget.image_create(tk.END, image=tk_img)
            text_widget.insert(tk.END, '\t\t' + str(is_fixed_error) + '\n\n')
            images.append(tk_img)
                

    def close_editor(event=None):
        root.destroy()
        sys.exit(0)

    def save_and_close(event=None):
        widget_text = text_widget.get("1.0", tk.END)
        
        if type == "simple":
            edited_text.set(widget_text.strip())
        
        elif type == "corpus":
            text_check_array = widget_text.strip().split('\n\n')
            for i, entry in enumerate(text_check_array):
                entry_word = entry.split()[0]
                if entry.count(r'[') == 0 and entry.count(r'see ') == 0 and entry.count(r'@') == 0:
                    messagebox.showerror("Invalid Entry Error", f"Cannot save: {entry_word} -- cannot separate at '[' or 'see' or '@' -- Fix before saving")
                    return
                if entry.count(r'[') > 0 and entry.count(r']') == 0:
                    messagebox.showerror("Missing Closing Bracket Error", f"Missing closing bracket in pronunciation section of entry: '{entry_word}' -- Fix before saving")
                    return
                if entry.count(r'<Loc:') > 1:
                    messagebox.showerror("Multiple Locale Arrays Error", f"Multiple locale arrays in entry '{entry_word}' -- Fix before saving")
                    return
                if entry.count(r'see ') > 0 and entry.count(r'<Loc:') > 0:
                    if (entry.count(r'[') == 0 and entry.count(r'@') == 0) or (entry.count(r'[') > 0 and entry.index(r'see ') < entry.index(r'[')):
                        messagebox.showerror("Invalid Entry Split Error", f"Cannot save: {entry_word} -- splits at 'see' but contains <Loc:> tag -- Fix before saving")
                        return
                if entry.count(r'@') > 0 and i == 0:
                    if entry[entry.index(r'@') + 1] != ' ':
                        messagebox.showerror("Invalid first entry", f"Cannot save: {entry_word}. Make sure to include a space after '@' character for proper concatenation")
                        return 
            edited_text.set(widget_text)
        
        elif type == "ocr_compare":
            error_text = widget_text.strip()

            if error_text.count('||||') > 0 and error_text.count('~~~~') == 0:
                messagebox.showerror("Invalid Entry Error", "Remove excess '|' or '~' characters before saving")
                return

            error_array = error_text.split('\n\n')
            error_array = [re.sub(r'\t{3,}', '\t\t', line) for line in error_array if not line.startswith('___')]
            error_array = [line.split('\t\t') for line in error_array]

            filtered_errors = []
            for i in range(len(error_array)):
                idx = error_array[i][0].strip()
                word = error_array[i][1].strip()
                is_fixed_error = error_array[i][2].strip() if len(error_array[i]) > 2 else None
                
                if is_fixed_error in ['True', 'False']:
                    filtered_errors.append(idx[:-1] + "||||" + word)
                
            edited_text.set("~~~~".join(filtered_errors))
                    
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
        header_line = int(height * 0.07)
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
        elif key == ord('t'): # 'T' key to trash the current image
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
        text_data = []
        for i in range(len(ocr_data['text'])):
            left = ocr_data['left'][i]
            top = ocr_data['top'][i]
            right = left + ocr_data['width'][i]
            bottom = top + ocr_data['height'][i]

            word = ocr_data['text'][i]
            confidence = ocr_data['conf'][i]
            bbox = [left, top, right, bottom]

            text_data.append([word, confidence, bbox])

        # Frequent OCR errors
        frequent_errors = {
            'I': ['X', 'T', '1', 'x'],
            "I’m": ["Y’m", "1’m", "T’m", "l’m", "lm", "1m", "V’m"],
            "I’d": ["l’d", "1’d"],
            "I’ve": ["l’ve", "Y’ve", "1’ve", "T’ve"],
            'Il': ['//', '}}', '{{', '17', '/!', 'I!', '/{', '11', '{1', '1]', '1l', '1!', '/]', 'I7', 'Z/', 'Z!', 'Zl', '7!', 'J!', 'J1', '/1', 'IT', '/l', 'Jl', '/7', '{!'],
            'Ils': ['{1s', '//s', 'J{s', '{{s', '/{s', '/!s', '11s', '/}s', 'Jls', 'J!s', 'J1s', '{ls', '/ls', '/1s'],
            'v.tr.': ['v.fr', 'v.tr', 'v.fr.', 'v.tr:', 'v1r', 'v.1r', 'v.1r:', 'v.#r:.', 'v.fr:', 'v#:', 'w#r', 'w#:', 'vtr', 'v.#r', 'v.sr:', 'v./r:', 'vs:', 'v.#r:', 'v.#r.', 'v.#7', 'v.#:'],
            'n.m.': ['n.m', '7.m.'],
            'it’s': ['its'],
            'It’s': ['Its', 'Ws'],
            'LF,': ['LE,', 'LE', 'LF'],
            '(LF)': ['(LE)'],
            'LF>': ['LE>'],
            "He’ll": ['He’II', 'He’Il', 'He’lI'],
            "he’ll": ['he’II', 'he’Il', 'he’lI'],
            "You’ll": ['You’II', 'You’Il', 'You’lI'],
            "you’ll": ['you’II', 'you’Il', 'you’lI'],
            "We’ll": ['We’II', 'We’Il', 'We’lI'],
            "we’ll": ['we’II', 'we’Il', 'we’lI'],
            "She’ll": ['She’II', 'She’Il', 'She’lI'],
            "she’ll": ['she’II', 'she’Il', 'she’lI'],
            "They’ll": ['They’II', 'They’Il', 'They’lI'],
            "they’ll": ['they’II', 'they’Il', 'they’lI'],
            "I’ll": ['I’II', 'I’Il', 'I’lI', 'l’ll', 'l’Il', 'l’lI']
        }
        word_errors = []

        for i in range(len(text_data)):
            word, conf, bbox = text_data[i]

            # Check for common issues
            is_frequent_error = any(word in errors for errors in frequent_errors.values())
            has_eos_punc_error = re.search(r'[.!?](?=["”\'’])', word)
            has_prepended_symbol = re.search(r'^(?!["\'(\[{<‘“])\W+[a-zA-Z]', word)
            contains_straight_quotes = re.search(r'["\']', word)
            contains_double_dot_i = re.search(r'ï', word)
            contains_dash_z = re.search(r'-z|z-', word)
            
            if conf >= 75 and (any([is_frequent_error, has_eos_punc_error, has_prepended_symbol, contains_straight_quotes, contains_double_dot_i, contains_dash_z])):
                conf = 74

            if conf < 75 and conf != -1:

                word = re.sub(r"(?<=[A-Za-z])'", "’", word)
                
                if re.match(r'^([*+«])', word):
                    if word in frequent_errors.keys() or any(word[1:] in errors for errors in frequent_errors.values()):
                        word = word[1:]
                    else:
                        word = word[0] + "(XX) " + word[1:]
                    text_data[i] = [word, conf, bbox]

                for key in frequent_errors.keys():
                    if word in frequent_errors[key]:
                        word = key
                        text_data[i] = [word, conf, bbox]
                        
                is_fixed_error = True if word in frequent_errors.keys() else False
                word_errors.append([i, word, conf, bbox, is_fixed_error])

        # Manually check low confidence words
        word_errors = sorted(word_errors, key=lambda x: x[4], reverse=True)
        filtered_errors = create_manual_editor([word_errors, img_spliced], name="Manual Text Editor - Low Confidence Words", type="ocr_compare")
        filtered_errors = [error.split("||||") for error in filtered_errors.split("~~~~")]
        
        # Print check
        for error in filtered_errors:
            idx, word = error
            if text_data[int(idx)][0] != word:
                text_data[int(idx)] = ([word, 75, None])
            else:
                text_data[int(idx)][1] = 75

        for data in text_data:
            if data[1] < 75 and data[1] != -1:
                data[0] = '%<>%' + data[0]

        text_concat = ' '.join([data[0] for data in text_data]).strip()
        text = re.sub('   ', '\n\n', text_concat)
        text = re.sub('  ', '\n', text)
        text = re.sub(r'\n{4,}', '', text)
        text = re.sub(r'-\n+', '', text) # fix hyphenated words
        text = re.sub(r'(?<!\s)%<>%', '', text) # remove extra confidence markers
        text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text) # replace single line breaks with spaces
        text = re.sub(r'(<Loc:[^<>]*>) +(?!\n)', r'\1\n\n', text) # add line breaks after locale arrays as needed
        text = text.strip().split('\n\n')

        # Add '@' symbol to any incomplete first entries at the top of the page
        if text[0] and (text[0].count('<Loc:') > 0 and text[0].count('[') == 0):
            text[0] = '@ ' + text[0]

        # remove mis-OCR'd characters from subscripts on some entry terms
        for i, entry in enumerate(text):
            words = entry.split()
            if words[0].endswith(',') or words[0].endswith('-') or words[0].endswith(';'):
                if len(words[0]) > 2 and not words[0][-2].isalpha():
                    words[0] = words[0][:-2] + words[0][-1]
                    text[i] = ' '.join(words)
            elif not words[0][-1].isalpha() and len(words[0]) > 1:
                words[0] = words[0][:-1]
                text[i] = ' '.join(words)

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
    corpus_dict = {
        "metadata": {
            "file_name": "DLF2010_extracts",
            "source": "Dictionary of Louisiana French: As Spoken in Cajun, Creole, and American Indian Communities (Valdman 2010)",
            "last_modified": "",
            "total_lines": 0,
            "segmentation_details": "Dictionary Terms",
            "segmentation_index": {}
        },
        "data": []
    }
    
    with open(json_file, 'r', encoding='utf-8') as file:
        json_data = json.load(file)

    data = json_data['Data']
    missing_translations = 0
    corpus_dict['metadata']['last_modified'] = datetime.datetime.now().strftime("%m-%d-%Y %H:%M:%S")

    for key, value in data.items():
        parallel_translations = value['Extracted Translations']
        if parallel_translations:
            corpus_dict['metadata']['total_lines'] += len(parallel_translations)
            corpus_dict['metadata']['segmentation_index'][key] = len(corpus_dict['data'])
        for translation in parallel_translations:
            eng = translation.get('English', '')
            caj = translation.get('Cajun French', '')
            if eng == '' or caj == '':
                missing_translations += 1
            else:
                translation_dict = {
                    "English": eng,
                    "Cajun French": caj
                }
                corpus_dict['data'].append(translation_dict)
        
    if missing_translations > 0:
        print(f"\n{missing_translations} translations were missing and not added to the parallel corpus.")
    print(f"\nCorpus successfully processed -- It contains {corpus_dict['metadata']['total_lines']} total parallel tranlation pairs\n")

    output_file = "Data\\DLF2010_extracts.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as file:
        json.dump(corpus_dict, file, ensure_ascii=False, indent=4)

def clean_json_file(json_file):
    with open(json_file, 'r', encoding='utf-8') as file:
        json_data = json.load(file)

    count = 0
    for key, value in json_data['Data'].items():
        for translation in value['Extracted Translations']:
            english_text = translation['English']
            french_text = translation['Cajun French']
            if re.search(r'\b\w*[A-Z]+\w*[a-z]+\w*\b', english_text) or re.search(r'\b\w*[A-Z]+\w*[a-z]+\w*\b', french_text):
                print(f"\n{key}:\n{english_text}\n{french_text}\n")
                count += 1
    
    print(f"\n{count} entries contain words with capitalization errors\n")

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
    elif len(sys.argv) > 1 and sys.argv[1] == "clean":
        clean_json_file(json_file)
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

