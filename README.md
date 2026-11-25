## Disclaimer ⚠️

This tool is intended **solely for educational and personal use**.  
It is **not affiliated with, endorsed by, or approved by Riot Games Inc.**

⚠️ **Important Notice:**  
Using this application **could potentially conflict** with Riot Games’ Terms of Service, especially because it automates parts of the login process.  
By using this tool, you acknowledge the potential consequences, including **account suspension, bans, or other actions** taken by Riot Games.

The author assumes **no responsibility** for any outcomes resulting from the use of this software.  
**Use at your own risk.**

# Riot AutoLogger 🎮

AutoLogger is a small Windows desktop application that manages multiple Riot Games accounts and signs in to the Riot Client with one click. It types your username and password into the Riot Client login screen for you.

> **v2** is a rewrite of the original app. The original version (v1.0) is still available under **Releases**.

---

## Features ✨

- Save multiple Riot accounts and sign in to any of them with one click
- Add, edit (with Save and Cancel) and delete accounts
- **Passwords are encrypted** with Windows DPAPI, so they are never stored as plain text
- **No image recognition:** works in any Riot Client language and at any window position or size
- Can **start the Riot Client for you** if it isn't open
- Sign-in runs in the background with a status line and a Cancel button
- Safe saving: atomic writes, an automatic backup, and recovery if the accounts file gets damaged
- Imports accounts from the old v1.0 `accounts.json` with one click
- No third-party dependencies

---

## How It Works 🛠️

### Account storage
Accounts are saved in `%APPDATA%\RiotAutoLogger\accounts.json`. Passwords are encrypted with the Windows Data Protection API (DPAPI), tied to your Windows user account. The previous version of the file is kept as `accounts.json.bak`, and a damaged file is set aside instead of overwritten.

### Signing in
1. Finds the Riot Client window (starting the client first if you allow it).
2. Waits until the sign-in screen is showing.
3. Clicks the username box, located relative to the window size, then types the username, presses Tab, types the password and presses Enter.

Characters are sent as Unicode keystrokes, so symbols are typed correctly on any keyboard layout. If the Riot Client loses focus during sign-in, the app stops and does not type the password.

### Files
- `Autologger by Gasson.py`: the window and app entry point
- `riot_client.py`: the sign-in logic
- `winapi.py`: Windows window, mouse and keyboard calls
- `storage.py`, `crypto.py`, `paths.py`: account storage, encryption and file locations

---

## Installation ⚙️

1. Use **Windows** with **Python 3** installed (Tkinter is included with the standard installer).
2. No packages need to be installed.

## Usage ▶️

- Run `python "Autologger by Gasson.py"`, or use the `.exe` from the Releases page.
- To add an account, fill in Account Name, Username and Password, then click **Add Account**.
- Click an account to sign in. Leave the mouse and keyboard alone until it finishes.
- Use **Edit** and **Delete** next to an account. Edits are only saved when you click **Save Changes**.
- Tick or untick **Start the Riot Client if it isn't open** as you prefer.

If you used v1.0, click **Import Accounts...** and choose your old `accounts.json` (it is in the folder you ran v1.0 from). Your accounts are added and encrypted. That old file still contains plain-text passwords, so delete it once you have checked everything works.

### About the .exe
The `.exe` on the Releases page is built from this source with PyInstaller. Unsigned programs like this can trigger Windows SmartScreen or antivirus warnings.

## Important Notes ⚠️

- The Riot Client has to be showing its **sign-in screen**. If you are already signed in, or it is still loading or updating, the app tells you and types nothing.
- Two-factor authentication and the "Stay signed in" checkbox are not handled.
- Encrypted passwords can only be read by the same Windows user on the same PC. Copying `accounts.json` to another computer will not work.
- The click position is based on the current Riot Client layout. A Riot update that changes the login screen could require an update to this app.

## License 📄

This project is licensed under the [MIT License](LICENSE).  
See the [LICENSE](LICENSE) file for details.

## Demo 🎥

Demo of v1.0:

[![Watch the demo](https://img.youtube.com/vi/3mkgYJjaUrM/0.jpg)](https://youtu.be/3mkgYJjaUrM)


## Credits 🙌
Created by gassonexe (Luka Galonjic)
