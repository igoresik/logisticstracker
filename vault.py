"""Encrypts saved keys with Windows DPAPI, so a copied tracker.db does not give them away.

Only the same Windows user on the same PC can decrypt. Other systems keep plain text.
"""

import base64
import sys

PREFIX = "dpapi:"

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    class _Blob(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_char))]

    def _crypt(function, data):
        source = _Blob(len(data), ctypes.create_string_buffer(data, len(data)))
        result = _Blob()
        if not function(ctypes.byref(source), None, None, None, None, 0, ctypes.byref(result)):
            raise OSError("Windows could not process the saved key")
        try:
            return ctypes.string_at(result.data, result.size)
        finally:
            ctypes.windll.kernel32.LocalFree(result.data)


def lock(text):
    if sys.platform != "win32" or not text or text.startswith(PREFIX):
        return text
    data = _crypt(ctypes.windll.crypt32.CryptProtectData, text.encode())
    return PREFIX + base64.b64encode(data).decode()


def unlock(value):
    if not value.startswith(PREFIX):
        return value
    try:
        data = base64.b64decode(value[len(PREFIX):])
        return _crypt(ctypes.windll.crypt32.CryptUnprotectData, data).decode()
    except (OSError, ValueError, NameError):
        return ""  # saved by another user or PC: the key has to be entered again
