import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import threading
import sys
import os
from config import DEFAULT_GAME_ID, DEFAULT_OUTPUT_FOLDER

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("ThreadPuller & GDocs Uploader")
        self.root.geometry("600x500")

        # Game ID
        tk.Label(root, text="GAME_ID:").grid(row=0, column=0, padx=10, pady=10, sticky="e")
        
        # Validation for Game ID (numbers only)
        vcmd = (root.register(self.validate_game_id), '%P')
        self.game_id_var = tk.StringVar(value=DEFAULT_GAME_ID)
        self.game_id_entry = tk.Entry(root, textvariable=self.game_id_var, validate='key', validatecommand=vcmd)
        self.game_id_entry.grid(row=0, column=1, padx=10, pady=10, sticky="we")

        # Folder
        tk.Label(root, text="Folder:").grid(row=1, column=0, padx=10, pady=10, sticky="e")
        self.folder_var = tk.StringVar(value=DEFAULT_OUTPUT_FOLDER)
        self.folder_entry = tk.Entry(root, textvariable=self.folder_var)
        self.folder_entry.grid(row=1, column=1, padx=10, pady=10, sticky="we")
        
        self.browse_btn = tk.Button(root, text="Browse", command=self.browse_folder)
        self.browse_btn.grid(row=1, column=2, padx=10, pady=10)

        # Buttons
        self.btn_frame = tk.Frame(root)
        self.btn_frame.grid(row=2, column=0, columnspan=3, pady=10)

        self.download_btn = tk.Button(self.btn_frame, text="DOWNLOAD", width=15, command=self.run_download)
        self.download_btn.pack(side=tk.LEFT, padx=10)

        self.upload_btn = tk.Button(self.btn_frame, text="UPLOAD", width=15, command=self.run_upload)
        self.upload_btn.pack(side=tk.LEFT, padx=10)

        # Output Text
        tk.Label(root, text="Output:").grid(row=3, column=0, padx=10, sticky="nw")
        
        # Add a scrollbar to the text widget
        self.text_frame = tk.Frame(root)
        self.text_frame.grid(row=4, column=0, columnspan=3, padx=10, pady=5, sticky="nsew")
        
        self.output_text = tk.Text(self.text_frame, height=15, width=60, state=tk.DISABLED)
        self.output_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.scrollbar = tk.Scrollbar(self.text_frame, command=self.output_text.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.output_text.config(yscrollcommand=self.scrollbar.set)

        # Configure resizing
        root.grid_columnconfigure(1, weight=1)
        root.grid_rowconfigure(4, weight=1)

    def validate_game_id(self, P):
        if str.isdigit(P) or P == "":
            return True
        else:
            return False

    def browse_folder(self):
        # Default to the current entry value if it's a valid directory
        initial_dir = self.folder_var.get()
        if not os.path.isdir(initial_dir):
            initial_dir = os.path.dirname(os.path.abspath(__file__))
            
        folder_selected = filedialog.askdirectory(initialdir=initial_dir)
        if folder_selected:
            # Normalize path for Windows to use backslashes, though both work
            self.folder_var.set(os.path.normpath(folder_selected))

    def append_output(self, text):
        self.output_text.config(state=tk.NORMAL)
        self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)
        self.output_text.config(state=tk.DISABLED)

    def run_script(self, cmd):
        self.download_btn.config(state=tk.DISABLED)
        self.upload_btn.config(state=tk.DISABLED)
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete(1.0, tk.END)
        self.output_text.config(state=tk.DISABLED)

        def worker():
            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )

                for line in process.stdout:
                    self.root.after(0, self.append_output, line)

                process.stdout.close()
                process.wait()
                self.root.after(0, self.append_output, f"\nProcess finished with code {process.returncode}\n")
            except Exception as e:
                self.root.after(0, self.append_output, f"\nError running script: {str(e)}\n")
            finally:
                self.root.after(0, lambda: self.download_btn.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.upload_btn.config(state=tk.NORMAL))

        threading.Thread(target=worker, daemon=True).start()

    def run_download(self):
        game_id = self.game_id_var.get().strip()
        folder = self.folder_var.get().strip()
        if not game_id:
            messagebox.showerror("Error", "Please enter a GAME_ID")
            return
        if not folder:
            messagebox.showerror("Error", "Please select a folder")
            return
            
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "download_threads.py")
        cmd = [sys.executable, "-u", script_path, "--game_id", game_id, "--output_folder", folder]
        self.run_script(cmd)

    def run_upload(self):
        folder = self.folder_var.get().strip()
        if not folder:
            messagebox.showerror("Error", "Please select a folder")
            return
            
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "upload_to_gdocs.py")
        cmd = [sys.executable, "-u", script_path, "--input_folder", folder]
        self.run_script(cmd)

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
