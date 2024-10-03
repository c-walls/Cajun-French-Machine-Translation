import os
import re
import json
import datetime
import translators as ts
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import sys

json_file = None

## TODO: add page length errors to array and display all together
## TODO: add the option to append to an existing JSON file


def load_text(text_widget, text):
    text_widget.delete("1.0", tk.END)
    for i, page in enumerate(text):
        text_widget.insert(tk.END, "\n________________________________ page " + str(i+1) + " ____________________________________\n\n\n")
        for line in page:
            text_widget.insert(tk.END, line + "\n\n")


def extract_text(text_widget):
    text = text_widget.get("1.0", tk.END)
    text = re.sub(r'\n_{2,}.*_{2,}\n\n\n', '', text, count=1)
    pages = re.split(r'\n_{2,}.*_{2,}\n\n\n', text)
    pages = [re.split(r'\n+', page.strip()) for page in pages]
    pages = [[line.strip() for line in page] for page in pages]
    
    return pages


def collect_metadata(total_lines, segmentation_index):
    global json_file
    
    # Create popup window for user input
    metadata_window = tk.Toplevel()
    metadata_window.title("Enter Metadata")
    metadata_window.geometry("+550+400")
    metadata_window.columnconfigure(0, weight=1)
    metadata_window.columnconfigure(1, weight=1)

    # Create label and entry for each field
    tk.Label(metadata_window, text="File Name:").grid(row=0, column=0, padx=(20, 5), pady=5, sticky=tk.E)
    tk.Label(metadata_window, text="Source:").grid(row=1, column=0, padx=(20, 5), pady=5, sticky=tk.E)
    tk.Label(metadata_window, text="Segmentation Details:").grid(row=2, column=0, padx=(20, 5), pady=5, sticky=(tk.N, tk.E))
    file_name_entry = tk.Entry(metadata_window, width=50)
    source_entry = tk.Entry(metadata_window, width=50)
    segmentation_entry = tk.Text(metadata_window, width=50, height=4)

    # Place each entry in the grid
    file_name_entry.grid(row=0, column=1, padx=(0, 20), sticky="ew")
    source_entry.grid(row=1, column=1, padx=(0, 20), sticky="ew")
    segmentation_entry.grid(row=2, column=1, padx=(0, 20), pady=5, sticky="ew")

    # Load metadata from JSON file if json_file is defined
    if json_file:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        metadata = data.get('metadata', {})
        file_name_entry.insert(0, metadata.get("file_name", ""))
        source_entry.insert(0, metadata.get("source", ""))
        segmentation_entry.insert(tk.END, metadata.get("segmentation_details", ""))

    metadata = {}
    def on_submit():
        metadata["file_name"] = file_name_entry.get()
        metadata["source"] = source_entry.get()
        metadata["last_modified"] = datetime.datetime.now().strftime("%m-%d-%Y %H:%M:%S")
        metadata["total_lines"] = total_lines
        metadata["segmentation_details"] = segmentation_entry.get("1.0", tk.END).strip()
        metadata["segmentation_index"] = segmentation_index

        metadata_window.destroy()
    
    # Create submit button
    submit_button = tk.Button(metadata_window, text="Submit", command=on_submit)
    submit_button.grid(row=3, column=1, pady=10)

    metadata_window.grab_set()
    metadata_window.wait_window()

    return metadata


def save_to_json(english_widget, cajun_french_widget):
    english_text = extract_text(english_widget)
    cajun_french_text = extract_text(cajun_french_widget)

    for i, (eng_page, cajun_page) in enumerate(zip(english_text, cajun_french_text)):
        if len(eng_page) != len(cajun_page):
            messagebox.showerror("Error", f"Page {i+1} has different number of lines in English and Cajun French text\n\nEnglish: {len(eng_page)} lines\nCajun French: {len(cajun_page)} lines")
            return

    total_lines = sum(len(page) for page in english_text)
    flattened_data = []
    segmentation_index = {}

    for i, (eng_page, cajun_page) in enumerate(zip(english_text, cajun_french_text)):
        segmentation_index[f'Page {str(i+1)}'] = len(eng_page)

        for eng_line, cajun_line in zip(eng_page, cajun_page):
            flattened_data.append({
                "English": eng_line,
                "Cajun French": cajun_line
            })

    metadata = collect_metadata(total_lines, segmentation_index)

    data = {
        "metadata": metadata,
        "data": flattened_data
    }

    # Create output directory and file path
    output_dir = r'Data'
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, metadata['file_name'] + '.json')

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    messagebox.showinfo("Success", f"Data saved to {output_file}")

    return True

