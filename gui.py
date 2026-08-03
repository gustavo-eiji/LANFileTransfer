import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox

from config import Config
from devicemanager import DeviceManager
from discovery import Discovery
from settings import APP_NAME, APP_VERSION
from transfer import TransferClient, TransferServer


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
        self.settings_button.pack(side="bottom")

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
                detail="Please select a device before sending a file."
            )
            return

        device_id = selection[0]

        device = self.device_manager.devices[device_id]

        filename = filedialog.askopenfilename()

        if not filename:
            return

        self.progress.set(0)

        try:
            self.status.set(f"Sending {Path(filename).name}")

            success, message = self.transfer_client.send_file(
            filename,
            device.ip_address,
            device.port,
            progress_callback=self.update_progress,
        )

        except Exception as e:
            messagebox.showerror(
                title="Unexpected Error",
                message=str(e),
            )
            return


        if success:
            messagebox.showinfo(
                "Transfer complete",
                message
            )
            self.status.set(f"{Path(filename).name} Transfer Complete")
        else:
            messagebox.showerror(
                "Transfer failed",
                message
            )
            self.status.set("Transfer Failed")


        self.root.after(2000, lambda: self.progress.set(0))


    def user_settings(self):

        window = tk.Toplevel(self.root)
        window.title("Settings")
        window.geometry("350x130")
        window.resizable(False, False)

        ttk.Label(
            window,
            text="Set new password"
        ).pack(anchor="w", padx=10, pady=(10, 0))

        security_entry = ttk.Entry(window, width=40)
        security_entry.pack(fill="x", padx=10)

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
        self.progress.set(percent)
        self.root.update_idletasks()