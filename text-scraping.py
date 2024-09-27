import re
import os
import sys
import pytesseract
from tqdm import tqdm
from PIL import Image

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
    text = re.sub(r"<><page-start><>.*?\n", "", text)
    text = re.sub(r"\d{0,3}\s*<><page-end><>", "", text)
    text = text.replace('\n\n', '||')
    text = re.sub(r'\|\|.{0,2}$', '', text)
    text = text.lstrip('\n')
    text = text.replace('\n', ' ')
    text = re.sub(r'\s+([».!?])', r'\1', text)
    text = re.sub(r'«\s+', '«', text)
    text = re.split(r"(?<=[».!?])\s*(?=[—«A-ZÇÀÉ])|(?<=[».!?])\|\|(?=[—«A-ZÇÀÉ])", text)
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

    english_text = [sentence_splitter(text) for text in english_text]
    cajun_french_text = [sentence_splitter(text) for text in cajun_french_text]

    for page in english_text:
        print("{")
        for sentence in page:
            print(f"    [{sentence}]")
        print("}")