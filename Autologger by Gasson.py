import tkinter as tk
import pyautogui
import pygetwindow as gw
import time
import json
import os
import sys

ACCOUNTS_FILE = "accounts.json"  # JSON file to store saved accounts

def resource_path(relative_path):
    # Get absolute path to resource, works for dev and PyInstaller
    try:
        base_path = sys._MEIPASS  # PyInstaller temp folder when frozen
    except Exception:
        base_path = os.path.abspath(".")  # Normal script execution path
    return os.path.join(base_path, relative_path)

# Load saved accounts from JSON file if it exists
if os.path.exists(ACCOUNTS_FILE):
    with open(ACCOUNTS_FILE, "r") as f:
        accounts = json.load(f)
else:
    accounts = {}

def save_accounts():
    # Save the accounts dictionary to JSON file with indentation
    with open(ACCOUNTS_FILE, "w") as f:
        json.dump(accounts, f, indent=4)

def inject_credentials(username, password):
    # Automate Riot Client login by injecting username and password using pyautogui
    try:
        print(f"Injecting for user: {username}")

        # Search for the Riot Client window by title
        for window in gw.getWindowsWithTitle("Riot Client"):
            print("Found Riot Client window.")
            window.minimize()    # Minimize to force window refresh
            time.sleep(0.1)
            window.restore()     # Restore it back
            window.activate()    # Bring it to foreground
            break
        else:
            print("Riot Client window not found.")
            return

        time.sleep(0.1)

        # Get window position to calculate relative click positions
        riot_x, riot_y = window.left, window.top

        # Click inside the window to ensure focus
        pyautogui.click(riot_x + 50, riot_y + 50)
        time.sleep(0.1)

        # Locate username input field on screen via image matching
        username_field = pyautogui.locateCenterOnScreen(resource_path("assets/username_field.png"), confidence=0.55)
        if username_field:
            pyautogui.click(username_field)
            time.sleep(0.3)
            pyautogui.write(username, interval=0.01)  # Type username slowly
        else:
            print("Username field not found.")
            return

        # Locate password input field on screen
        password_field = pyautogui.locateCenterOnScreen(resource_path("assets/password_field.png"), confidence=0.55)
        if password_field:
            pyautogui.click(password_field)
            time.sleep(0.3)
            pyautogui.write(password, interval=0.01)  # Type password slowly
        else:
            print("Password field not found.")
            return

        # Locate and click the login button
        login_button = pyautogui.locateCenterOnScreen(resource_path("assets/login_button.png"), confidence=0.55)
        if login_button:
            time.sleep(0.3)
            pyautogui.click(login_button)
            print("Login sequence complete.")
        else:
            print("Login button not found.")

    except Exception as e:
        import traceback
        print("Error during injection:")
        traceback.print_exc()

# Create the main Tkinter window
window = tk.Tk()
window.title("AutoLogger by Gasson")

# Set custom window icon (using PNG for taskbar/window icon)
icon_img = tk.PhotoImage(file=resource_path("assets/youricon.png"))
window.iconphoto(True, icon_img)

# Define colors used in the UI
bg_color = "#2D003E"       # Background color
button_color = "#B266FF"   # Button color
text_color = "#FFFFFF"     # Text color

# Apply background color to main window
window.configure(bg=bg_color)

# Set fixed window size and disable resizing/maximize/fullscreen
window.geometry("800x600")
window.resizable(False, False)
window.minsize(800, 600)
window.maxsize(800, 600)

