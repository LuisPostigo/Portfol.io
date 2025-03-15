import os
from subprocess import call
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD

from pre_processing import process_files

class DragDropFiles:
    def __init__(self, root):
        """Initialize the GUI elements for the application."""
        self.root = root
        self.root.title("Portfol.io")
        self.root.geometry("600x600")
        self.cwd = os.getcwd()

        self.resume_files = {}
        self.job_files = {}

        self.setup_resume_interface()
        self.setup_job_interface()
        self.setup_process_button()

    def setup_resume_interface(self):
        """Sets up the interface for resume file input."""
        resume_label = tk.Label(self.root, text="Drag and Drop Resumes Here or Browse:")
        resume_label.pack(pady=5)
        self.resume_text = tk.Text(self.root, height=10, width=50)
        self.resume_text.pack(pady=5)
        self.resume_text.drop_target_register(DND_FILES)
        self.resume_text.dnd_bind('<<Drop>>', self.drop_resume)
        resume_browse_button = tk.Button(self.root, text="Browse Resumes", command=self.browse_resume)
        resume_browse_button.pack(pady=5)

    def setup_job_interface(self):
        """Sets up the interface for job posting file input."""
        job_label = tk.Label(self.root, text="Drag and Drop Job Postings Here or Browse:")
        job_label.pack(pady=5)
        self.job_text = tk.Text(self.root, height=10, width=50)
        self.job_text.pack(pady=5)
        self.job_text.drop_target_register(DND_FILES)
        self.job_text.dnd_bind('<<Drop>>', self.drop_job_posting)
        job_browse_button = tk.Button(self.root, text="Browse Job Postings", command=self.browse_job_posting)
        job_browse_button.pack(pady=5)

    def setup_process_button(self):
        """Creates a button to process the input files."""
        process_button = tk.Button(self.root, text="Process Files", command=self.gui_process_files, bg="green", fg="white")
        process_button.pack(pady=20)

    def drop_resume(self, event):
        """Handles dropping resume files into the text box."""
        files = self.root.tk.splitlist(event.data)
        for file in files:
            filename = os.path.basename(file)
            self.resume_text.insert(tk.END, f"• {filename}\n")
            self.resume_files[file] = 'resume'

    def drop_job_posting(self, event):
        """Handles dropping job posting files into the text box."""
        files = self.root.tk.splitlist(event.data)
        for file in files:
            filename = os.path.basename(file)
            self.job_text.insert(tk.END, f"• {filename}\n")
            self.job_files[file] = 'job_posting'

    def browse_resume(self):
        """Opens a file dialog to browse and select resume files."""
        file_paths = filedialog.askopenfilenames(title="Select Resumes", filetypes=[("PDF files", "*.pdf"), ("Text files", "*.txt")])
        for path in file_paths:
            filename = os.path.basename(path)
            self.resume_text.insert(tk.END, f"• {filename}\n")
            self.resume_files[path] = 'resume'

    def browse_job_posting(self):
        """Opens a file dialog to browse and select job posting files."""
        file_paths = filedialog.askopenfilenames(title="Select Job Postings", filetypes=[("PDF files", "*.pdf"), ("Text files", "*.txt")])
        for path in file_paths:
            filename = os.path.basename(path)
            self.job_text.insert(tk.END, f"• {filename}\n")
            self.job_files[path] = 'job_posting'

    def gui_process_files(self):
        """Processes all collected files and provides user feedback."""
        all_files = [{'file_path': path, 'file_type': self.resume_files[path]} for path in self.resume_files]
        all_files += [{'file_path': path, 'file_type': self.job_files[path]} for path in self.job_files]

        if all_files:
            process_files(all_files)
            messagebox.showinfo("Success!", "Files processed and sorted into respective folders successfully.")
        else:
            messagebox.showwarning("Input Error", "Please upload at least one file.")

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = DragDropFiles(root)
    root.mainloop()

    call(["python", "pre_processing/applicants2KIF.py"])
