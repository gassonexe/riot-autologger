"""Password encryption with Windows DPAPI. Run `python crypto.py` on Windows to check it works."""

import base64
import sys

_PREFIX = "dpapi:"
_CRYPTPROTECT_UI_FORBIDDEN = 0x01


class CryptoError(Exception):
    pass


def _dpapi(data: bytes, protect: bool) -> bytes:
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p

    buffer = ctypes.create_string_buffer(data, max(len(data), 1))
    blob_in = DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
    blob_out = DATA_BLOB()

    function = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    ok = function(
        ctypes.byref(blob_in), None, None, None, None,
        _CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(blob_out),
    )
    if not ok:
        action = "encrypt" if protect else "decrypt"
        raise CryptoError(
            f"Windows could not {action} the data (error {ctypes.GetLastError()}). "
            "Encrypted passwords only work for the Windows user that saved them."
        )
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        kernel32.LocalFree(ctypes.cast(blob_out.pbData, ctypes.c_void_p))


class DpapiCrypto:

    def __init__(self):
        if sys.platform != "win32":
            raise CryptoError("Password encryption needs Windows (DPAPI).")

    def encrypt(self, text: str) -> str:
        raw = _dpapi(text.encode("utf-8"), protect=True)
        return _PREFIX + base64.b64encode(raw).decode("ascii")

    def decrypt(self, token: str) -> str:
        if not token.startswith(_PREFIX):
            raise CryptoError("Stored password is not in the expected encrypted format.")
        try:
            raw = base64.b64decode(token[len(_PREFIX):], validate=True)
        except ValueError as exc:
            raise CryptoError("Stored password is damaged.") from exc
        return _dpapi(raw, protect=False).decode("utf-8")


if __name__ == "__main__":
    crypto = DpapiCrypto()
    sample = "p@ss wörd!#1 "
    token = crypto.encrypt(sample)
    assert token.startswith(_PREFIX) and sample not in token
    assert crypto.decrypt(token) == sample
    print("DPAPI round trip OK")
