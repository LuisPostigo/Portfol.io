import sys
import os
import threading
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QTextEdit, QVBoxLayout, QFileDialog, QMessageBox
)
from PyQt6.QtGui import QPixmap, QDragEnterEvent, QDropEvent, QDrag
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QMimeData
from subprocess import call
from pre_processing import process_files

class DragDropTextEdit(QTextEdit):
    """Custom QTextEdit to properly handle drag-and-drop with QDrag."""
    
    def __init__(self, parent, file_dict, file_type):
        super().__init__(parent)
        self.file_dict = file_dict
        self.file_type = file_type
        self.setAcceptDrops(True)
        self.setPlaceholderText(f"Drop {file_type.replace('_', ' ')} files here...")
        self.setStyleSheet("background-color: white; color: black; font-size: 12px; border: 1px solid gray;")

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Accept drag events if they contain URLs (files)."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        """Handle file drop, store files, and update the UI."""
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            filename = os.path.basename(file_path)

            if file_path.endswith((".pdf", ".txt")):
                self.append(f"• {filename}")
                self.file_dict[file_path] = self.file_type 

                print(f"DEBUG: {self.file_type} file added -> {file_path}")

        print(f"DEBUG: Updated {self.file_type} files: {self.file_dict}")

    def mousePressEvent(self, event):
        """Enable dragging files out of the widget."""
        if event.button() == Qt.MouseButton.LeftButton:
            cursor = self.cursorForPosition(event.pos())
            text = cursor.selectedText()

            if text:
                mime_data = QMimeData()
                mime_data.setText(text)

                drag = QDrag(self)
                drag.setMimeData(mime_data)

                drop_action = drag.exec(Qt.DropAction.CopyAction)

class PortfolIoApp(QWidget):
    """Main application window with a built-in splash overlay animation and drag-and-drop functionality."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Portfol.io")
        self.setFixedSize(600, 600)
        self.setStyleSheet("background-color: white;")

        self.resume_files = {}
        self.job_files = {}

        self.setup_ui()
        self.setup_splash_overlay()

    def setup_ui(self):
        """Set up the main UI elements."""
        layout = QVBoxLayout()

        # Resume Section
        resume_label = QLabel("Drag and Drop Resumes Here or Browse:")
        resume_label.setStyleSheet("color: black; font-size: 14px;")

        self.resume_text = DragDropTextEdit(self, self.resume_files, "resume")

        browse_resume_button = QPushButton("Browse Resumes")
        browse_resume_button.setStyleSheet("""
            background-color: #2196F3;
            color: white;
            font-size: 14px;
            border-radius: 5px;
            padding: 10px;
        """)
        browse_resume_button.clicked.connect(self.browse_resume)

        # Job Posting Section
        job_label = QLabel("Drag and Drop Job Postings Here or Browse:")
        job_label.setStyleSheet("color: black; font-size: 14px;")

        self.job_text = DragDropTextEdit(self, self.job_files, "job_posting")

        browse_job_button = QPushButton("Browse Job Postings")
        browse_job_button.setStyleSheet("""
            background-color: #FF9800;
            color: white;
            font-size: 14px;
            border-radius: 5px;
            padding: 10px;
        """)
        browse_job_button.clicked.connect(self.browse_job_posting)

        # Process Button
        process_button = QPushButton("Process Files")
        process_button.setStyleSheet("""
            background-color: #003366;
            color: white;
            font-size: 16px;
            border-radius: 5px;
            padding: 12px;
        """)
        process_button.clicked.connect(self.gui_process_files)

        # Adds widgets to layout
        layout.addWidget(resume_label)
        layout.addWidget(self.resume_text)
        layout.addWidget(browse_resume_button)
        layout.addWidget(job_label)
        layout.addWidget(self.job_text)
        layout.addWidget(browse_job_button)
        layout.addWidget(process_button)

        self.setLayout(layout)

    def setup_splash_overlay(self):
        """Creates a white overlay with a logo that lifts up to reveal the main window."""
        self.splash_overlay = QWidget(self)
        self.splash_overlay.setGeometry(0, 0, 600, 600)
        self.splash_overlay.setStyleSheet("background-color: white;")

        # Loads and display logo
        logo_path = os.path.join(os.getcwd(), "graphics", "portfolio.png")
        logo_label = QLabel(self.splash_overlay)
        pixmap = QPixmap(logo_path)
        logo_label.setPixmap(pixmap.scaled(400, 400, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Layout for the splash overlay
        layout = QVBoxLayout(self.splash_overlay)
        layout.addWidget(logo_label)
        self.splash_overlay.setLayout(layout)

        # Starts animation after 3 seconds
        QTimer.singleShot(3000, self.start_lift_animation)

    def start_lift_animation(self):
        """Lifts the splash overlay up to reveal the main window."""
        self.animation = QPropertyAnimation(self.splash_overlay, b"geometry")
        self.animation.setDuration(1200)                                # 1.2 seconds smooth transition
        self.animation.setStartValue(self.splash_overlay.geometry())    # Starts at full cover
        self.animation.setEndValue(self.splash_overlay.geometry().translated(0, -self.height()))  # Move up

        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)        # Smooth easing
        self.animation.finished.connect(self.splash_overlay.deleteLater)  # Removes it after animation
        self.animation.start()

    def browse_resume(self):
        """Open file dialog to select resume files and store them."""
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Select Resumes", "", "PDF files (*.pdf);;Text files (*.txt)")
        
        if not file_paths:
            print("DEBUG: No resume files selected.")
            return

        for path in file_paths:
            filename = os.path.basename(path)
            self.resume_text.append(f"• {filename}")
            self.resume_files[path] = "resume"
            print(f"DEBUG: Resume file added via browse -> {path}")

    def browse_job_posting(self):
        """Open file dialog to select job posting files and store them."""
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Select Job Postings", "", "PDF files (*.pdf);;Text files (*.txt)")

        if not file_paths:
            print("DEBUG: No job posting files selected.")
            return

        for path in file_paths:
            filename = os.path.basename(path)
            self.job_text.append(f"• {filename}")
            self.job_files[path] = "job_posting"
            print(f"DEBUG: Job posting file added via browse -> {path}")

    def gui_process_files(self):
        """Processes all collected files and provides user feedback."""
        if not self.resume_files and not self.job_files:
            QMessageBox.warning(self, "Input Error", "Please upload at least one file.")
            return

        all_files = [{'file_path': path, 'file_type': self.resume_files[path]} for path in self.resume_files]
        all_files += [{'file_path': path, 'file_type': self.job_files[path]} for path in self.job_files]

        print(f"DEBUG: Final list of files to process: {all_files}")

        if all_files:
            process_files(all_files)
            QMessageBox.information(self, "Success!", "Files processed and sorted into respective folders successfully.")

    def run_scripts_in_background(self):
        """Runs the external Python script in a separate thread."""
        thread1 = threading.Thread(target=lambda: call(["python", "pre_processing/applicants2KIF.py"]))
        thread2 = threading.Thread(target=lambda: call(["python", "pre_processing/jobPostings2KIF.py"]))

        thread1.start()
        thread2.start()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    main_window = PortfolIoApp()
    main_window.show()

    sys.exit(app.exec())
