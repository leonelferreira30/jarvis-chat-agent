JARVIS CHAT AGENT — WINDOWS AGENT (EM DESENVOLVIMENTO)

REQUISITOS
- Windows 10/11
- Python 3.10 ou superior
- Ollama instalado e executando para o provedor local configurado
- Instale dependências: py -m pip install -r requirements.txt

INICIAR
1. Baixe/clique em Code > Download ZIP ou clone este repositório.
2. Abra o Prompt de Comando na pasta do projeto.
3. Execute: py -m pip install -r requirements.txt
4. Execute: py jarvis.py

RECURSOS IMPLEMENTADOS NESTA BRANCH
- Interface de chat Tkinter em português.
- Planejamento em várias etapas com ferramentas.
- Pesquisa de arquivos pelo nome na pasta do usuário ou em uma pasta indicada.
- Listagem e leitura de arquivos de texto por caminho completo.
- Criação e edição de arquivos de texto em locais indicados pelo usuário.
- Criação de pastas.
- Cópia e movimentação de arquivos e pastas.
- Confirmação antes de criar, substituir, copiar ou mover arquivos.
- Bloqueio de gravação em diretórios críticos do Windows.
- Memória resumida dentro de workspace.

CONECTAR O JARVIS AO CODEX
O servidor MCP local permite que o Codex chame as ferramentas do JARVIS nesta máquina. O modelo do Codex interpreta seu pedido e escolhe as ferramentas; não é preciso cadastrar uma chave de provedor no JARVIS para essa integração.

Para usar o código-fonte:
1. Instale as dependências e deixe a pasta do repositório no computador.
2. No Codex desktop, abra Configurações > Servidores MCP > Adicionar servidor e escolha STDIO.
3. Use o comando py e os argumentos -3 e o caminho completo para jarvis_mcp.py. Defina a pasta do repositório como diretório de trabalho. Salve e reinicie o Codex.
4. Depois de conectado, peça no chat para usar as ferramentas locais do JARVIS para a tarefa. Os nomes das ferramentas começam com jarvis_.

Se preferir editar ~/.codex/config.toml, acrescente esta configuração e substitua o caminho de exemplo pelo caminho real da pasta do repositório. Em caminhos TOML com barras invertidas, use duas barras por separador:
[mcp_servers.jarvis]
command = "py"
args = ["-3", "C:\\caminho\\para\\jarvis-chat-agent\\jarvis_mcp.py"]
cwd = "C:\\caminho\\para\\jarvis-chat-agent"
default_tools_approval_mode = "prompt"
tool_timeout_sec = 120

Confirmações e limites:
- Criar ou substituir arquivos, criar pastas, mover/copiar arquivos e baixar arquivos mostram uma confirmação no Windows.
- Gravações em pastas protegidas do Windows são bloqueadas.
- Downloads exigem HTTPS e nunca são executados automaticamente.
- O servidor não expõe uma ferramenta para executar comandos arbitrários.
- Ferramentas de leitura e busca podem retornar conteúdo local ao Codex; use-as somente para a tarefa solicitada.

GERAR EXECUTÁVEIS
No Windows, execute build_exe.bat. O aplicativo fica em dist\\JARVIS\\JARVIS.exe e o servidor local MCP em dist\\JARVIS-MCP.exe. No Codex, configure o executável JARVIS-MCP.exe como servidor STDIO. Mantenha a pasta completa do JARVIS ao distribuir.

IMPORTANTE — LIMITES DESTA VERSÃO
A integração não concede acesso irrestrito nem executa comandos arbitrários. O JARVIS pode baixar arquivos HTTPS com confirmação e abrir o Chrome; instalações de programas, drivers, reparos do Windows e automação avançada não são expostos pelo servidor MCP.
Arquivos binários (por exemplo, imagens, executáveis e documentos complexos) não são editados pela ferramenta de texto. Não execute arquivos baixados sem verificar sua origem e assinatura. Operações de escrita em diretórios críticos do Windows são bloqueadas.
