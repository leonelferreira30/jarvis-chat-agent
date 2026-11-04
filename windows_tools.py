"""Windows file tools for JARVIS.

User files can be searched and managed outside the application workspace.
System folders are protected from writes. Destructive actions require confirmation.
"""
import os
import shutil
from pathlib import Path

PROTECTED_NAMES = {"windows", "program files", "program files (x86)", "programdata", "$recycle.bin", "system volume information"}
MAX_TEXT_BYTES = 2_000_000

def resolve_path(raw, for_write=False):
    raw = os.path.expandvars(os.path.expanduser(str(raw or "").strip().strip('"')))
    if not raw:
        raise ValueError("Informe um caminho.")
    target = os.path.abspath(raw)
    if for_write:
        parts = {p.casefold() for p in Path(target).parts}
        if parts & PROTECTED_NAMES:
            raise PermissionError("Pasta protegida do Windows: gravação bloqueada.")
    return target

def search_files(name, folder=None, limit=100):
    term = str(name or "").casefold().strip()
    if not term:
        return {"error": "Informe o nome ou parte do nome do arquivo."}
    root = resolve_path(folder or str(Path.home()))
    if not os.path.isdir(root):
        return {"error": f"Pasta não encontrada: {root}"}
    results = []
    for current, dirs, files in os.walk(root, onerror=lambda _e: None):
        dirs[:] = [d for d in dirs if d.casefold() not in PROTECTED_NAMES and not d.startswith(".")]
        for filename in files:
            if term in filename.casefold():
                results.append(os.path.join(current, filename))
                if len(results) >= limit:
                    return {"results": results, "truncated": True}
    return {"results": results, "truncated": False}

def list_files(folder):
    root = resolve_path(folder)
    if not os.path.isdir(root):
        return {"error": f"Pasta não encontrada: {root}"}
    items = []
    with os.scandir(root) as entries:
        for entry in entries:
            try:
                items.append({"name": entry.name, "type": "folder" if entry.is_dir(follow_symlinks=False) else "file"})
            except OSError:
                continue
    return {"path": root, "items": items[:300]}

def read_text(path):
    target = resolve_path(path)
    if not os.path.isfile(target):
        return {"error": f"Arquivo não encontrado: {target}"}
    if os.path.getsize(target) > MAX_TEXT_BYTES:
        return {"error": "Arquivo maior que 2 MB; leitura bloqueada para evitar travamento."}
    try:
        with open(target, "r", encoding="utf-8-sig") as f:
            return {"path": target, "content": f.read()}
    except UnicodeDecodeError:
        return {"error": "Arquivo não é texto UTF-8."}

def write_text(path, content, confirm):
    target = resolve_path(path, for_write=True)
    if len(content.encode("utf-8")) > MAX_TEXT_BYTES:
        return {"error": "Conteúdo maior que 2 MB."}
    action = "Substituir" if os.path.exists(target) else "Criar"
    if not confirm(f"{action} arquivo", f"{action} este arquivo?\n{target}"):
        return {"cancelled": True}
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        f.write(content)
    return {"success": True, "path": target}

def create_folder(path, confirm):
    target = resolve_path(path, for_write=True)
    if os.path.isdir(target):
        return {"success": True, "already_exists": True, "path": target}
    if not confirm("Criar pasta", f"Criar esta pasta?\n{target}"):
        return {"cancelled": True}
    os.makedirs(target, exist_ok=True)
    return {"success": True, "path": target}

def move_or_copy(source, destination, mode, confirm):
    src = resolve_path(source)
    dst = resolve_path(destination, for_write=True)
    if not os.path.exists(src):
        return {"error": f"Origem não encontrada: {src}"}
    if mode not in ("mover", "copiar"):
        return {"error": "Modo deve ser mover ou copiar."}
    if not confirm("Confirmar operação", f"{mode.title()} de:\n{src}\nPara:\n{dst}"):
        return {"cancelled": True}
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if mode == "mover":
        shutil.move(src, dst)
    elif os.path.isdir(src):
        shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        shutil.copy2(src, dst)
    return {"success": True, "path": dst}


def download_file(url, destination, confirm):
    from urllib.parse import urlparse
    from urllib.request import Request, urlopen
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        return {"error": "Por segurança, downloads exigem um endereço HTTPS válido."}
    target = resolve_path(destination, for_write=True)
    if not confirm("Confirmar download", f"Baixar este arquivo?\\nOrigem: {url}\\nDestino: {target}\\nO arquivo não será executado automaticamente."):
        return {"cancelled": True}
    os.makedirs(os.path.dirname(target), exist_ok=True)
    request = Request(url, headers={"User-Agent": "JARVIS-Windows-Agent/1.0"})
    total = 0
    try:
        with urlopen(request, timeout=45) as response, open(target, "wb") as output:
            while True:
                chunk = response.read(64 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > 150 * 1024 * 1024:
                    output.close()
                    os.remove(target)
                    return {"error": "Download excedeu 150 MB e foi cancelado."}
                output.write(chunk)
    except Exception:
        if os.path.exists(target):
            os.remove(target)
        raise
    return {"success": True, "path": target, "bytes": total, "executed": False}
