import tkinter as tk
from tkinter import filedialog, messagebox
import os
import fitz  # this does the PyMuPDF for PDF extraction

def clean_text(text):
    """Cleans the text by removing excessive blank lines."""
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
    """Extracts text from the given PDF file."""
    try:
        doc = fitz.open(pdf_path)
        text = "".join(page.get_text() for page in doc)
        return text.strip()
    except Exception as e:
        return f"Error extracting PDF content: {e}"
    
def browse_resume():
    """Opens a file dialog to select a resume file."""
    file_path = filedialog.askopenfilename(title="Select Resume", 
                                           filetypes=[("PDF files", "*.pdf"),       # so far it supports pdf files
                                                       ("Text files", "*.txt")])    # and text files
    if file_path:
        resume_entry.delete(0, tk.END)
        resume_entry.insert(0, file_path)

def browse_job_posting():
    """Opens a file dialog to select a job posting file."""
    file_path = filedialog.askopenfilename(title="Select Job Posting", 
                                           filetypes=[("PDF files", "*.pdf"), 
                                                      ("Text files", "*.txt")])
    if file_path:
        job_entry.delete(0, tk.END)
        job_entry.insert(0, file_path)

def process_files():
    """Processes the uploaded resume and job posting. handling error scenarios."""
    resume_path = resume_entry.get()
    job_path = job_entry.get()

    # Exception 1: Are both files paths provided?
    if not resume_path or not job_path:
        messagebox.showwarning("Input Error", "Please upload both Resume and Job Posting.")
        return
    
    # Exception 2: Do the files exist?
    if not os.path.exists(resume_path) or not os.path.exists(job_path):
        messagebox.showerror("File Error", "One or both files do not exist.")
        return

    resume_text = extract_text_from_pdf(resume_path)
    job_text = extract_text_from_pdf(job_path)

    # Creates resume.txt and jobPosting.txt files for both uploaded files.
    with open("resume.txt", "w") as resume_file:
        resume_file.write(resume_text)
    
    with open("jobPosting.txt", "w") as job_file:
        job_file.write(job_text)

    messagebox.showinfo("Success!", f"Resume and Job Posting received:\nResume: {resume_path}\nJob Posting: {job_path}")
    messagebox.showinfo("Extraction Complete", "Information extracted and saved to 'resume.txt' and 'jobPosting.txt'")

####################################################################################
#                                  GUI Setup                                       #
####################################################################################

root = tk.Tk()
root.title("Recruiter Agent: Resume & Job Posting Uploader")
root.geometry("500x300")
root.resizable(False, False)

# Resume
tk.Label(root, text="Upload Resume:").pack(pady=5)
resume_entry = tk.Entry(root, width=50)
resume_entry.pack(pady=5)
tk.Button(root, text="Browse", command=browse_resume).pack(pady=5)

# Job Posting
tk.Label(root, text="Upload Job Posting:").pack(pady=5)
job_entry = tk.Entry(root, width=50)
job_entry.pack(pady=5)
tk.Button(root, text="Browse", command=browse_job_posting).pack(pady=5)

# Submit Button
tk.Button(root, text="Process Files", command=process_files, bg="green", fg="white").pack(pady=20)

if __name__ == "__main__":
    root.mainloop()
