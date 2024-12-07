import re
import os
import sys
import pytesseract
from tqdm import tqdm
from PIL import Image, ImageFilter, ImageEnhance
from corpus_alignment_tool import create_editor

# Configure Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def ocr_image(image_path, language):
    try:
        image = Image.open(image_path)
        return "<><page-start><>" + pytesseract.image_to_string(image, lang=language, config='--psm 6') + "<><page-end><>"
    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return ""

def preprocess_images(input_folder):
    if not os.path.exists(os.path.join(input_folder, "preprocessed_images")):
        preprocessed_folder = os.path.join(input_folder, "preprocessed_images")
        os.makedirs(preprocessed_folder, exist_ok=True)
        
        files = sorted([f for f in os.listdir(input_folder) if f.lower().endswith('.jpg')])
        for image in tqdm(files, desc="Preprocessing images"):
            im = Image.open(os.path.join(input_folder, image))
            im = im.convert('L') # Convert to grayscale
            enhancer = ImageEnhance.Contrast(im)
            im = enhancer.enhance(2)
            im = im.filter(ImageFilter.MedianFilter(size=3)) # Denoise
            im = im.convert('1') # Convert to black and white
            im.save(os.path.join(preprocessed_folder, image))
    else:
        print("\nUsing existing preprocessed images")

def process_images(input_folder):
    english_text = []
    cajun_french_text = []
    files = sorted(os.listdir(input_folder))
    
    for i, image in enumerate(tqdm(files, desc="Processing images")):
        image_path = os.path.join(input_folder, image)
        if image.lower().endswith((".png", ".jpg", ".jpeg")):
            if i % 2 != 0:
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
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: python text_scraping.py <path_to_input_folder> [-P (Use preprocessed images - optional)]")
        sys.exit(1)
    elif not os.path.isdir(sys.argv[1]):
        print(f"Error: {sys.argv[1]} is not a valid directory")
        sys.exit(1)
    
    input_folder = sys.argv[1]
    use_preprocessed = len(sys.argv) == 3 and sys.argv[2] == '-P'
    
    if use_preprocessed:
        preprocess_images(input_folder)
        image_folder = os.path.join(input_folder, "preprocessed_images")
    else:
        image_folder = input_folder
    
    english_text, cajun_french_text = process_images(image_folder)

    english_text = [sentence_splitter(page) for page in english_text]
    cajun_french_text = [sentence_splitter(page) for page in cajun_french_text]

    print("\nCreating editor...")
    create_editor(english_text, cajun_french_text)