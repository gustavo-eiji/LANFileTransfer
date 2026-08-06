import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox

from config import Config
from devicemanager import DeviceManager
from discovery import Discovery
from settings import APP_NAME, APP_VERSION
from transfer import TransferClient, TransferServer
import threading

from qrcode.main import QRCode
from qrcode.constants import ERROR_CORRECT_M
from PIL import ImageTk

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

        self.progress_bar = None
        self.device_manager = device_manager
        self.discovery = discovery
        self.transfer_server = transfer_server
        self.transfer_client = transfer_client
        self.config = config

        self.root = tk.Tk()

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

    def create_buttons(self):

        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill="x", padx=10)

        ### REFRESH
        self.refresh_button = ttk.Button(
            button_frame,
            text="Refresh",
            command=self.refresh_devices
        )
        self.refresh_button.pack(side="left")

        ### SEND FILE
        self.send_button = ttk.Button(
            button_frame,
            text="Send File",
            command=self.send_file,
        )
        self.send_button.pack(side="right")

        ### SETTINGS
        self.settings_button = ttk.Button(
            button_frame,
            text="Settings",
            command=self.user_settings,
        )
        self.settings_button.pack(side="left", padx=5)

        ### PAIRING QR -- ADDED FOR ANDROID QR PAIRING
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

    def send_file(self):

        selection = self.device_table.selection()

        if not selection:
            print("No device selected")
            messagebox.showwarning(
                title="No device selected",
                message="Please select a device before sending a file."
            )
            return

        device_id = selection[0]

        device = self.device_manager.devices[device_id]

        filename = filedialog.askopenfilename()

        if not filename:
            return

        self.progress.set(0)
        self.status.set(f"Sending {Path(filename).name}")

        # Disable Send button during transfer
        self.send_button.config(state="disabled")
        self.refresh_button.config(state="disabled")

        threading.Thread(
            target=self.transfer_worker,
            args=(filename, device),
            daemon=True,
        ).start()




    def transfer_worker(self, filename, device):

        try:
            success, message = self.transfer_client.send_file(
                filename,
                device.ip_address,
                device.port,
                progress_callback=self.update_progress,
            )


        except Exception as e:
            self.root.after(
                0,
                lambda: (
                    self.send_button.config(state="normal"),
                    self.refresh_button.config(state="normal"),
                    messagebox.showerror(
                        "Unexpected Error",
                        str(e),
                    ),
                    self.status.set("Transfer Failed"),
                ),
            )

            return


        if success:
            self.root.after(
                0,
                lambda: messagebox.showinfo(
                    "Transfer complete",
                    message,
                )
            )

        else:
            self.root.after(
                0,
                lambda: messagebox.showinfo(
                    "Transfer Failed",
                    message,
                )
            )

        self.send_button.config(state="normal")
        self.refresh_button.config(state="normal")
        self.root.after(2000, lambda: self.progress.set(0))

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

        # ttk.Button(
        #     window,
        #     text="Save",
        #     command=lambda: self.save_settings(
        #         security_entry.get(),
        #         window,
        #     ),
        # ).pack(pady=15)

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

        self.status = tk.StringVar(value="Listening...")

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
        self.progress = tk.DoubleVar(value=0)

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