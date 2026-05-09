import os
import subprocess
import sys
import traceback
from pathlib import Path

def print_dependency_help(app_name, missing_package):
    print(f"{app_name} requires {missing_package}, but it is not installed in this Python environment.")
    print("Install the required packages, then run the app again:")
    if sys.platform.startswith("win"):
        print("  py -m pip install PyQt6 pyserial")
        print("  py D:\\p1loader\\PMC8_Dashboard.py")
    elif sys.platform == "darwin":
        print("  python3 -m pip install PyQt6 pyserial")
        print("  cd /path/to/p1loader")
        print("  python3 PMC8_Dashboard.py")
    else:
        print("  python3 -m pip install PyQt6 pyserial")
        print("  cd /path/to/p1loader")
        print("  python3 PMC8_Dashboard.py")

try:
    from PyQt6.QtCore import QObject, QThread, pyqtSignal
    from PyQt6.QtWidgets import (
        QCheckBox,
        QDialog,
        QFileDialog,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QPushButton,
        QTextEdit,
        QVBoxLayout,
    )
except ModuleNotFoundError as exc:
    if exc.name == "PyQt6":
        print_dependency_help("PMC8 uploader", "PyQt6")
        sys.exit(1)
    raise

from propeller_uploader import LoaderError, upload as propeller_upload


class UploadWorker(QObject):
    progress = pyqtSignal(str)
    finished = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self, serial_port, file_path, eeprom, run_after):
        super().__init__()
        self.serial_port = serial_port
        self.file_path = file_path
        self.eeprom = eeprom
        self.run_after = run_after

    def run(self):
        try:
            if sys.platform == "darwin":
                self._run_macos_p1load()
            else:
                propeller_upload(
                    self.serial_port,
                    self.file_path,
                    eeprom=self.eeprom,
                    run=self.run_after,
                    gpio_pin=-1,
                    progress=self.progress.emit,
                    terminal=False,
                )
            self.finished.emit()
        except LoaderError as exc:
            self.failed.emit(str(exc))
        except Exception:
            self.failed.emit(traceback.format_exc())

    def _run_macos_p1load(self):
        app_dir = Path(__file__).resolve().parent
        p1load = app_dir / "p1load_package (1)" / "p1load"
        if not p1load.is_file():
            raise LoaderError(f"Bundled macOS p1load was not found: {p1load}")

        try:
            p1load.chmod(p1load.stat().st_mode | 0o755)
        except OSError as exc:
            self.progress.emit(f"Warning: could not mark p1load executable: {exc}")

        cmd = [str(p1load), "-p", self.serial_port]
        if self.eeprom:
            cmd.append("-e")
        cmd.append(self.file_path)
        if self.run_after:
            cmd.append("-r")

        self.progress.emit("Using bundled macOS p1load.")
        self.progress.emit("Command: " + " ".join(cmd))
        proc = subprocess.run(
            cmd,
            cwd=str(p1load.parent),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        output = proc.stdout.strip()
        if output:
            for line in output.splitlines():
                self.progress.emit(line)
        if proc.returncode != 0:
            raise LoaderError(f"p1load failed with exit code {proc.returncode}")


class UploadDialog(QDialog):
    def __init__(self, parent=None, serial_port=""):
        super().__init__(parent)
        self.thread = None
        self.worker = None
        self.setWindowTitle("Propeller Code Uploader")
        self.resize(560, 360)
        self._build_ui(serial_port)

    def _build_ui(self, serial_port):
        layout = QVBoxLayout()

        file_row = QHBoxLayout()
        self.file_edit = QLineEdit()
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_file)
        file_row.addWidget(QLabel("Binary File:"))
        file_row.addWidget(self.file_edit, 1)
        file_row.addWidget(browse_btn)
        layout.addLayout(file_row)

        port_row = QHBoxLayout()
        self.port_edit = QLineEdit(serial_port)
        port_row.addWidget(QLabel("Serial Port:"))
        port_row.addWidget(self.port_edit, 1)
        layout.addLayout(port_row)

        self.eeprom_checkbox = QCheckBox("Write to EEPROM")
        self.eeprom_checkbox.setChecked(True)
        self.run_checkbox = QCheckBox("Run after upload")
        self.run_checkbox.setChecked(True)
        layout.addWidget(self.eeprom_checkbox)
        layout.addWidget(self.run_checkbox)

        self.progress_box = QTextEdit()
        self.progress_box.setReadOnly(True)
        layout.addWidget(QLabel("Status:"))
        layout.addWidget(self.progress_box, 1)

        button_row = QHBoxLayout()
        self.upload_btn = QPushButton("Upload")
        self.upload_btn.clicked.connect(self.start_upload)
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        button_row.addWidget(self.upload_btn)
        button_row.addWidget(self.close_btn)
        layout.addLayout(button_row)

        self.setLayout(layout)

    def browse_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select Propeller Binary",
            "",
            "Propeller Binary (*.binary *.eeprom *.bin);;All Files (*)",
        )
        if filename:
            self.file_edit.setText(filename)

    def log_progress(self, message):
        self.progress_box.append(str(message))

    def start_upload(self):
        serial_port = self.port_edit.text().strip()
        file_path = self.file_edit.text().strip()

        if not serial_port:
            self.log_progress("Serial port is required.")
            return
        if not file_path:
            self.log_progress("Binary file is required.")
            return
        if not os.path.isfile(file_path):
            self.log_progress(f"File not found: {file_path}")
            return

        self.upload_btn.setEnabled(False)
        self.close_btn.setEnabled(False)
        self.log_progress(f"Uploading {file_path} to {serial_port}...")

        self.thread = QThread(self)
        self.worker = UploadWorker(
            serial_port,
            file_path,
            self.eeprom_checkbox.isChecked(),
            self.run_checkbox.isChecked(),
        )
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.log_progress)
        self.worker.finished.connect(self._upload_finished)
        self.worker.failed.connect(self._upload_failed)
        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self._thread_finished)

        self.thread.start()

    def _upload_finished(self):
        self.log_progress("Upload complete.")

    def _upload_failed(self, message):
        self.log_progress("Upload failed:")
        self.log_progress(message)

    def _thread_finished(self):
        self.upload_btn.setEnabled(True)
        self.close_btn.setEnabled(True)
        self.thread = None
        self.worker = None
