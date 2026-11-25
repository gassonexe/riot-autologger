"""Encrypted account storage with atomic saves, a backup, and import of the old plaintext format.

File format: {"version": 2, "accounts": {"<name>": {"username": "...", "password": "<encrypted>"}}}
"""

import json
import os
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

SCHEMA_VERSION = 2


class StorageError(Exception):
    pass


class ValidationError(ValueError):
    pass


@dataclass(frozen=True)
class Account:
    name: str
    username: str
    password: str = field(repr=False)  # keep secrets out of logs and tracebacks


class AccountStore:

    def __init__(self, path, crypto, legacy_paths=()):
        self.path = Path(path)
        self.backup_path = self.path.with_name(self.path.name + ".bak")
        self._crypto = crypto
        self._accounts = {}   # name -> {"username": str, "password": <encrypted token>}
        self.notices = []
        self._load(list(legacy_paths))


    def names(self):
        return list(self._accounts)

    def __len__(self):
        return len(self._accounts)

    def __contains__(self, name):
        return name in self._accounts

    def username_of(self, name):
        return self._record(name)["username"]

    def get(self, name):
        record = self._record(name)
        return Account(name, record["username"], self._crypto.decrypt(record["password"]))


    def add(self, name, username, password):
        name, username = self._clean(name, username, password)
        if name in self._accounts:
            raise ValidationError(f"An account named '{name}' already exists.")
        updated = dict(self._accounts)
        updated[name] = {"username": username, "password": self._crypto.encrypt(password)}
        self._commit(updated)

    def update(self, old_name, new_name, username, password):
        self._record(old_name)
        new_name, username = self._clean(new_name, username, password)
        if new_name != old_name and new_name in self._accounts:
            raise ValidationError(f"An account named '{new_name}' already exists.")
        record = {"username": username, "password": self._crypto.encrypt(password)}
        updated = {}
        for name, existing in self._accounts.items():
            if name == old_name:
                updated[new_name] = record
            else:
                updated[name] = existing
        self._commit(updated)

    def delete(self, name):
        self._record(name)
        updated = {k: v for k, v in self._accounts.items() if k != name}
        self._commit(updated)


    def _record(self, name):
        try:
            return self._accounts[name]
        except KeyError:
            raise ValidationError(f"Account '{name}' no longer exists.") from None

    @staticmethod
    def _clean(name, username, password):
        # Name and username are trimmed; the password is kept exactly as typed.
        name, username = name.strip(), username.strip()
        if not name or not username or not password:
            raise ValidationError("Please fill in the account name, username and password.")
        return name, username


    def _load(self, legacy_paths):
        if self.path.exists():
            parsed = self._try_read(self.path)
            if parsed is not None:
                self._adopt(*parsed)
                return
            quarantined = self._quarantine(self.path)
            if self._restore_from_backup(
                f"Your accounts file was damaged and has been set aside as {quarantined.name}."
            ):
                return
            self.notices.append(
                "Your accounts file was damaged and no backup could be read. "
                f"The damaged file was kept as {quarantined} in case it can be recovered."
            )
            return

        if self.backup_path.exists() and self._restore_from_backup(
            "The accounts file was missing."
        ):
            return

        self._migrate_legacy(legacy_paths)

    def _restore_from_backup(self, reason):
        if not self.backup_path.exists():
            return False
        parsed = self._try_read(self.backup_path)
        if parsed is None:
            return False
        self._adopt(*parsed)
        self.notices.append(f"{reason} Restored {len(self._accounts)} account(s) from the backup.")
        return True

    def _migrate_legacy(self, legacy_paths):
        for old in legacy_paths:
            old = Path(old)
            if not old.is_file() or old.resolve() == self.path.resolve():
                continue
            parsed = self._try_read(old)
            if parsed is None:
                self.notices.append(f"Could not read the old accounts file at {old}; skipped it.")
                continue
            accounts, is_legacy = parsed
            if not accounts:
                continue
            expected = self._decrypted_copy(accounts, is_legacy)
            self._adopt(accounts, is_legacy)
            self._verify(expected)
            self.notices.append(
                f"{len(accounts)} account(s) were imported from {old} and their passwords are "
                f"now encrypted.\n\nThe old file still contains the passwords in plain text. "
                "Once you've checked that your accounts work, delete it."
            )
            return

    def _decrypted_copy(self, accounts, is_legacy):
        copy = {}
        for name, record in accounts.items():
            password = record["password"] if is_legacy else self._crypto.decrypt(record["password"])
            copy[name] = (record["username"], password)
        return copy

    def _verify(self, expected):
        parsed = self._try_read(self.path)
        problem = None
        if parsed is None or parsed[1]:
            problem = "the saved file could not be read back"
        else:
            written = parsed[0]
            if list(written) != list(expected):
                problem = "the saved account list does not match"
            else:
                for name, (username, password) in expected.items():
                    record = written[name]
                    if record["username"] != username or self._crypto.decrypt(record["password"]) != password:
                        problem = f"account '{name}' did not round-trip"
                        break
        if problem:
            try:
                self.path.unlink()
            except OSError:
                pass
            self._accounts = {}
            raise StorageError(
                f"Importing your accounts failed ({problem}). Your original file was not changed."
            )

    def _adopt(self, accounts, is_legacy):
        if is_legacy:
            accounts = {
                name: {"username": rec["username"], "password": self._crypto.encrypt(rec["password"])}
                for name, rec in accounts.items()
            }
        self._accounts = accounts
        if is_legacy or not self.path.exists():
            self._save()

    @staticmethod
    def _try_read(path):
        """Return (accounts, is_legacy) or None if the file is unreadable or not valid."""
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if not isinstance(data, dict):
                return None
            if data.get("version") == SCHEMA_VERSION and isinstance(data.get("accounts"), dict):
                accounts, is_legacy = data["accounts"], False
            else:
                accounts, is_legacy = data, True
            for record in accounts.values():
                if not (
                    isinstance(record, dict)
                    and isinstance(record.get("username"), str)
                    and isinstance(record.get("password"), str)
                ):
                    return None
            return accounts, is_legacy
        except (OSError, ValueError):
            return None

    @staticmethod
    def _quarantine(path):
        stamp = time.strftime("%Y%m%d-%H%M%S")
        target = path.with_name(f"{path.stem}.corrupt-{stamp}{path.suffix}")
        try:
            os.replace(path, target)
        except OSError as exc:
            raise StorageError(f"Could not set aside the damaged accounts file: {exc}") from exc
        return target


    def _commit(self, new_accounts):
        """Save new_accounts; memory only changes if the write succeeded."""
        previous = self._accounts
        self._accounts = new_accounts
        try:
            self._save()
        except BaseException:
            self._accounts = previous
            raise

    def _save(self):
        payload = {"version": SCHEMA_VERSION, "accounts": self._accounts}
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            # Keep the previous good version as a one-step backup.
            # (Never back up an old plaintext-format file: that would copy the passwords.)
            existing = self._try_read(self.path) if self.path.exists() else None
            if existing is not None and not existing[1]:
                shutil.copy2(self.path, self.backup_path)

            fd, temp_name = tempfile.mkstemp(
                dir=self.path.parent, prefix=self.path.name + ".", suffix=".tmp"
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(payload, handle, indent=4, ensure_ascii=False)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_name, self.path)  # atomic: old file or new file, never half
            except BaseException:
                try:
                    os.unlink(temp_name)
                except OSError:
                    pass
                raise
        except OSError as exc:
            raise StorageError(f"Could not save your accounts: {exc}") from exc
