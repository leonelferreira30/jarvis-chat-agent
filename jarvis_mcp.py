"""Local MCP bridge exposing JARVIS's guarded Windows tools to Codex.

Run with Python on Windows:
    py -3 jarvis_mcp.py

The process speaks newline-delimited JSON-RPC on stdin/stdout. Keep stdout reserved
for MCP messages; diagnostics are written to stderr.
"""
import json
import logging
import sys
import tkinter as tk
from tkinter import messagebox

import windows_tools

# MCP stdio requires UTF-8 even when Windows' active code page is different.
for _stream in (sys.stdin, sys.stdout):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(levelname)s: %(message)s")
LOGGER = logging.getLogger("jarvis_mcp")

INSTRUCTIONS = (
    "JARVIS provides local Windows file and browser tools. Use them only for the "
    "user's requested task. Read and search tools return local data to the assistant. "
    "Writes, folder creation, moves/copies, and downloads show a Windows confirmation "
    "dialog. Downloads require HTTPS and are never executed. Do not use these tools "
    "to run arbitrary commands or bypass a confirmation."
)

TOOLS = [
    {
        "name": "jarvis_search_files",
        "description": "Search filenames under a Windows folder (defaults to the user's home folder). Returns matching paths.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Filename or substring to find."},
                "folder": {"type": "string", "description": "Optional folder to search."},
            },
            "required": ["name"],
            "additionalProperties": False,
        },
    },
    {
        "name": "jarvis_list_files",
        "description": "List files and folders in a Windows directory.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Full Windows path."}},
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "jarvis_read_text",
        "description": "Read a UTF-8 text file by full Windows path (files larger than 2 MB are refused).",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Full Windows path."}},
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "jarvis_write_text",
        "description": "Create or replace a UTF-8 text file. Shows a Windows confirmation dialog and blocks protected Windows folders.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Full Windows destination path."},
                "content": {"type": "string", "description": "Text to write."},
            },
            "required": ["path", "content"],
            "additionalProperties": False,
        },
    },
    {
        "name": "jarvis_create_folder",
        "description": "Create a Windows folder after confirmation. Protected Windows folders are blocked.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Full Windows destination path."}},
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "jarvis_move_or_copy",
        "description": "Move or copy a Windows file/folder after confirmation. Protected Windows destinations are blocked.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Full source path."},
                "destination": {"type": "string", "description": "Full destination path."},
                "mode": {"type": "string", "enum": ["mover", "copiar"]},
            },
            "required": ["source", "destination", "mode"],
            "additionalProperties": False,
        },
    },
    {
        "name": "jarvis_download_https",
        "description": "Download a file over HTTPS after confirmation. The downloaded file is never run automatically.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "HTTPS URL."},
                "destination": {"type": "string", "description": "Full Windows destination path."},
            },
            "required": ["url", "destination"],
            "additionalProperties": False,
        },
    },
    {
        "name": "jarvis_open_chrome_window",
        "description": "Open a new Google Chrome window, optionally at an HTTP or HTTPS URL.",
        "inputSchema": {
            "type": "object",
            "properties": {"url": {"type": "string", "description": "Optional HTTP or HTTPS URL."}},
            "additionalProperties": False,
        },
    },
]


def confirm_in_windows(title, message):
    """Use a fail-closed Windows dialog for operations already requiring approval."""
    root = None
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        return bool(messagebox.askyesno(title, message, parent=root, icon="warning"))
    except Exception:
        LOGGER.exception("Could not show the JARVIS confirmation dialog; denying the operation.")
        return False
    finally:
        if root is not None:
            try:
                root.destroy()
            except Exception:
                pass


def call_tool(name, args):
    if not isinstance(args, dict):
        return {"error": "Tool arguments must be an object."}
    try:
        if name == "jarvis_search_files":
            return windows_tools.search_files(args.get("name", ""), args.get("folder") or None)
        if name == "jarvis_list_files":
            return windows_tools.list_files(args["path"])
        if name == "jarvis_read_text":
            return windows_tools.read_text(args["path"])
        if name == "jarvis_write_text":
            return windows_tools.write_text(args["path"], args["content"], confirm_in_windows)
        if name == "jarvis_create_folder":
            return windows_tools.create_folder(args["path"], confirm_in_windows)
        if name == "jarvis_move_or_copy":
            return windows_tools.move_or_copy(
                args["source"], args["destination"], args["mode"], confirm_in_windows
            )
        if name == "jarvis_download_https":
            return windows_tools.download_file(args["url"], args["destination"], confirm_in_windows)
        if name == "jarvis_open_chrome_window":
            return windows_tools.open_chrome_window(args.get("url"))
        return {"error": f"Unknown tool: {name}"}
    except Exception as exc:
        LOGGER.exception("JARVIS tool failed: %s", name)
        return {"error": str(exc)}


def rpc_result(request_id, result):
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def rpc_error(request_id, code, message):
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def handle_message(message):
    if not isinstance(message, dict):
        return None
    method = message.get("method")
    request_id = message.get("id")

    if method == "notifications/initialized" or (method and method.startswith("notifications/")):
        return None
    if method == "initialize":
        params = message.get("params") or {}
        version = params.get("protocolVersion", "2025-06-18")
        return rpc_result(request_id, {
            "protocolVersion": version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "JARVIS Windows Agent", "version": "0.1.0"},
            "instructions": INSTRUCTIONS,
        })
    if method == "ping":
        return rpc_result(request_id, {})
    if method == "tools/list":
        return rpc_result(request_id, {"tools": TOOLS})
    if method == "tools/call":
        params = message.get("params") or {}
        name = params.get("name", "")
        result = call_tool(name, params.get("arguments") or {})
        is_error = isinstance(result, dict) and (bool(result.get("error")) or result.get("success") is False)
        return rpc_result(request_id, {
            "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
            "isError": is_error,
        })
    if request_id is not None:
        return rpc_error(request_id, -32601, f"Method not found: {method}")
    return None


def main():
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        request = None
        try:
            request = json.loads(line)
            response = handle_message(request)
            if response is not None:
                sys.stdout.write(json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n")
                sys.stdout.flush()
        except Exception as exc:
            LOGGER.exception("MCP message could not be handled.")
            request_id = request.get("id") if isinstance(request, dict) else None
            if request_id is not None:
                sys.stdout.write(json.dumps(rpc_error(request_id, -32603, str(exc)), ensure_ascii=False) + "\n")
                sys.stdout.flush()


if __name__ == "__main__":
    main()