class TranslationManager:
    def __init__(self, root):
        self.root = root
        self.translations = {}

    def translate_selection(self):
        widget = self.root.focus_get()
        widget_name = widget.winfo_name()
        selection = widget.tag_ranges(tk.SEL)
        if not selection:
            for label in self.translations.values():
                label.destroy()
            self.translations.clear()
            return
        elif widget_name in self.translations.keys():
            self.translations[widget_name].destroy()

        start, end = selection
        text = widget.get(start, end)
        translation = ""
        bounding_box = widget.bbox(end)

        if widget_name == 'english_widget':
            translation = ts.translate_text(text, translator='google', to_language='fr', from_language='en')
        elif widget_name == 'cajun_widget':
            translation = ts.translate_text(text, translator='google', to_language='en', from_language='fr')

        label = tk.Label(self.root, text=translation, bg="#ffffe0", relief="solid", borderwidth=0.5, padx=5, pady=5, font=("Helvetica", 12, "bold"), wraplength=(widget.winfo_width() - 85))
        label.place(x=widget.winfo_rootx() + 75, y=bounding_box[1] + 10)
        self.translations[widget_name] = label

def create_editor(english_text, cajun_french_text):
    root = tk.Tk()
    root.title("Corpus Alignment Tool")
    root.geometry("1400x800")
    root.state("zoomed")

    # Create outer frame that dynamically resizes
    frame = ttk.Frame(root)
    frame.pack(fill=tk.BOTH, expand=True)
    frame.columnconfigure(0, weight=1)
    frame.columnconfigure(1, weight=1)
    frame.rowconfigure(0, weight=1)
    frame.rowconfigure(1, weight=0)

    # Create side-by-side text widgets
    english_widget = tk.Text(frame, wrap="word", name="english_widget", font=("Verdana", 11), padx=10, bg="#f6f5f6")
    english_widget.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S), padx=(0, 10))
    cajun_widget = tk.Text(frame, wrap="word", name="cajun_widget", font=("Verdana", 11), padx=10, bg="#f6f5f6")
    cajun_widget.grid(column=1, row=0, sticky=(tk.N, tk.W, tk.E, tk.S), padx=(0, 10))

    # Load text into text widgets
    load_text(english_widget, english_text)
    load_text(cajun_widget, cajun_french_text)

    # Create scrollbars
    scrollbar1 = ttk.Scrollbar(frame, orient="vertical", command=english_widget.yview)
    scrollbar1.grid(column=0, row=0, sticky=(tk.N, tk.S, tk.E))
    english_widget["yscrollcommand"] = scrollbar1.set
    scrollbar2 = ttk.Scrollbar(frame, orient="vertical", command=cajun_widget.yview)
    scrollbar2.grid(column=1, row=0, sticky=(tk.N, tk.S, tk.E))
    cajun_widget["yscrollcommand"] = scrollbar2.set

    # Create save button
    button_frame = ttk.Frame(frame)
    button_frame.grid(column=0, row=1, columnspan=2, pady=(8, 8))
    save_button = tk.Button(button_frame, text="Save", font=("Verdana", 11, "bold"), bg="#e3e3e3", relief="ridge", padx=30, pady=5, command=lambda: (save_to_json(english_widget, cajun_widget) and root.destroy()))
    save_button.pack()

    translation_manager = TranslationManager(root)
    root.bind("<Control-Shift-Z>", lambda event: translation_manager.translate_selection())
    root.mainloop()


def load_from_json(json_file):
    with open(json_file, 'r', encoding='utf-8') as f:
        file = json.load(f)
    data = file.get('data', [])

    english_text = [item['English'] for item in data]
    cajun_french_text = [item['Cajun French'] for item in data]
    segmentation_index = file.get('metadata', {}).get('segmentation_index', {})

    english_text = reconstruct_pages(english_text, segmentation_index)
    cajun_french_text = reconstruct_pages(cajun_french_text, segmentation_index)

    return english_text, cajun_french_text


def reconstruct_pages(data, segmentation_index):
    pages = []
    start = 0
    for length in segmentation_index.values():
        pages.append(data[start:start+length])
        start += length
    return pages


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1].endswith('.json'):
        json_file = sys.argv[1]
        
        if not os.path.exists(json_file):
            print(f"Error: The file {json_file} does not exist.")
        else:
            print(f"Loading data from {json_file}")

        english_text, cajun_french_text = load_from_json(json_file)
        create_editor(english_text, cajun_french_text)
    else:
        print("\nCLI Usage: python corpus_alignment_tool.py <path_to_json_file>\nOtherwise import and call create_editor(english_text, cajun_french_text) in python\n")