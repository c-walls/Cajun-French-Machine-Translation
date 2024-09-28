import re
import os
import sys
import pytesseract
from tqdm import tqdm
from PIL import Image
from corpus_alignment_tool import create_editor

# Configure Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def ocr_image(image_path, language):
    try:
        image = Image.open(image_path)
        return "<><page-start><>" + pytesseract.image_to_string(image, lang=language) + "<><page-end><>"
    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return ""

def process_images(input_folder):
    english_text = []
    cajun_french_text = []
    files = sorted(os.listdir(input_folder))
    for i, image in enumerate(tqdm(files, desc="Processing images")):
        image_path = os.path.join(input_folder, image)
        if image.lower().endswith((".png", ".jpg", ".jpeg")):
            if i % 2 == 0:
                english_text.append(ocr_image(image_path, "eng"))
            else:
                cajun_french_text.append(ocr_image(image_path, "fra"))
    
    return english_text, cajun_french_text

def sentence_splitter(text):
    text = re.sub(r"<><page-start><>\s*.*?\n+", "", text) # Remove page start markers and the first line of text (chapter title headers)
    text = re.sub(r"\n+\d{0,3}.{0,2}\s*<><page-end><>", "", text)  # Remove page end markers and page numbers + up to 2 stray characters
    text = re.sub(r'\n+.{0,2}\s*$', '', text)  # trailing whitespace + up to 2 stray characters
    text = text.strip().replace('\n', ' ')  # strip any remaining whitespace and replace newlines with spaces
    text = re.sub(r'\s+([».!?])', r'\1', text)  # Remove any spaces before punctuation marks or closing French quotes
    text = re.sub(r'«\s+', '«', text)  # Remove any spaces after opening French quotes
    text = re.sub(r"'", '’', text)  # Replace straight single quotes with curly single quotes (for better string processing)
    text = re.sub(r'(?<=\s)’', '‘', text)  # Replace closing apostrophes with opening ones if preceded by a space
    text = re.split(r"(?<=[»”.!?])\s*(?=[—«“A-ZÇÀÉ])", text)  # Split text into sentences based on punctuation and capitalized words or specific characters
    return text

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python text-scraping.py <path_to_input_folder>")
        sys.exit(1)
    elif not os.path.isdir(sys.argv[1]):
        print(f"Error: {sys.argv[1]} is not a valid directory")
        sys.exit(1)
    
    input_folder = sys.argv[1]
    english_text, cajun_french_text = process_images(input_folder)

    english_text = [sentence_splitter(page) for page in english_text]
    cajun_french_text = [sentence_splitter(page) for page in cajun_french_text]

    create_editor(english_text, cajun_french_text)