# Center the window on the user's screen
window.update_idletasks()  # Update window info before geometry calculations
screen_width = window.winfo_screenwidth()
screen_height = window.winfo_screenheight()
size_width = 800
size_height = 600
x = (screen_width // 2) - (size_width // 2)
y = (screen_height // 2) - (size_height // 2)
window.geometry(f"{size_width}x{size_height}+{x}+{y}")

# Add a header label prompting user action
tk.Label(
    window,
    text="Click an account to log in:",
    bg=bg_color,
    fg=text_color,
    font=("Helvetica", 14, "bold")
).pack(pady=10)

# Container frame to hold scrollable accounts list
container = tk.Frame(window, bg=bg_color)
container.pack(pady=10, fill="both", expand=True)

# Canvas widget used to enable scrolling of accounts
canvas = tk.Canvas(container, bg=bg_color, highlightthickness=0)
scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)

# Frame inside the canvas that will contain the account buttons
scrollable_frame = tk.Frame(canvas, bg=bg_color)

# Create window inside canvas for scrollable_frame, anchored top-left
scrollable_frame_id = canvas.create_window((0,0), window=scrollable_frame, anchor="nw")

def update_scroll():
    # Update the scroll region and handle scrollbar visibility and horizontal centering

    canvas.configure(scrollregion=canvas.bbox("all"))  # Set scrollable area

    scroll_region = canvas.bbox("all")
    if scroll_region:
        _, _, _, content_height = scroll_region
        view_height = canvas.winfo_height()

        # Show scrollbar only if content is taller than view height
        if content_height > view_height:
            scrollbar.pack(side="right", fill="y")
            canvas.configure(yscrollcommand=scrollbar.set)

            # Bind mouse wheel for scrolling
            canvas.bind_all("<MouseWheel>", on_mousewheel)
            canvas.bind_all("<Button-4>", on_mousewheel)  # Linux scroll up
            canvas.bind_all("<Button-5>", on_mousewheel)  # Linux scroll down
        else:
            # Hide scrollbar and unbind mouse wheel if not needed
            scrollbar.pack_forget()
            canvas.configure(yscrollcommand=None)
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")
    else:
        # No content, hide scrollbar and unbind
        scrollbar.pack_forget()
        canvas.configure(yscrollcommand=None)
        canvas.unbind_all("<MouseWheel>")
        canvas.unbind_all("<Button-4>")
        canvas.unbind_all("<Button-5>")

    # Horizontally center the scrollable_frame inside the canvas
    canvas_width = canvas.winfo_width()
    frame_width = scrollable_frame.winfo_reqwidth()
    x_offset = max((canvas_width - frame_width) // 2, 0)
    canvas.coords(scrollable_frame_id, x_offset, 0)

# Update scroll region and scrollbar visibility whenever scrollable_frame resizes
scrollable_frame.bind("<Configure>", lambda e: update_scroll())

canvas.pack(side="left", fill="both", expand=True)

account_frames = {}  # Store references to account frames for easy access

def add_account_button(name, creds):
    # Add a new account button with Edit and Delete options inside the scrollable frame

    # Prevent duplicate buttons for the same account
    if name in account_frames:
        return

    # Outer frame to hold account button and action buttons horizontally
    outer_frame = tk.Frame(scrollable_frame, bg=bg_color)
    outer_frame.pack(pady=3, fill="x")

    # Main account button to trigger login injection
    btn = tk.Button(
        outer_frame,
        text=name,
        width=30,
        bg=button_color,
        fg="black",
        activebackground="#A64DFF",
        font=("Helvetica", 12),
        command=lambda u=creds["username"], p=creds["password"]: inject_credentials(u, p)
    )
    btn.pack(side="left", padx=(0,10))

    def start_edit_account():
        # Populate form entries with account data to allow editing
        label_entry.delete(0, tk.END)
        label_entry.insert(0, name)
        username_entry.delete(0, tk.END)
        username_entry.insert(0, creds["username"])
        password_entry.delete(0, tk.END)
        password_entry.insert(0, creds["password"])

        # Remove old account before editing so it can be replaced on save
        del accounts[name]
        outer_frame.destroy()
        del account_frames[name]
        save_accounts()
        update_scroll()

    # Button to edit the selected account
    edit_btn = tk.Button(outer_frame, text="Edit", width=6, command=start_edit_account)
    edit_btn.pack(side="left", padx=(0,5))

    def delete_account():
        # Delete account from data and UI
        if name in accounts:
            del accounts[name]
            outer_frame.destroy()
            del account_frames[name]
            save_accounts()
            print(f"Deleted account: {name}")
            update_scroll()

    # Button to delete the selected account
    del_btn = tk.Button(outer_frame, text="Delete", width=6, command=delete_account)
    del_btn.pack(side="left")

    # Store reference to outer frame for this account
    account_frames[name] = outer_frame
    update_scroll()

def add_account():
    # Read user input from form and add new account to dictionary and UI
    name = label_entry.get().strip()
    username = username_entry.get().strip()
    password = password_entry.get().strip()

    # Validate all fields are filled
    if not name or not username or not password:
        print("Please fill in all fields")
        return

    # Check for duplicate account names
    if name in accounts:
        print("Account name already exists!")
        return

    # Save new account and add button
    accounts[name] = {"username": username, "password": password}
    add_account_button(name, accounts[name])
    save_accounts()

    # Clear form entries after adding
    label_entry.delete(0, tk.END)
    username_entry.delete(0, tk.END)
    password_entry.delete(0, tk.END)

    print(f"Account '{name}' added successfully.")
    update_scroll()

# Add buttons for all previously saved accounts on startup
for name, creds in accounts.items():
    add_account_button(name, creds)

# Label for the add new account section
tk.Label(window, text="Add New Account", bg=bg_color, fg=text_color, font=("Helvetica", 12, "bold")).pack(pady=(20,10))

# Container for the add account form inputs
form_container = tk.Frame(window, bg=bg_color)
form_container.pack(pady=10)

# Labels for form fields
tk.Label(form_container, text="Account Name", bg=bg_color, fg=text_color, font=("Helvetica", 10)).grid(row=0, column=0, padx=20, pady=(0,5))
tk.Label(form_container, text="Username", bg=bg_color, fg=text_color, font=("Helvetica", 10)).grid(row=0, column=1, padx=20, pady=(0,5))
tk.Label(form_container, text="Password", bg=bg_color, fg=text_color, font=("Helvetica", 10)).grid(row=0, column=2, padx=20, pady=(0,5))

# Entry widgets for form fields
label_entry = tk.Entry(form_container, width=18, font=("Helvetica", 10))
username_entry = tk.Entry(form_container, width=18, font=("Helvetica", 10))
password_entry = tk.Entry(form_container, width=18, show="*", font=("Helvetica", 10))

label_entry.grid(row=1, column=0, padx=20)
username_entry.grid(row=1, column=1, padx=20)
password_entry.grid(row=1, column=2, padx=20)

# Button to add new account when clicked
tk.Button(
    window,
    text="Add Account",
    bg=button_color,
    fg="black",
    activebackground="#A64DFF",
    font=("Helvetica", 11, "bold"),
    command=add_account
).pack(pady=(10,15))

def on_mousewheel(event):
    # Scroll canvas vertically based on mouse wheel delta
    canvas.yview_scroll(int(-1*(event.delta/120)), "units")

# Bind mouse wheel event for scrolling the accounts list
canvas.bind_all("<MouseWheel>", on_mousewheel)

# Bind window resize/move event to update scroll region and positions to avoid disappearing accounts
window.bind("<Configure>", lambda e: update_scroll())

# Start Tkinter event loop
window.mainloop()
