import os
import logging
import fitz

from backend.config import UPLOADS_DIR

class FilePreprocessor:
    def __init__(self, base_dir=UPLOADS_DIR):
        self.raw_dir = os.path.join(base_dir, 'raw')
        self.applicant_subdir = 'applicants'
        self.job_posting_subdir = 'jobPostings'
        os.makedirs(self.raw_dir, exist_ok=True)

    def clean_text(self, text):
        lines = text.split('\n')
        cleaned_lines = []
        blank_count = 0
        for line in lines:
            if line.strip() == "":
                blank_count += 1
            else:
                blank_count = 0
            if blank_count < 2:
                cleaned_lines.append(line)
        return '\n'.join(cleaned_lines)

    def extract_text_from_pdf(self, pdf_path):
        try:
            doc = fitz.open(pdf_path)
            text = "\n".join(page.get_text() for page in doc)
            return self.clean_text(text.strip())
        except Exception as e:
            logging.error(f"Error extracting PDF content from {pdf_path}: {e}")
            return None

    def process_folder(self, subfolder_name):
        input_dir = os.path.join(self.raw_dir, subfolder_name)
        if not os.path.exists(input_dir):
            logging.warning(f"No such directory to process: {input_dir}")
            return {}

        processed_texts = {}
        for filename in os.listdir(input_dir):
            file_path = os.path.join(input_dir, filename)
            if not os.path.isfile(file_path):
                continue

            try:
                if filename.endswith('.pdf'):
                    text = self.extract_text_from_pdf(file_path)
                elif filename.endswith('.docx'):
                    logging.warning(f"DOCX handling not implemented: {filename}")
                    continue
                else:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        text = f.read()

                if text:
                    cleaned_text = self.clean_text(text)
                    processed_texts[filename] = cleaned_text

            except Exception as e:
                logging.error(f"Failed to process {file_path}: {str(e)}")

        return processed_texts

    def process_all(self):
        results = []
        for subfolder in [self.applicant_subdir, self.job_posting_subdir]:
            input_dir = os.path.join(self.raw_dir, subfolder)
            if not os.path.exists(input_dir):
                continue

            for filename in os.listdir(input_dir):
                file_path = os.path.join(input_dir, filename)
                if not os.path.isfile(file_path):
                    continue

                if filename.endswith('.pdf'):
                    text = self.extract_text_from_pdf(file_path)
                elif filename.endswith('.docx'):
                    text = ""  # or you can implement docx later
                else:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        text = f.read()

                if text:
                    cleaned_text = self.clean_text(text)
                    results.append({
                        'filename': filename,
                        'file_type': 'resume' if subfolder == self.applicant_subdir else 'job_posting',
                        'text': cleaned_text
                    })

        return results

# Optional manual run
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    preprocessor = FilePreprocessor()
    results = preprocessor.process_all()
    print(results)
