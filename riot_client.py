"""Sign in to the Riot Client by window position and keyboard input, without image recognition."""

import json
import os
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

USERNAME_BOX = (0.13, 0.30)
# Empty spots on the light left-hand panel. If they are not bright, it is not the sign-in
# screen (still loading, updating, or already signed in).
READY_POINTS = ((0.05, 0.60), (0.20, 0.60))
LIGHT_PANEL_MIN = 225
MIN_SIZE = (400, 300)

LAUNCH_ARGUMENTS = ()


@dataclass(frozen=True)
class Timing:
    launch_timeout: float = 60.0
    ready_after_launch: float = 45.0
    ready_when_running: float = 6.0
    poll: float = 0.25
    settle: float = 0.5
    after_click: float = 0.2
    between_fields: float = 0.15


class Outcome(Enum):
    SUBMITTED = "submitted"
    CANCELLED = "cancelled"
    CLIENT_NOT_RUNNING = "client_not_running"
    CLIENT_NOT_INSTALLED = "client_not_installed"
    LAUNCH_FAILED = "launch_failed"
    WINDOW_TIMEOUT = "window_timeout"
    FOCUS_FAILED = "focus_failed"
    NOT_LOGIN_SCREEN = "not_login_screen"
    FOCUS_LOST = "focus_lost"


@dataclass(frozen=True)
class LoginResult:
    outcome: Outcome
    message: str

    @property
    def ok(self):
        return self.outcome is Outcome.SUBMITTED


class _Abort(Exception):
    def __init__(self, outcome, message):
        super().__init__(message)
        self.result = LoginResult(outcome, message)


def point_in_rect(rect, fraction_x, fraction_y):
    """Screen point at the given fraction of rect = (left, top, right, bottom)."""
    left, top, right, bottom = rect
    return (left + round((right - left) * fraction_x), top + round((bottom - top) * fraction_y))


