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

IMPORTANTE — LIMITES DESTA VERSÃO
Esta etapa corrige o bloqueio que limitava todas as operações à pasta workspace. Ela não concede acesso irrestrito nem executa qualquer comando arbitrário. Reparos do Windows, downloads/instalações, controle de programas, drivers e automação avançada ainda precisam ser implementados e testados em etapas próprias.
Arquivos binários (por exemplo, imagens, executáveis e documentos complexos) não são editados pela ferramenta de texto. Não execute arquivos baixados sem verificar sua origem e assinatura. Operações de escrita em diretórios críticos do Windows são bloqueadas.

GERAR EXECUTÁVEL
No Windows, execute build_exe.bat. O executável fica em dist\JARVIS\JARVIS.exe. Mantenha a pasta completa ao distribuir.
