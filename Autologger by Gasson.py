import queue
import sys
import threading
import tkinter as tk
from tkinter import messagebox

from crypto import CryptoError, DpapiCrypto
from paths import accounts_file, legacy_accounts_files, resource_path
from riot_client import Outcome, RiotLogin
from storage import AccountStore, StorageError, ValidationError
from winapi import WinApi

APP_TITLE = "AutoLogger by Gasson"
APP_VERSION = "2.0"


window = tk.Tk()
window.title(f"{APP_TITLE} v{APP_VERSION}")

icon_img = tk.PhotoImage(file=resource_path("assets/youricon.png"))
window.iconphoto(True, icon_img)

bg_color = "#2D003E"
button_color = "#B266FF"
text_color = "#FFFFFF"

window.configure(bg=bg_color)

window.geometry("800x600")
window.resizable(False, False)
window.minsize(800, 600)
window.maxsize(800, 600)

window.update_idletasks()
screen_width = window.winfo_screenwidth()
screen_height = window.winfo_screenheight()
size_width = 800
size_height = 600
x = (screen_width // 2) - (size_width // 2)
y = (screen_height // 2) - (size_height // 2)
window.geometry(f"{size_width}x{size_height}+{x}+{y}")

try:
    store = AccountStore(accounts_file(), DpapiCrypto(), legacy_paths=legacy_accounts_files())
    engine = RiotLogin(WinApi())
except (StorageError, CryptoError, OSError) as error:
    messagebox.showerror(APP_TITLE, f"Could not load your accounts:\n\n{error}")
    window.destroy()
    sys.exit(1)

edit_state = {"name": None}

login_state = {"running": False, "cancel": None}
ui_events = queue.Queue()

tk.Label(
    window,
    text="Click an account to log in:",
    bg=bg_color,
    fg=text_color,
    font=("Helvetica", 14, "bold")
).pack(pady=10)

# Packed before the list so these keep their space at the bottom of the window
status_bar = tk.Frame(window, bg=bg_color)
status_bar.pack(side="bottom", fill="x", padx=15, pady=(0,8))
status_var = tk.StringVar(value="")
tk.Label(status_bar, textvariable=status_var, bg=bg_color, fg=text_color,
         font=("Helvetica", 10), anchor="w", justify="left", wraplength=600).pack(side="left", fill="x", expand=True)
cancel_btn = tk.Button(status_bar, text="Cancel", command=lambda: cancel_login())  # defined further down

options_row = tk.Frame(window, bg=bg_color)
options_row.pack(side="bottom", fill="x", padx=15)
launch_var = tk.BooleanVar(value=True)
tk.Checkbutton(
    options_row, text="Start the Riot Client if it isn't open", variable=launch_var,
    bg=bg_color, fg=text_color, activebackground=bg_color, activeforeground=text_color,
    selectcolor="#4B0A66", font=("Helvetica", 10)
).pack(side="left")

container = tk.Frame(window, bg=bg_color)
container.pack(pady=10, fill="both", expand=True)

canvas = tk.Canvas(container, bg=bg_color, highlightthickness=0)
scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)

scrollable_frame = tk.Frame(canvas, bg=bg_color)

scrollable_frame_id = canvas.create_window((0,0), window=scrollable_frame, anchor="nw")


def on_mousewheel(event):
    canvas.yview_scroll(int(-1*(event.delta/120)), "units")


def update_scroll():
    canvas.configure(scrollregion=canvas.bbox("all"))

    scroll_region = canvas.bbox("all")
    if scroll_region:
        _, _, _, content_height = scroll_region
        view_height = canvas.winfo_height()

        if content_height > view_height:
            scrollbar.pack(side="right", fill="y")
            canvas.configure(yscrollcommand=scrollbar.set)

            canvas.bind_all("<MouseWheel>", on_mousewheel)
            canvas.bind_all("<Button-4>", on_mousewheel)
            canvas.bind_all("<Button-5>", on_mousewheel)
        else:
            scrollbar.pack_forget()
            canvas.configure(yscrollcommand=None)
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")
    else:
        scrollbar.pack_forget()
        canvas.configure(yscrollcommand=None)
        canvas.unbind_all("<MouseWheel>")
        canvas.unbind_all("<Button-4>")
        canvas.unbind_all("<Button-5>")

    canvas_width = canvas.winfo_width()
    frame_width = scrollable_frame.winfo_reqwidth()
    x_offset = max((canvas_width - frame_width) // 2, 0)
    canvas.coords(scrollable_frame_id, x_offset, 0)

scrollable_frame.bind("<Configure>", lambda e: update_scroll())

canvas.pack(side="left", fill="both", expand=True)


def show_error(message):
    messagebox.showerror(APP_TITLE, message)


def set_status(text):
    status_var.set(text)


def login(name):
    if login_state["running"]:
        set_status("A sign-in is already running.")
        return
    try:
        account = store.get(name)
    except (ValidationError, CryptoError, StorageError) as error:
        show_error(f"Could not read the saved login for '{name}':\n\n{error}\n\n"
                   "Edit the account and enter its password again.")
        return

    username, password = account.username, account.password
    launch = launch_var.get()          # read here: Tk must only be used from the main thread
    cancel = threading.Event()
    login_state.update(running=True, cancel=cancel)
    cancel_btn.pack(side="right")
    set_status(f"Signing in to '{name}'...")

    def work():
        try:
            result = engine.login(username, password, launch=launch, cancel=cancel,
                                  status=lambda message: ui_events.put(("status", message)))
            ui_events.put(("done", result))
        except Exception as error:
            ui_events.put(("error", f"Unexpected error: {type(error).__name__}: {error}"))

    threading.Thread(target=work, daemon=True).start()


def cancel_login():
    cancel = login_state["cancel"]
    if cancel is not None:
        cancel.set()
        set_status("Cancelling...")


def finish_login(message, show_dialog):
    login_state.update(running=False, cancel=None)
    cancel_btn.pack_forget()
    set_status(message)
    if show_dialog:
        messagebox.showwarning(APP_TITLE, message)


def poll_events():
    try:
        while True:
            kind, payload = ui_events.get_nowait()
            if kind == "status":
                if login_state["running"]:
                    set_status(payload)
            elif kind == "done":
                finish_login(payload.message,
                             show_dialog=not payload.ok and payload.outcome is not Outcome.CANCELLED)
            else:
                finish_login(payload, show_dialog=True)
    except queue.Empty:
        pass
    window.after(100, poll_events)


def clear_form():
    label_entry.delete(0, tk.END)
    username_entry.delete(0, tk.END)
    password_entry.delete(0, tk.END)


def end_edit():
    edit_state["name"] = None
    clear_form()
    submit_btn.config(text="Add Account")
    cancel_btn.pack_forget()
    form_title.config(text="Add New Account")


def begin_edit(name):
    try:
        username = store.username_of(name)
    except ValidationError as error:
        show_error(str(error))
        refresh_account_list()
        return

    try:
        password = store.get(name).password
    except (CryptoError, StorageError) as error:
        password = ""
        messagebox.showwarning(
            APP_TITLE,
            f"The saved password for '{name}' could not be read:\n\n{error}\n\n"
            "Please enter the password again."
        )

    edit_state["name"] = name
    clear_form()
    label_entry.insert(0, name)
    username_entry.insert(0, username)
    password_entry.insert(0, password)
    submit_btn.config(text="Save Changes")
    cancel_btn.pack(side="left", padx=5)
    form_title.config(text=f"Editing: {name}")


def delete_account(name):
    if not messagebox.askyesno(APP_TITLE, f"Delete the account '{name}'?"):
        return
    try:
        store.delete(name)
    except (ValidationError, StorageError) as error:
        show_error(str(error))
    if edit_state["name"] == name:
        end_edit()
    refresh_account_list()


def add_account_button(name):
    outer_frame = tk.Frame(scrollable_frame, bg=bg_color)
    outer_frame.pack(pady=3, fill="x")

    tk.Button(
        outer_frame,
        text=name,
        width=30,
        bg=button_color,
        fg="black",
        activebackground="#A64DFF",
        font=("Helvetica", 12),
        command=lambda n=name: login(n)
    ).pack(side="left", padx=(0,10))

    tk.Button(outer_frame, text="Edit", width=6, command=lambda n=name: begin_edit(n)).pack(side="left", padx=(0,5))
    tk.Button(outer_frame, text="Delete", width=6, command=lambda n=name: delete_account(n)).pack(side="left")


def refresh_account_list():
    for child in scrollable_frame.winfo_children():
        child.destroy()
    for name in store.names():
        add_account_button(name)
    update_scroll()


def submit_form():
    name = label_entry.get()
    username = username_entry.get()
    password = password_entry.get()  # kept exactly as typed

    try:
        if edit_state["name"] is None:
            store.add(name, username, password)
        else:
            store.update(edit_state["name"], name, username, password)
    except ValidationError as error:
        messagebox.showwarning(APP_TITLE, str(error))
        return
    except (StorageError, CryptoError) as error:
        show_error(str(error))
        return

    end_edit()
    refresh_account_list()


form_title = tk.Label(window, text="Add New Account", bg=bg_color, fg=text_color, font=("Helvetica", 12, "bold"))
form_title.pack(pady=(20,10))

form_container = tk.Frame(window, bg=bg_color)
form_container.pack(pady=10)

tk.Label(form_container, text="Account Name", bg=bg_color, fg=text_color, font=("Helvetica", 10)).grid(row=0, column=0, padx=20, pady=(0,5))
tk.Label(form_container, text="Username", bg=bg_color, fg=text_color, font=("Helvetica", 10)).grid(row=0, column=1, padx=20, pady=(0,5))
tk.Label(form_container, text="Password", bg=bg_color, fg=text_color, font=("Helvetica", 10)).grid(row=0, column=2, padx=20, pady=(0,5))

label_entry = tk.Entry(form_container, width=18, font=("Helvetica", 10))
username_entry = tk.Entry(form_container, width=18, font=("Helvetica", 10))
password_entry = tk.Entry(form_container, width=18, show="*", font=("Helvetica", 10))

label_entry.grid(row=1, column=0, padx=20)
username_entry.grid(row=1, column=1, padx=20)
password_entry.grid(row=1, column=2, padx=20)

button_row = tk.Frame(window, bg=bg_color)
button_row.pack(pady=(10,15))

submit_btn = tk.Button(
    button_row,
    text="Add Account",
    bg=button_color,
    fg="black",
    activebackground="#A64DFF",
    font=("Helvetica", 11, "bold"),
    command=submit_form
)
submit_btn.pack(side="left", padx=5)

cancel_btn = tk.Button(
    button_row,
    text="Cancel",
    font=("Helvetica", 11),
    command=end_edit
)

refresh_account_list()

window.after(100, poll_events)

canvas.bind_all("<MouseWheel>", on_mousewheel)

window.bind("<Configure>", lambda e: update_scroll())

for notice in store.notices:
    messagebox.showinfo(APP_TITLE, notice)

window.mainloop()
