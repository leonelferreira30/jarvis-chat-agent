JARVIS CHAT AGENT — EDIÇÃO DEEPSEEK (WINDOWS)

IA principal online: DeepSeek API. A API pode gerar cobrança conforme o uso.

INSTALAÇÃO
1. Extraia a pasta JARVIS_Chat_Agent.
2. Abra o Prompt de Comando dentro dela.
3. Execute: py -m pip install -r requirements.txt
4. Execute: py jarvis.py
5. Clique em Configurações, escolha deepseek e mantenha o modelo deepseek-flash.
6. Cole sua chave API no campo protegido e salve.

SEGURANÇA DA CHAVE
A chave não é escrita em config.json. O programa usa o Gerenciador de Credenciais do Windows via keyring. Se esse armazenamento não estiver disponível, a gravação é recusada. Não compartilhe chaves em chats ou prints. Como uma chave foi exposta nesta conversa, a recomendação segura continua sendo revogá-la e criar outra; esta versão não utiliza a chave publicada.

RECURSOS
- Chat em português e planejamento em várias etapas.
- Ferramentas limitadas à pasta workspace: listar, ler, criar pastas e gravar arquivos.
- Confirmação antes de gravar arquivos e executar scripts Python.
- Memória resumida em workspace/jarvis_project_memory.md.

LIMITES
Esta versão não controla mouse/teclado, navegador, e-mail ou todo o Windows. O conteúdo da conversa e dos arquivos enviados ao modelo é transmitido à DeepSeek. Revise scripts antes de autorizar sua execução.

GERAR EXE
No Windows, execute build_exe.bat. O executável será criado em dist\JARVIS\JARVIS.exe. Mantenha a pasta dist\JARVIS inteira.