def find_client_executable(environ=None):
    environ = os.environ if environ is None else environ
    program_data = environ.get("PROGRAMDATA", r"C:\ProgramData")
    listing = Path(program_data) / "Riot Games" / "RiotClientInstalls.json"
    try:
        with open(listing, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        for key in ("rc_default", "rc_live", "rc_beta"):
            value = data.get(key) if isinstance(data, dict) else None
            if isinstance(value, str) and Path(value).is_file():
                return Path(value)
    except (OSError, ValueError):
        pass

    drive = environ.get("SystemDrive", "C:")
    for candidate in (
        Path(drive + "\\") / "Riot Games" / "Riot Client" / "RiotClientServices.exe",
        Path(environ.get("PROGRAMFILES", r"C:\Program Files")) / "Riot Games" / "Riot Client" / "RiotClientServices.exe",
    ):
        if candidate.is_file():
            return candidate
    return None


class RiotLogin:
    def __init__(self, api, timing=None, find_executable=find_client_executable,
                 sleep=time.sleep, clock=time.monotonic):
        self.api = api
        self.timing = timing or Timing()
        self._find_executable = find_executable
        self._sleep = sleep
        self._clock = clock


    def login(self, username, password, launch=True, status=None, cancel=None):
        """Run the whole sign-in. Never raises for expected problems: returns a LoginResult.

        status: optional function(str) called with progress messages.
        cancel: optional threading.Event; set it to stop.
        """
        say = status or (lambda message: None)
        try:
            with self.api.dpi_aware():
                return self._login(username, password, launch, say, cancel)
        except _Abort as stop:
            return stop.result
        except OSError as error:
            return LoginResult(Outcome.FOCUS_FAILED, f"Windows refused the request: {error}")


    def _login(self, username, password, launch, say, cancel):
        timing = self.timing

        say("Looking for the Riot Client...")
        hwnd = self.api.find_window()
        launched = False

        if hwnd is None:
            if not launch:
                raise _Abort(Outcome.CLIENT_NOT_RUNNING,
                             "The Riot Client is not open. Open it, or turn on starting it automatically.")
            executable = self._find_executable()
            if executable is None:
                raise _Abort(Outcome.CLIENT_NOT_INSTALLED,
                             "Could not find the Riot Client on this PC. Is it installed?")
            say("Starting the Riot Client...")
            try:
                self.api.launch(executable, LAUNCH_ARGUMENTS)
            except OSError as error:
                raise _Abort(Outcome.LAUNCH_FAILED, f"Could not start the Riot Client: {error}")
            launched = True
            hwnd = self._wait(self.api.find_window, timing.launch_timeout, cancel)
            if hwnd is None:
                raise _Abort(Outcome.WINDOW_TIMEOUT,
                             "The Riot Client did not open in time. Try again, or open it yourself first.")

        say("Bringing the Riot Client to the front...")
        hwnd = self._focus(hwnd)

        say("Waiting for the sign-in screen...")
        hwnd = self._wait_for_login_screen(
            hwnd, timing.ready_after_launch if launched else timing.ready_when_running, cancel)
        self._sleep(timing.settle)

        say("Signing in...")
        self._type_credentials(hwnd, username, password, cancel)
        return LoginResult(Outcome.SUBMITTED,
                           "Sign-in submitted. Check the Riot Client for the result.")

    def _focus(self, hwnd):
        if not self.api.set_foreground(hwnd):
            raise _Abort(Outcome.FOCUS_FAILED,
                         "Windows would not bring the Riot Client to the front. "
                         "Click on the Riot Client window once and try again.")
        return hwnd

    def _wait(self, check, timeout, cancel):
        deadline = self._clock() + timeout
        while True:
            self._check_cancel(cancel)
            value = check()
            if value:
                return value
            if self._clock() >= deadline:
                return None
            self._sleep(self.timing.poll)

    def _wait_for_login_screen(self, hwnd, timeout, cancel):
        current = {"hwnd": hwnd}

        def ready():
            # The client may replace its window while starting up, so look again each time.
            found = self.api.find_window()
            if found is None:
                return False
            if found != current["hwnd"] or self.api.foreground_window() != found:
                if not self.api.set_foreground(found):
                    return False
                current["hwnd"] = found
            return self._looks_like_login_screen(found)

        if not self._wait(ready, timeout, cancel):
            raise _Abort(Outcome.NOT_LOGIN_SCREEN,
                         "The Riot Client is not showing the sign-in screen. It may still be "
                         "loading or updating, or you may already be signed in.")
        return current["hwnd"]

    def _looks_like_login_screen(self, hwnd):
        rect = self.api.client_rect(hwnd)
        if rect is None or rect[2] - rect[0] < MIN_SIZE[0] or rect[3] - rect[1] < MIN_SIZE[1]:
            return False
        for fraction_x, fraction_y in READY_POINTS:
            colour = self.api.pixel(*point_in_rect(rect, fraction_x, fraction_y))
            if colour is None or min(colour) < LIGHT_PANEL_MIN:
                return False
        return True

    def _type_credentials(self, hwnd, username, password, cancel):
        timing = self.timing
        rect = self.api.client_rect(hwnd)
        if rect is None:
            raise _Abort(Outcome.WINDOW_TIMEOUT, "The Riot Client window disappeared.")
        saved_cursor = self.api.cursor_pos()
        try:
            self._require_front(hwnd, cancel)
            self.api.click(*point_in_rect(rect, *USERNAME_BOX))
            self._sleep(timing.after_click)

            self._require_front(hwnd, cancel)
            self.api.clear_field()
            self.api.type_text(username)
            self.api.press_tab()
            self._sleep(timing.between_fields)

            # Never type the password unless the Riot Client still has the keyboard.
            self._require_front(hwnd, cancel)
            self.api.clear_field()
            self.api.type_text(password)

            self._require_front(hwnd, cancel)
            self.api.press_enter()
        finally:
            try:
                self.api.move_cursor(*saved_cursor)
            except OSError:
                pass

    def _require_front(self, hwnd, cancel):
        self._check_cancel(cancel)
        if self.api.foreground_window() == hwnd:
            return
        if self.api.set_foreground(hwnd):
            return
        raise _Abort(Outcome.FOCUS_LOST,
                     "The Riot Client lost focus, so nothing more was typed. Try again "
                     "and leave the keyboard and mouse alone until it finishes.")

    @staticmethod
    def _check_cancel(cancel):
        if cancel is not None and cancel.is_set():
            raise _Abort(Outcome.CANCELLED, "Cancelled.")
