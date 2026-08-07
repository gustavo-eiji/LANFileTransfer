import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox

from config import Config
from devicemanager import DeviceManager
from discovery import Discovery
from settings import APP_NAME, APP_VERSION
from transfer import TransferClient, TransferServer
import threading
import os

from qrcode.main import QRCode
from qrcode.constants import ERROR_CORRECT_M
from PIL import ImageTk

from tkinterdnd2 import TkinterDnD, DND_FILES

# Must match the prefix the Android app's QR scanner looks for.
QR_PAIRING_PREFIX = "LANFTSALT1:"

class MainWindow:

    def __init__(
            self,
            device_manager: DeviceManager,
            discovery: Discovery,
            transfer_server: TransferServer,
            transfer_client: TransferClient,
            config: Config,
    ):

        # Instance attributes
        self.device_manager = device_manager
        self.discovery = discovery
        self.transfer_server = transfer_server
        self.transfer_client = transfer_client
        self.config = config

        # UI-related attributes
        self.device_table: ttk.Treeview
        self.refresh_button: ttk.Button
        self.send_button: ttk.Button
        self.send_folder_button: ttk.Button
        self.settings_button: ttk.Button
        self.qr_button: ttk.Button
        self.status: tk.StringVar
        self.status_label: ttk.Label
        self.progress: tk.DoubleVar
        self.progress_bar: ttk.Progressbar

        self.root = TkinterDnD.Tk()

        self.root.title(f"{APP_NAME} {APP_VERSION}")
        self.root.geometry("700x450")

        self.create_table()
        self.create_buttons()
        self.create_status_bar()
        self.create_progress_bar()
        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.on_close,
        )

    def run(self):
        self.root.mainloop()

    def on_close(self):
        self.root.destroy()

    def create_table(self):
        # noinspection PyAttributeOutsideInit
        self.device_table = ttk.Treeview(
            self.root,
            columns=("hostname", "os", "ip", "port"),
            show="headings",
            height=12,
        )

        self.device_table.heading("hostname", text="Hostname")
        self.device_table.heading("os", text="OS")
        self.device_table.heading("ip", text="IP Address")
        self.device_table.heading("port", text="Port")

        self.device_table.column("hostname", width=250)
        self.device_table.column("os", width=120)
        self.device_table.column("ip", width=180)
        self.device_table.column("port", width=180)

        self.device_table.pack(fill="both", expand=True, padx=10, pady=10)

        # Drag & Drop
        # noinspection PyUnresolvedReferences
        self.device_table.drop_target_register(DND_FILES)
        # noinspection PyUnresolvedReferences
        self.device_table.dnd_bind("<<Drop>>", self.on_files_dropped)

    def create_buttons(self):

        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill="x", padx=10)

        ### REFRESH
        # noinspection PyAttributeOutsideInit
        self.refresh_button = ttk.Button(
            button_frame,
            text="Refresh",
            command=self.refresh_devices
        )
        self.refresh_button.pack(side="left")

        ### SEND FILE
        # noinspection PyAttributeOutsideInit
        self.send_button = ttk.Button(
            button_frame,
            text="Send File",
            command=self.send_file,
        )
        self.send_button.pack(side="right")

        # SEND FOLDER
        # noinspection PyAttributeOutsideInit
        self.send_folder_button = ttk.Button(
            button_frame,
            text="Send Folder",
            command=self.send_folder_dialog,
        )
        self.send_folder_button.pack(side="right", padx=5)

        ### SETTINGS
        # noinspection PyAttributeOutsideInit
        self.settings_button = ttk.Button(
            button_frame,
            text="Settings",
            command=self.user_settings,
        )
        self.settings_button.pack(side="left", padx=5)

        ### PAIRING QR
        # noinspection PyAttributeOutsideInit
        self.qr_button = ttk.Button(
            button_frame,
            text="Pairing QR",
            command=self.show_pairing_qr,
        )
        self.qr_button.pack(side="left", padx=1)

    def refresh_devices(self):
        self.device_table.delete(
            *self.device_table.get_children()
        )

        for device in self.device_manager.get_devices():

            is_local = device.device_id == self.discovery.device_id
            hostname = device.hostname

            # Tags your own device on the GUI table
            if is_local:
                hostname += " (Your Device)"

            self.device_table.insert(
                "",
                "end",
                iid=device.device_id,
                values=(
                    hostname,
                    device.operating_system,
                    device.ip_address,
                    device.port,
                )
            )

    def get_selected_device(self):
        selection = self.device_table.selection()

        if not selection:
            messagebox.showwarning(
                title="No device selected",
                message="Please select a device before sending files."
            )
            return None

        device_id = selection[0]
        #return self.device_manager.devices[device_id]

        device = self.device_manager.devices.get(device_id)

        if device is None:
            messagebox.showwarning(
                title="Location no longer available",
                message="Selected device or folder location is no longer available. Refresh device list and re-select the save folder location."
            )
            return None

        return device

    def collect_files(self, paths):
        files = []
        seen = set()
        MAX_FILES = 5000
        MAX_SIZE_GB = 10
        total_size = 0

        for raw in paths:
            path = Path(raw)

            # Reject symlinks at the top level
            if path.is_symlink():
                messagebox.showwarning(
                    "Symlink detected",
                    f"{path} is a symbolic link. For security, symlinks are not followed."
                )
                continue

            if path.is_dir():
                for root, _dirs, filenames in os.walk(path, followlinks=False):
                    root_path = Path(root)

                    # Skip if the directory itself is a symlink
                    if root_path.is_symlink():
                        continue

                    for fn in filenames:
                        full_path = Path(root) / fn
                        full_str = str(full_path)

                        # Skip symlinked files
                        if full_path.is_symlink():
                            continue

                        if full_str not in seen:
                            seen.add(full_str)

                            # Check limits
                            if len(files) >= MAX_FILES:
                                messagebox.showerror(
                                    "Too many files",
                                    f"Folder contains more than {MAX_FILES} files. "
                                    "Please select a smaller folder."
                                )
                                return []

                            try:
                                file_size = full_path.stat().st_size
                                total_size += file_size

                                if total_size > MAX_SIZE_GB * 1024 ** 3:
                                    messagebox.showerror(
                                        "Folder too large",
                                        f"Total size exceeds {MAX_SIZE_GB}GB limit."
                                    )
                                    return []
                            except OSError:
                                continue  # Skip files we can't read

                            files.append(full_str)

            elif path.is_file():
                if not path.is_symlink() and raw not in seen:  # ✅ Also check symlink for files
                    seen.add(raw)
                    try:
                        file_size = path.stat().st_size
                        total_size += file_size
                    except OSError:
                        pass
                    files.append(raw)

        # Show confirmation before sending
        if files:
            total_size_mb = total_size / (1024 ** 2)
            response = messagebox.askyesno(
                "Confirm send",
                f"Send {len(files)} file(s) ({total_size_mb:.1f} MB)?"
            )
            if not response:
                return []

        return files

    def send_file(self):

        device = self.get_selected_device()
        if device is None:
            return

        filename = filedialog.askopenfilename()
        if not filename:
            return

        self.start_batch_transfer([filename], device)


    def send_folder_dialog(self):
        device = self.get_selected_device()
        if device is None:
            return

        folder = filedialog.askdirectory()

        if not folder:
            return

        self.start_batch_transfer([folder], device)

    def on_files_dropped(self, event):
        # event.data can contain multiple paths, space-separated; any path
        # containing spaces is wrapped in {}. tk's splitlist() parses both
        # cases correctly -- this is the standard tkinterdnd2 pattern.
        paths = list(self.root.tk.splitlist(event.data))

        if not paths:
            return

        # Prefer the row the files were actually dropped on.
        try:
            local_y = event.y_root - self.device_table.winfo_rooty()
            row_id = self.device_table.identify_row(local_y)
            device = self.device_manager.devices.get(row_id)
        except (AttributeError, tk.TclError):
            device = None

        # Fall back to whatever's currently selected, if any.
        if device is None:
            selection = self.device_table.selection()
            if selection:
                # device = self.device_manager.devices[selection[0]]
                device = self.device_manager.devices.get(selection[0])

        if device is None:
            messagebox.showwarning(
                title="No device selected",
                message="Drop files onto a specific device row, or select "
                        "a device first, then drop.",
            )
            return

        self.start_batch_transfer(paths, device)


    def start_batch_transfer(self, raw_paths, device):
        files = self.collect_files(raw_paths)

        if not files:
            messagebox.showinfo(
                "Nothing to send",
                "No files were found in the selected item(s).",
            )
            return

        self.send_button.config(state="disabled")
        self.send_folder_button.config(state="disabled")
        self.refresh_button.config(state="disabled")

        threading.Thread(
            target=self.batch_transfer_worker,
            args=(files, device),
            daemon=True,
        ).start()

    def batch_transfer_worker(self, files, device):
        total = len(files)
        succeeded = 0
        failed = []

        try:
            for index, filename in enumerate(files, start=1):
                display_name = Path(filename).name

                self.root.after(
                    0,
                    lambda i=index, n=total, name=display_name: (
                        self.progress.set(0) if self.progress else None,
                        self.status.set(f"Sending {i}/{n}: {name}") if self.status else None,
                    ),
                )

                try:
                    success, message = self.transfer_client.send_file(
                        filename,
                        device.ip_address,
                        device.port,
                        progress_callback=self.update_progress,
                    )
                except Exception as e:
                    success, message = False, str(e)

                if success:
                    succeeded += 1
                else:
                    failed.append((display_name, message))

        except Exception as e:
            failed.append(("Unexpected error", str(e)))

        finally:
            self.root.after(
                0,
                lambda: self.finish_batch_transfer(succeeded, failed, total),
            )

    def finish_batch_transfer(self, succeeded, failed, total):
        self.send_button.config(state="normal")
        self.send_folder_button.config(state="normal")
        self.refresh_button.config(state="normal")
        self.progress.set(0)

        if not failed:
            self.status.set(f"Sent {succeeded}/{total} file(s) successfully.")
            messagebox.showinfo(
                "Transfer complete",
                f"Sent {succeeded}/{total} file(s) successfully.",
            )
        else:
            self.status.set(f"Sent {succeeded}/{total} file(s), {len(failed)} failed.")
            details = "\n".join(f"- {name}: {reason}" for name, reason in failed[:10])
            if len(failed) > 10:
                details += f"\n... and {len(failed) - 10} more."
            messagebox.showwarning(
                "Some transfers failed",
                f"{succeeded}/{total} succeeded.\n\nFailed:\n{details}",
            )

    def user_settings(self):

        window = tk.Toplevel(self.root)
        window.title("Settings")
        window.geometry("350x220")
        window.resizable(False, False)

        # Password
        ttk.Label(
            window,
            text="Set new password"
        ).pack(anchor="w", padx=10, pady=(10, 0))

        security_entry = ttk.Entry(window, width=40)
        security_entry.pack(fill="x", padx=10)

        # Save Folder
        ttk.Label(
            window,
            text="Save received files to"
        ).pack(anchor="w", padx=10, pady=(15, 0))

        folder_var = tk.StringVar(value=self.config.save_folder)

        ttk.Label(
            window,
            textvariable=folder_var,
            wraplength=400,
        ).pack(anchor="w", padx=10)

        ttk.Button(
            window,
            text="Browse...",
            command=lambda: self.choose_folder(folder_var),
        ).pack(anchor="w", padx=10, pady=5)

        ttk.Button(
            window,
            text="Save",
            command=lambda: self.save_settings(
                security_entry.get(),
                window,
            ),
        ).pack(pady=15)

    def save_settings(self, security_code: str, window):

        self.config.set_new_code(security_code)

        self.status.set("Settings saved.")

        window.destroy()

    def choose_folder(self, folder_var):

        folder = filedialog.askdirectory(
            title="Select destination folder"
        )

        if folder:
            self.config.set_save_folder(folder)
            folder_var.set(folder)

    # ADDED FOR ANDROID QR PAIRING
    def show_pairing_qr(self):
        if not self.config.security_salt:
            messagebox.showwarning(
                title="No password set",
                message="Set a password under Settings first, then click "
                        "Pairing QR again to generate a code for your phone.",
            )
            return

        qr_payload = f"{QR_PAIRING_PREFIX}{self.config.security_salt}"

        qr = QRCode(
            version=None,
            error_correction=ERROR_CORRECT_M,
            box_size=8,
            border=4,
        )
        qr.add_data(qr_payload)
        qr.make(fit=True)
        image = qr.make_image(fill_color="black", back_color="white").convert("RGB")

        window = tk.Toplevel(self.root)
        window.title("Pairing QR")
        window.resizable(False, False)

        # Keep a reference on the window itself -- otherwise Tkinter's
        # garbage collector can drop the image before it's ever drawn.
        window.qr_photo = ImageTk.PhotoImage(image)

        ttk.Label(window, image=window.qr_photo).pack(padx=15, pady=(15, 5))

        ttk.Label(
            window,
            text=(
                "Scan this from the Android app's \"Scan to pair\" button.\n"
                "This code changes every time you set a new password here --\n"
                "rescan after changing your password."
            ),
            justify="center",
        ).pack(padx=15, pady=(0, 15))


    def create_status_bar(self):

        # noinspection PyAttributeOutsideInit
        self.status = tk.StringVar(value="Listening...")

        # noinspection PyAttributeOutsideInit
        self.status_label = ttk.Label(
            self.root,
            textvariable=self.status,
            relief="sunken",
            anchor="w",
        )

        self.status_label.pack(
            fill="x",
            side="bottom",
            padx=10,
            pady=10,
        )

    def create_progress_bar(self):
        # noinspection PyAttributeOutsideInit
        self.progress = tk.DoubleVar(value=0)

        # noinspection PyAttributeOutsideInit
        self.progress_bar = ttk.Progressbar(
            self.root,
            variable=self.progress,
            maximum=100,
            mode="determinate",
        )

        self.progress_bar.pack(
            fill="x", padx=10, pady=(0, 10),
                               )

    def update_progress(self, percent):
        self.root.after(
            0,
            lambda: self.progress.set(percent)
        )