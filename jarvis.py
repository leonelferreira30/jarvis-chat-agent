import os, sys, json, threading, queue, urllib.request, urllib.error, datetime, subprocess
try:
    import keyring
except Exception:
    keyring = None
import tkinter as tk
import windows_tools
from tkinter import ttk, messagebox, filedialog

APP_DIR = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
CONFIG_FILE = os.path.join(APP_DIR, "config.json")
WORKSPACE = os.path.join(APP_DIR, "workspace")
os.makedirs(WORKSPACE, exist_ok=True)

DEFAULT = {
    "provider": "ollama",
    "model": "qwen2.5:1.5b",
    "base_url": "http://localhost:11434",
    "openai_model": "",
    "max_steps": 8
}

def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        loaded.pop("api_key", None)
        provider = loaded.get("provider", DEFAULT["provider"])
        if provider not in ("ollama", "deepseek", "gemini", "openai_compatible"):
            provider = DEFAULT["provider"]
        loaded["provider"] = provider
        if provider == "deepseek":
            loaded["base_url"] = loaded.get("base_url") or "https://api.deepseek.com"
            loaded["openai_model"] = loaded.get("openai_model") or "deepseek-chat"
        elif provider == "gemini":
            loaded["base_url"] = loaded.get("base_url") or "https://generativelanguage.googleapis.com/v1beta/openai"
            loaded["openai_model"] = loaded.get("openai_model") or "gemini-2.5-flash"
        elif provider == "openai_compatible":
            loaded["base_url"] = loaded.get("base_url") or "https://api.openai.com/v1"
        return {**DEFAULT, **loaded}
    except Exception:
        return DEFAULT.copy()

CFG = load_config()

SYSTEM = """Você é JARVIS, um agente de trabalho para Windows, que conversa em português brasileiro.
Responda sempre em português do Brasil.
Ajude a concluir tarefas grandes com planejamento, execução em etapas e verificação.
Quando o usuário pedir uma ação no computador, use a ferramenta apropriada em vez de apenas descrever etapas.
Nunca diga que criou, leu, abriu, moveu ou baixou algo sem chamar a ferramenta correspondente e receber um resultado que confirme a operação.
Se uma ferramenta falhar, informe o erro real e proponha o próximo passo seguro. Não invente sucesso.
Se a tarefa exigir ações no computador, use as ferramentas disponíveis. Você pode trabalhar nos arquivos do usuário fora da pasta workspace quando ele indicar um caminho ou pedir uma busca. Nunca altere pastas críticas do Windows. Use as ferramentas de arquivos do Windows e confirme antes de criar, substituir, mover ou copiar arquivos.
Antes de criar ou sobrescrever arquivos, peça confirmação ao usuário por meio da ferramenta de confirmação.
Nunca diga que concluiu algo sem verificar o resultado.
Não revele raciocínio interno privado. Em vez disso, apresente planos, decisões resumidas, progresso e resultados verificáveis.
Se faltar informação essencial, faça uma pergunta objetiva.
Se uma tarefa for grande, divida em etapas pequenas e execute o máximo possível com as ferramentas permitidas."""

