## Disclaimer ⚠️

This tool is intended **solely for educational and personal use**.  
It is **not affiliated with, endorsed by, or approved by Riot Games Inc.**

⚠️ **Important Notice:**  
Using this application **may violate Riot Games’ Terms of Service**, particularly regarding automation of the login process.  
By using this tool, you acknowledge the potential consequences, including **account suspension, bans, or other actions** taken by Riot Games.

The author assumes **no responsibility** for any outcomes resulting from the use of this software.  
**Use at your own risk.**

# Riot AutoLogger 🎮

AutoLogger is a simple Python desktop application that automates logging into Riot Games Client accounts. It uses a graphical interface to manage multiple saved accounts and automates the login process by interacting with the Riot Client window using GUI automation.

---

## Features ✨

- Save multiple Riot Client accounts with usernames and passwords  
- Manage accounts via a simple UI: add, edit, and delete accounts  
- Automatically locate Riot Client window and inject credentials  
- Scrollable and centered list of saved accounts  
- Secure password entry masked in the UI  
- Portable GUI with a fixed window size and simple custom theming  

---

## How It Works 🛠️

### Account Management  
Accounts are saved locally in a `accounts.json` file in the same directory. Users can add new accounts or modify existing ones through the UI.

### GUI Interface  
Built with Tkinter, the interface displays a scrollable list of saved accounts. Clicking an account will trigger the login process.

### Automated Login  
Using `pyautogui` and `pygetwindow`, the program searches for the Riot Client window, activates it, and performs automated mouse clicks and keyboard input to fill in the username and password fields and then click the login button. It relies on image recognition to find the exact input fields and buttons.

### File Structure  
- `accounts.json`: Stores the saved accounts.  
- `assets/`: Contains PNG images used for image recognition (e.g., username field, password field, login button, and icon).  

---

## Installation ⚙️

1. Make sure you have **Python 3** installed.
2. Install the required Python libraries by running:
   ```bash
   pip install pyautogui pygetwindow
## Usage ▶️

- Run the Python script.
 
- The application window will open.

- To add a new account, fill in the Account Name, Username, and Password fields, then click Add Account.

- Click on any account button to automatically log in to that account through the Riot Client.

- Use the Edit or Delete buttons next to each account to modify or remove them.

- All changes are saved automatically in the accounts.json file.

## Important Notes ⚠️
The app uses image recognition to locate input fields on the Riot Client login window, so only the client in English is supported at the moment.

Make sure the Riot Client is open.

For best results, use the app at a consistent screen resolution and UI scale.

Passwords are stored locally in plain JSON format.

## License 📄

This project is licensed under the [MIT License](LICENSE).  
See the [LICENSE](LICENSE) file for details.

## Credits 🙌
Created by gassonexe (Luka Galonjic)
