import os
import shutil
import logging
import fitz

def clean_text(text):
    """
    Cleans up text extracted from files by removing excessive blank lines.
    """
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

def extract_text_from_pdf(pdf_path):
    """
    Extracts text from a PDF file using PyMuPDF (fitz).
    Handles exceptions and returns cleaned text or an error message.
    """
    try:
        doc = fitz.open(pdf_path)
        text = "\n".join(page.get_text() for page in doc)
        return clean_text(text.strip())
    except Exception as e:
        return f"Error extracting PDF content: {e}"
    
def copy_to_raw(file_path, raw_dir):
    """
    Copies a file to the raw directory, logging the action.
    """
    filename = os.path.basename(file_path)
    dest_path = os.path.join(raw_dir, filename)

    print("Attempting to copy from:", file_path, "to:", dest_path)

    if not os.path.exists(file_path):
        print("Error: File does not exist:", file_path)
        return None

    shutil.copy(file_path, dest_path)
    return dest_path

def process_files(file_paths):
    """
    Processes a list of files, copying them to a raw directory, extracting text,
    and saving cleaned text to a pre-processed directory based on file type.
    """
    base_dir = os.path.join(os.getcwd(), 'datasets')
    raw_dir = os.path.join(base_dir, 'raw')
    pre_processed_dir = os.path.join(base_dir, 'pre-processed')
    
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(pre_processed_dir, exist_ok=True)
    
    for file_info in file_paths:
        file_type = file_info['file_type']
        specific_dir = os.path.join(pre_processed_dir, 'applicants' if file_type == 'resume' else 'jobPostings')
        os.makedirs(specific_dir, exist_ok=True)

        original_file_path = file_info['file_path']
        copied_file_path = copy_to_raw(original_file_path, raw_dir)

        if copied_file_path:
            filename = os.path.basename(copied_file_path)
            output_file_path = os.path.join(specific_dir, f"{os.path.splitext(filename)[0]}.txt")

            try:
                if copied_file_path.endswith('.pdf'):
                    text = extract_text_from_pdf(copied_file_path)
                elif copied_file_path.endswith('.docx'):
                    pass
                else:
                    with open(copied_file_path, 'r') as file:
                        text = file.read()
                
                text = clean_text(text)

                with open(output_file_path, "w") as file:
                    file.write(text)
                
                logging.info(f"Processed and saved: {output_file_path}")
            except Exception as e:
                logging.error(f"Failed to process {copied_file_path}: {str(e)}")
        else:
            logging.error(f"Skipping file due to copying error: {original_file_path}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    file_list = [
        {'file_path': '/path/to/resume1.pdf', 'file_type': 'resume'},
        {'file_path': '/path/to/job1.txt', 'file_type': 'job_posting'}
    ]
    process_files(file_list)