TOOLS = [
 {"type":"function","function":{"name":"search_files","description":"Procura arquivos pelo nome em uma pasta do Windows. Se a pasta não for informada, pesquisa na pasta do usuário.","parameters":{"type":"object","properties":{"name":{"type":"string"},"folder":{"type":"string"}},"required":["name"]}}},
 {"type":"function","function":{"name":"list_windows_files","description":"Lista arquivos e pastas em qualquer pasta acessível do Windows.","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},
 {"type":"function","function":{"name":"read_windows_file","description":"Lê um arquivo de texto por caminho completo no Windows.","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},
 {"type":"function","function":{"name":"write_windows_file","description":"Cria ou substitui um arquivo de texto em um caminho completo do Windows. Exige confirmação.","parameters":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]}}},
 {"type":"function","function":{"name":"create_windows_folder","description":"Cria uma pasta no Windows em um caminho completo. Exige confirmação.","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},
 {"type":"function","function":{"name":"move_or_copy_windows_item","description":"Move ou copia um arquivo/pasta para outro caminho. Exige confirmação.","parameters":{"type":"object","properties":{"source":{"type":"string"},"destination":{"type":"string"},"mode":{"type":"string","enum":["mover","copiar"]}},"required":["source","destination","mode"]}}},
 {"type":"function","function":{"name":"download_windows_file","description":"Baixa um arquivo ou instalador por HTTPS para um caminho indicado. Exige confirmação e nunca executa o download automaticamente.","parameters":{"type":"object","properties":{"url":{"type":"string"},"destination":{"type":"string"}},"required":["url","destination"]}}},
 {"type":"function","function":{"name":"diagnose_windows","description":"Executa diagnósticos somente de leitura no Windows: rede, sistema ou processos.","parameters":{"type":"object","properties":{"kind":{"type":"string","enum":["rede","sistema","processos"]}},"required":["kind"]}}},
 {"type":"function","function":{"name":"open_chrome_window","description":"Abre uma nova janela do Google Chrome. Pode abrir um endereço HTTP ou HTTPS opcional.","parameters":{"type":"object","properties":{"url":{"type":"string","description":"Endereço web opcional, começando com http:// ou https://"}},"required":[]}}},
 {"type":"function","function":{"name":"list_files","description":"Lista arquivos e pastas dentro do workspace ou de uma subpasta dele.","parameters":{"type":"object","properties":{"path":{"type":"string","description":"Subpasta relativa; use vazio para a raiz."}},"required":["path"]}}},
 {"type":"function","function":{"name":"read_file","description":"Lê um arquivo de texto dentro do workspace.","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},
 {"type":"function","function":{"name":"write_file","description":"Cria ou substitui um arquivo de texto no workspace. Sempre exige confirmação do usuário.","parameters":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]}}},
 {"type":"function","function":{"name":"create_folder","description":"Cria uma pasta dentro do workspace.","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},
 {"type":"function","function":{"name":"run_python","description":"Executa um arquivo Python existente dentro do workspace. Sempre exige confirmação.","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}}
]

def safe_path(rel):
    rel = rel.strip().replace("\\", os.sep).replace("/", os.sep)
    full = os.path.abspath(os.path.join(WORKSPACE, rel))
    if os.path.commonpath([WORKSPACE, full]) != os.path.abspath(WORKSPACE):
        raise ValueError("Acesso negado: caminho fora do workspace.")
    return full

class Jarvis:
    def __init__(self, root):
        self.root = root
        root.title("JARVIS • Agente de IA")
        root.geometry("1120x760")
        root.minsize(850, 600)
        root.configure(bg="#08111f")
        self.q = queue.Queue()
        self.busy = False
        self.messages = [{"role":"system","content":SYSTEM}]
        self.project_notes = self.load_notes()
        self.build()
        self.add_message("assistant", "Olá! Sou o JARVIS. Posso planejar e executar trabalhos no seu workspace, criar arquivos, programar e acompanhar projetos. O que vamos fazer?")
        self.root.after(120, self.poll)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def load_notes(self):
        p = os.path.join(WORKSPACE, "jarvis_project_memory.md")
        try:
            with open(p, "r", encoding="utf-8") as f: return f.read()
        except: return ""

    def build(self):
        side = tk.Frame(self.root, bg="#0b1929", width=245)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        tk.Label(side, text="J.A.R.V.I.S", fg="#66dcff", bg="#0b1929",
                 font=("Segoe UI", 23, "bold")).pack(anchor="w", padx=18, pady=(22,0))
        tk.Label(side, text="AGENTE DE TRABALHO IA", fg="#8da9bd", bg="#0b1929",
                 font=("Segoe UI", 9)).pack(anchor="w", padx=20, pady=(0,25))
        ttk.Button(side, text="＋ Nova conversa", command=self.new_chat).pack(fill="x", padx=14, pady=5)
        ttk.Button(side, text="📁 Abrir workspace", command=self.open_workspace).pack(fill="x", padx=14, pady=5)
        ttk.Button(side, text="⚙ Configurações", command=self.settings).pack(fill="x", padx=14, pady=5)
        ttk.Button(side, text="▤ Memória do projeto", command=self.show_memory).pack(fill="x", padx=14, pady=5)
        tk.Frame(side, bg="#20384d", height=1).pack(fill="x", padx=14, pady=18)
        tk.Label(side, text="CAPACIDADES", fg="#66dcff", bg="#0b1929",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=18)
        for item in ["Planejar tarefas", "Criar e editar arquivos", "Programar projetos", "Organizar documentos", "Executar scripts Python*", "Memória persistente"]:
            tk.Label(side, text="• " + item, fg="#c3d3df", bg="#0b1929",
                     font=("Segoe UI", 9)).pack(anchor="w", padx=20, pady=4)
        tk.Label(side, text="* com confirmação", fg="#708da3", bg="#0b1929",
                 font=("Segoe UI", 8)).pack(anchor="w", padx=20, pady=(10,0))
        main = tk.Frame(self.root, bg="#08111f")
        main.pack(side="left", fill="both", expand=True)
        top = tk.Frame(main, bg="#08111f")
        top.pack(fill="x", padx=22, pady=(18,8))
        tk.Label(top, text="Área de trabalho", fg="#e5f4ff", bg="#08111f",
                 font=("Segoe UI", 16, "bold")).pack(side="left")
        self.status = tk.Label(top, text="● Pronto", fg="#64e6a5", bg="#08111f",
                               font=("Segoe UI", 9))
        self.status.pack(side="right")

        # Criação do chat sem chamar pack() imediatamente
        self.chat = tk.Text(main, bg="#0d1b2c", fg="#d9edf7", insertbackground="white",
                            font=("Segoe UI", 10), relief="flat", wrap="word",
                            padx=18, pady=16, spacing1=3, spacing3=9)
        self.chat.tag_config("user", foreground="#78d9ff", font=("Segoe UI",10,"bold"))
        self.chat.tag_config("assistant", foreground="#9ff0c4", font=("Segoe UI",10,"bold"))
        self.chat.tag_config("body", foreground="#e1edf5")
        self.chat.tag_config("system", foreground="#ffcb80")

        # Configuração do painel inferior (entradas e botões)
        bottom = tk.Frame(main, bg="#08111f")
        self.entry = tk.Text(bottom, height=4, bg="#102338", fg="#f0f7ff",
                             insertbackground="white", font=("Segoe UI",10),
                             relief="flat", padx=12, pady=10, wrap="word")
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", self.on_entry_return)
        self.entry.bind("<Control-Return>", self.on_entry_newline)
        buttons = tk.Frame(bottom, bg="#08111f")
        buttons.pack(side="right", padx=(10,0), fill="y")
        self.send_btn = ttk.Button(buttons, text="Enviar  ➤", command=self.send)
        self.send_btn.pack(fill="x", pady=(0,6))
        ttk.Button(buttons, text="Limpar", command=self.clear_input).pack(fill="x")

        # Área de entrada fixa na parte inferior
        bottom.pack(side="bottom", fill="x", padx=20, pady=(0,18))

        # Área de conversa ocupa o espaço restante
        self.chat.pack(side="top", fill="both", expand=True, padx=20, pady=10)

        # Foco inicial na caixa de mensagem
        self.entry.focus_set()

    def add_message(self, role, text):
        label = "VOCÊ" if role == "user" else ("JARVIS" if role == "assistant" else "SISTEMA")
        tag = role if role in ("user","assistant","system") else "assistant"
        self.chat.configure(state="normal")
        self.chat.insert("end", label + "\n", tag)
        self.chat.insert("end", text + "\n\n", "body")
        self.chat.configure(state="disabled")
        self.chat.see("end")

    def on_entry_return(self, event=None):
        if self.busy:
            return "break"
        if self.entry.get("1.0","end").strip():
            self.send()
        return "break"

    def on_entry_newline(self, event=None):
        self.entry.insert("insert", "\n")
        return "break"

    def clear_input(self):
        self.entry.delete("1.0","end")
        self.entry.focus_set()

    def send(self):
        if self.busy: return
        text = self.entry.get("1.0","end").strip()
        if not text: return
        self.entry.delete("1.0","end")
        self.add_message("user", text)
        self.messages.append({"role":"user","content":text})
        self.busy = True
        self.status.config(text="● Trabalhando...", fg="#ffcb80")
        self.send_btn.config(state="disabled")
        threading.Thread(target=self.agent_loop, daemon=True).start()

    def describe_tool_action(self, name, args):
        labels = {
            "search_files": "procurar arquivos", "list_windows_files": "listar uma pasta",
            "read_windows_file": "ler um arquivo", "write_windows_file": "criar ou editar um arquivo",
            "create_windows_folder": "criar uma pasta", "move_or_copy_windows_item": "mover ou copiar um item",
            "download_windows_file": "baixar um arquivo", "diagnose_windows": "diagnosticar o Windows",
            "open_chrome_window": "abrir uma nova janela do Google Chrome",
            "list_files": "listar arquivos do workspace", "read_file": "ler arquivo do workspace",
            "write_file": "gravar arquivo no workspace", "create_folder": "criar pasta no workspace",
            "run_python": "executar script Python",
        }
        detail = args.get("name", "") if name == "search_files" else args.get("url", "") if name == "open_chrome_window" else args.get("kind", "") if name == "diagnose_windows" else args.get("destination", "") if name == "download_windows_file" else args.get("path", "")
        return labels.get(name, name or "ferramenta") + (f" — {str(detail)[:140]}" if detail else "")
    def agent_loop(self):
        try:
            if self.project_notes:
                self.messages[0]["content"] = SYSTEM + "\n\nMEMÓRIA DO PROJETO (contexto resumido):\n" + self.project_notes[-12000:]
            else:
                self.messages[0]["content"] = SYSTEM
            for step in range(int(CFG.get("max_steps",8))):
                self.q.put(("progress", f"Etapa {step + 1}: analisando o pedido e planejando a próxima ação..."))
                response = self.call_model(self.messages)
                msg = response.get("message", {})
                tool_calls = msg.get("tool_calls") or []
                if not tool_calls:
                    answer = msg.get("content") or "Não recebi uma resposta textual."
                    self.messages.append({"role":"assistant","content":answer})
                    self.q.put(("answer", answer))
                    self.save_session_note()
                    return
                self.messages.append(msg)
                for call in tool_calls:
                    fn = call.get("function", {})
                    name = fn.get("name")
                    args = fn.get("arguments", {})
                    if isinstance(args, str):
                        args = json.loads(args)
                    action = self.describe_tool_action(name, args)
                    self.q.put(("progress", f"Tentando executar: {action}..."))
                    result = self.run_tool(name, args)
                    self.messages.append({"role":"tool","tool_call_id":call.get("id"),"name":name,"content":json.dumps(result,ensure_ascii=False)})
                    if isinstance(result, dict) and result.get("cancelled"):
                        self.q.put(("progress", f"Operação cancelada: {action}."))
                    elif isinstance(result, dict) and (result.get("error") or result.get("success") is False):
                        error_text = str(result.get("error") or "erro não especificado")[:220]
                        self.q.put(("progress", f"Falha ao executar: {action} — {error_text}"))
                    elif isinstance(result, dict) and result.get("success") is True:
                        self.q.put(("progress", f"Concluído: {action}."))
                    else:
                        self.q.put(("progress", f"Etapa executada: {action}. Resultado recebido; verificando a próxima etapa."))
            self.q.put(("answer","Atingi o limite de etapas desta rodada. Posso continuar se você pedir."))
        except Exception as e:
            self.q.put(("error", str(e)))
        finally:
            self.q.put(("done", None))

    def get_api_key(self, provider=None):
        provider = provider or CFG.get("provider", "deepseek")
        account = provider + "_api_key"
        if keyring:
            try:
                secret = keyring.get_password("JARVIS", account)
                if secret:
                    return secret
                # Compatibilidade com versões antigas que salvavam apenas a chave do DeepSeek.
                if provider == "deepseek":
                    secret = keyring.get_password("JARVIS", "deepseek_api_key")
                    if secret:
                        return secret
            except Exception:
                pass
        env_names = {
            "deepseek": "DEEPSEEK_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "openai_compatible": "JARVIS_API_KEY",
        }
        return os.environ.get(env_names.get(provider, ""), "")

    def call_model(self, messages):
        provider = CFG.get("provider", "deepseek")
        if provider == "ollama":
            url = CFG.get("base_url", "http://localhost:11434").rstrip("/") + "/api/chat"
            payload = {"model": CFG.get("model", "qwen2.5:3b"), "messages": messages, "tools": TOOLS, "stream": False}
            headers = {"Content-Type": "application/json"}
            api_format = False
        else:
            if provider == "deepseek":
                base_url, model = "https://api.deepseek.com", CFG.get("openai_model", "deepseek-chat")
            elif provider == "gemini":
                base_url = CFG.get("base_url", "https://generativelanguage.googleapis.com/v1beta/openai")
                model = CFG.get("openai_model", "gemini-2.5-flash")
            else:
                base_url, model = CFG.get("base_url", "https://api.openai.com/v1"), CFG.get("openai_model", "gpt-4.1-mini")
            api_key = self.get_api_key(provider)
            if not api_key:
                raise RuntimeError("Chave API não encontrada. Abra Configurações e salve a chave.")
            url = base_url.rstrip("/") + "/chat/completions"
            payload = {"model": model, "messages": messages, "tools": TOOLS, "tool_choice": "auto", "stream": False}
            if provider == "deepseek":
                payload["thinking"] = {"type": "disabled"}
            headers = {"Content-Type": "application/json", "Authorization": "Bearer " + api_key}
            api_format = True
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                data = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")[:1000]
            raise RuntimeError(f"Erro da API (HTTP {e.code}): {detail}")
        if not api_format:
            return data
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("A API não retornou nenhuma resposta.")
        return {"message": choices[0].get("message", {})}

    def ask_confirmation(self, title, message):
        event = threading.Event()
        result = {"approved": False}
        self.q.put(("confirm", (title, message, event, result)))
        if not event.wait(timeout=300):
            return False
        return bool(result["approved"])

    def run_tool(self, name, args):
        try:
            if name == "search_files":
                return windows_tools.search_files(args.get("name",""), args.get("folder") or None)
            if name == "list_windows_files":
                return windows_tools.list_files(args["path"])
            if name == "read_windows_file":
                return windows_tools.read_text(args["path"])
            if name == "write_windows_file":
                return windows_tools.write_text(args["path"], args.get("content",""), self.ask_confirmation)
            if name == "create_windows_folder":
                return windows_tools.create_folder(args["path"], self.ask_confirmation)
            if name == "move_or_copy_windows_item":
                return windows_tools.move_or_copy(args["source"], args["destination"], args["mode"], self.ask_confirmation)
            if name == "download_windows_file":
                return windows_tools.download_file(args["url"], args["destination"], self.ask_confirmation)
            if name == "diagnose_windows":
                return windows_tools.diagnose_windows(args["kind"])
            if name == "open_chrome_window":
                return windows_tools.open_chrome_window(args.get("url"))
            if name == "list_files":
                folder = safe_path(args.get("path",""))
                if not os.path.isdir(folder): return {"error":"Pasta não encontrada"}
                return {"items":[{"name":x,"type":"pasta" if os.path.isdir(os.path.join(folder,x)) else "arquivo"} for x in os.listdir(folder)[:200]]}
            if name == "read_file":
                p = safe_path(args["path"])
                if not os.path.isfile(p): return {"error":"Arquivo não encontrado"}
                if os.path.getsize(p) > 1_000_000: return {"error":"Arquivo maior que 1 MB; não lido por segurança."}
                with open(p,"r",encoding="utf-8") as f: return {"content":f.read()}
            if name == "create_folder":
                p = safe_path(args["path"])
                os.makedirs(p,exist_ok=True)
                return {"success":True,"path":args["path"]}
            if name == "write_file":
                rel = args["path"]
                content = args["content"]
                if len(content) > 2_000_000: return {"error":"Conteúdo excede 2 MB."}
                if not self.ask_confirmation("JARVIS quer criar/alterar um arquivo",
                    f"Permitir gravar este arquivo dentro do workspace?\n\n{rel}\n\nTamanho: {len(content)} caracteres"):
                    return {"cancelled":True}
                p = safe_path(rel)
                os.makedirs(os.path.dirname(p),exist_ok=True)
                with open(p,"w",encoding="utf-8") as f: f.write(content)
                return {"success":True,"path":rel,"bytes":len(content.encode("utf-8"))}
            if name == "run_python":
                p = safe_path(args["path"])
                if not p.lower().endswith(".py") or not os.path.isfile(p):
                    return {"error":"Informe um arquivo .py existente dentro do workspace."}
                if not self.ask_confirmation("Confirmar execução",f"Executar este script Python?\n\n{args['path']}\n\nScripts podem alterar seu computador."):
                    return {"cancelled":True}
                proc = subprocess.run([sys.executable,p],cwd=WORKSPACE,capture_output=True,text=True,timeout=60)
                return {"returncode":proc.returncode,"stdout":proc.stdout[-8000:],"stderr":proc.stderr[-4000:]}
            return {"error":"Ferramenta desconhecida"}
        except Exception as e:
            return {"error":str(e)}

    def poll(self):
        try:
            while True:
                kind, data = self.q.get_nowait()
                if kind == "answer": self.add_message("assistant",data)
                elif kind == "progress": self.add_message("system",data)
                elif kind == "error": self.add_message("system","Erro: "+data)
                elif kind == "confirm":
                    title, prompt, event, result = data
                    result["approved"] = messagebox.askyesno(title, prompt)
                    event.set()
                elif kind == "done":
                    self.busy = False
                    self.status.config(text="● Pronto",fg="#64e6a5")
                    self.send_btn.config(state="normal")
        except queue.Empty: pass
        self.root.after(120,self.poll)

    def save_session_note(self):
        recent = [m for m in self.messages if m.get("role") in ("user","assistant")][-18:]
        lines = ["# Memória de trabalho do JARVIS", "", "Atualizado: "+datetime.datetime.now().isoformat(timespec="minutes"), ""]
        for m in recent:
            content = m.get("content","")
            if isinstance(content,str) and content.strip():
                lines.append(("Usuário: " if m["role"]=="user" else "JARVIS: ")+content[:2500])
                lines.append("")
        try:
            with open(os.path.join(WORKSPACE,"jarvis_project_memory.md"),"w",encoding="utf-8") as f:
                f.write("\n".join(lines))
            self.project_notes = "\n".join(lines)
        except: pass

    def new_chat(self):
        if self.busy: return
        self.messages = [{"role":"system","content":SYSTEM}]
        self.chat.configure(state="normal"); self.chat.delete("1.0","end"); self.chat.configure(state="disabled")
        self.add_message("assistant","Nova conversa iniciada. Os arquivos do workspace continuam disponíveis.")

    def open_workspace(self):
        os.startfile(WORKSPACE)

    def show_memory(self):
        p = os.path.join(WORKSPACE,"jarvis_project_memory.md")
        if not os.path.exists(p):
            messagebox.showinfo("Memória","Ainda não há memória salva.")
        else:
            os.startfile(p)

    def settings(self):
        win = tk.Toplevel(self.root); win.title("Configurações do JARVIS"); win.geometry("560x500")
        win.configure(bg="#0d1b2c")
        tk.Label(win,text="Provedor de IA",fg="white",bg="#0d1b2c").pack(pady=(15,3))
        provider = tk.StringVar(value=CFG.get("provider", "ollama"))
        provider_box = ttk.Combobox(win,textvariable=provider,values=["ollama","gemini","deepseek","openai_compatible"],state="readonly")
        provider_box.pack()
        fields = {}
        for label,key,show in [
            ("Endereço base (OpenAI/Ollama)","base_url",None),
            ("Modelo local (Ollama)","model",None),
            ("Modelo online (Gemini: gemini-2.5-flash)","openai_model",None),
            ("Nova chave API (oculta; não será gravada em config.json)","api_key","*")]:
            tk.Label(win,text=label,fg="white",bg="#0d1b2c",wraplength=510).pack(pady=(10,2))
            v=tk.StringVar(value=(CFG.get(key,"") if key != "api_key" else ""))
            ttk.Entry(win,textvariable=v,width=68,show=show).pack(); fields[key]=v
        def apply_provider_defaults(_event=None):
            chosen = provider.get()
            default_urls = {"deepseek":"https://api.deepseek.com", "gemini":"https://generativelanguage.googleapis.com/v1beta/openai", "openai_compatible":"https://api.openai.com/v1", "ollama":"http://localhost:11434"}
            default_models = {"deepseek":"deepseek-chat", "gemini":"gemini-2.5-flash", "openai_compatible":"gpt-4.1-mini"}
            current_url = fields["base_url"].get().strip()
            if not current_url or current_url in set(default_urls.values()):
                fields["base_url"].set(default_urls.get(chosen, default_urls["ollama"]))
            current_model = fields["openai_model"].get().strip()
            if not current_model or current_model in set(default_models.values()):
                fields["openai_model"].set(default_models.get(chosen, ""))
        provider_box.bind("<<ComboboxSelected>>", apply_provider_defaults)
        tk.Label(win,text="Gemini gratuito: https://generativelanguage.googleapis.com/v1beta/openai • modelo: gemini-2.5-flash",fg="#9db4c7",bg="#0d1b2c",wraplength=510).pack(pady=(12,2))
        tk.Label(win,text="A chave é armazenada no Gerenciador de Credenciais do Windows.",fg="#9db4c7",bg="#0d1b2c",wraplength=510).pack()
        def save():
            chosen=provider.get(); CFG["provider"]=chosen
            default_urls = {"deepseek":"https://api.deepseek.com", "gemini":"https://generativelanguage.googleapis.com/v1beta/openai", "openai_compatible":"https://api.openai.com/v1", "ollama":"http://localhost:11434"}
            CFG["base_url"]=fields["base_url"].get().strip() or default_urls.get(chosen, "http://localhost:11434")
            CFG["model"]=fields["model"].get().strip() or "qwen2.5:1.5b"
            default_models = {"deepseek":"deepseek-chat", "gemini":"gemini-2.5-flash", "openai_compatible":"gpt-4.1-mini"}
            CFG["openai_model"]=fields["openai_model"].get().strip() or default_models.get(chosen, "")
            secret=fields["api_key"].get().strip()
            if secret:
                if not keyring:
                    messagebox.showerror("Armazenamento seguro indisponível","O módulo keyring não está disponível. Instale os requisitos atualizados."); return
                try: keyring.set_password("JARVIS",chosen + "_api_key",secret)
                except Exception as e: messagebox.showerror("Falha ao salvar chave",str(e)); return
            with open(CONFIG_FILE,"w",encoding="utf-8") as f:
                json.dump(CFG,f,ensure_ascii=False,indent=2)
            messagebox.showinfo("JARVIS","Configurações salvas. A chave não foi gravada no arquivo config.json."); win.destroy()
        ttk.Button(win,text="Salvar configurações",command=save).pack(pady=18)

    def close(self):
        self.root.destroy()

if __name__ == "__main__":
    root=tk.Tk()
    app=Jarvis(root)
    root.mainloop()