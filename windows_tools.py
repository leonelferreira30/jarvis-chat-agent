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


def diagnose_windows(kind):
    import subprocess
    commands = {
        "rede": ["ipconfig", "/all"],
        "sistema": ["systeminfo"],
        "processos": ["tasklist"],
    }
    if kind not in commands:
        return {"error": "Diagnósticos disponíveis: rede, sistema ou processos."}
    result = subprocess.run(commands[kind], capture_output=True, text=True, timeout=60, shell=False)
    return {"returncode": result.returncode, "output": (result.stdout or result.stderr)[-12000:]}

def repair_windows(kind, confirm):
    import subprocess
    jobs = {
        "limpar_dns": (["ipconfig", "/flushdns"], "Limpar o cache DNS. Não altera arquivos pessoais."),
        "verificar_arquivos": (["sfc", "/scannow"], "Verificar e tentar reparar arquivos protegidos do Windows. Pode demorar bastante."),
    }
    if kind not in jobs:
        return {"error": "Reparos disponíveis: limpar_dns ou verificar_arquivos."}
    command, description = jobs[kind]
    if not confirm("Autorizar reparo do Windows", description + "\\n\\nO Windows pode solicitar privilégios de administrador."):
        return {"cancelled": True}
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=3600, shell=False)
        return {"returncode": result.returncode, "output": (result.stdout + "\\n" + result.stderr)[-14000:]}
    except subprocess.TimeoutExpired:
        return {"error": "O reparo demorou mais que o limite de uma hora. Verifique o estado do Windows antes de tentar novamente."}


def open_chrome_window(url=None):
    """Open a new Google Chrome window without invoking a shell command."""
    import subprocess
    import shutil
    from pathlib import Path

    candidates = []
    found = shutil.which("chrome") or shutil.which("chrome.exe")
    if found:
        candidates.append(found)

    local = os.environ.get("LOCALAPPDATA", "")
    program_files = os.environ.get("PROGRAMFILES", r"C:\\Program Files")
    program_files_x86 = os.environ.get("PROGRAMFILES(X86)", r"C:\\Program Files (x86)")
    for base in (local, program_files, program_files_x86):
        if base:
            candidates.append(str(Path(base) / "Google" / "Chrome" / "Application" / "chrome.exe"))

    # App Paths is the usual Windows registration for Chrome.
    try:
        import winreg
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for key_path in (
                r"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\chrome.exe",
                r"SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\App Paths\\chrome.exe",
            ):
                try:
                    with winreg.OpenKey(hive, key_path) as key:
                        value, _ = winreg.QueryValueEx(key, "")
                        candidates.insert(0, value)
                except OSError:
                    pass
    except ImportError:
        pass

    chrome = next((p for p in candidates if p and os.path.isfile(p)), None)
    if not chrome:
        return {"success": False, "error": "Google Chrome não foi encontrado. Verifique se está instalado."}

    args = [chrome, "--new-window"]
    if url:
        from urllib.parse import urlparse
        parsed = urlparse(str(url).strip())
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return {"success": False, "error": "O endereço precisa começar com http:// ou https:// e ser válido."}
        args.append(str(url).strip())

    try:
        process = subprocess.Popen(args, close_fds=True)
        return {"success": True, "browser": "Google Chrome", "new_window_requested": True, "pid": process.pid, "url": url or None}
    except OSError as exc:
        return {"success": False, "error": f"Não foi possível iniciar o Chrome: {exc}"}
