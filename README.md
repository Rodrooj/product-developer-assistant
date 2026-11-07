# Product Developer Assistant 🚀

> **Workflow principal:** transforme pesquisa web e netnografia em um dossiê Markdown auditável, da coleta de fontes à síntese estruturada, diretamente pelo Plow Chat.

O **Product Developer Assistant** é um agente Plow/Hermes para esse fluxo de pesquisa de ponta a ponta. Ele também oferece seis capacidades complementares para dar continuidade ao trabalho de produto: documentos, design, GitHub, e-mail, arquivos e automações.

<img width="1254" height="1254" alt="Logo Assistant" src="https://github.com/user-attachments/assets/aede5bf4-0707-4f32-823a-5fc8211f5f14" />

---

## 🌟 Capacidades

### Workflow principal: pesquisa web → dossiê Markdown

A habilidade `web-research` conduz pesquisa de mercado, benchmarking competitivo e netnografia, registra fontes auditáveis e salva a síntese como um dossiê estruturado em Markdown.

### Todas as habilidades

A tabela abaixo apresenta a habilidade do workflow principal e as seis capacidades complementares.

| Habilidade | Identificador | O que faz | Como funciona |
|---|---|---|---|
| **Pesquisa de Mercado & Netnografia (workflow principal)** | `web-research` | Conduz pesquisas de mercado, benchmarking competitivo, análise de comunidades e gera dossiês estruturados em Markdown. | Navega na web através das ferramentas nativas do Latch (`plow_browser_*`), salvando evidências e links de fontes auditáveis. |
| **Revisão e Escrita de Documentos** | `document-reviewer` | Redige, revisa, audita e aprimora especificações, relatórios e PRDs no Apple Pages e Microsoft Word. | Automação nativa no macOS via AppleScript (`plow_run_applescript`), realizando edições pontuais e preservando estilos e formatação. |
| **Organização de Design & UI/UX** | `figma-organizer` | Inspeciona arquivos de design, componentes, design tokens, metadados e mapeamentos de Code Connect no Figma. | Integração direta com o servidor MCP oficial do Figma via OAuth 2.1 via cliente MCP do Hermes, com allowlist restrita em `image/seed/config.yaml`. |
| **Manutenção de Repositórios & Git** | `github-ops` | Acompanha PRs para revisão, issues atribuídas, commits recentes e status de workflows do GitHub Actions. | Execução via GitHub CLI (`gh`) autenticado no ambiente do container através da ferramenta `terminal`. |
| **Leitor de E-mails Multi-conta** | `email-reader` | Oferece perfis IMAP para Gmail, iCloud e Outlook; cada conta exige credenciais e autorização válidas no provedor. | Script `plow-imap.py` com seleção por `--account`. Gmail e iCloud tiveram validação funcional em desenvolvimento; Outlook está configurado, mas não foi validado funcionalmente. |
| **Organização de Arquivos Locais** | `file-organization` | Organiza arquivos da Mesa (Desktop), Downloads e projetos seguindo regras de categorização por tipo, contexto ou data. | Manipulação do sistema de arquivos local do Mac via ferramentas do Latch (`plow_run_command`). |
| **Automação & Agendamento Contínuo** | `automation` | Agenda rotinas periódicas (ex: resumos diários de PRs, checagem de e-mails, alertas de Figma) com suporte a suspensão do sistema. | Integração com Hermes Cron e LaunchAgent do macOS (`com.plow.product-assistant.automation-wake`), utilizando `caffeinate`. |

## ✅ Casos de uso reais

Consulte o [inventário de casos de uso e evidências](docs/USE_CASES.md). Ele distingue evidência pública de relatos operacionais que ainda dependem de artefatos externos para verificação independente.

---

## 🛠️ Arquitetura do Sistema

```text
               ┌──────────────────────────────┐
               │    Plow Chat (Interface)    │
               └──────────────┬───────────────┘
                              │
               ┌──────────────▼───────────────┐
               │    Hermes Gateway Daemon     │
               │   (Supervisionado por s6)    │
               └───────┬──────────────┬───────┘
                       │              │
       ┌───────────────▼──────┐ ┌─────▼────────────────┐
       │ Ferramentas Locais   │ │ Servidores MCP       │
       │ • GitHub CLI (gh)    │ │ • Figma MCP (OAuth)  │
       │ • IMAP Client        │ │ • Plow Latch MCP     │
       │ • Terminal Container │ └─────┬────────────────┘
       └──────────────────────┘       │
                         ┌────────────▼──────────────┐
                         │      Plow Latch (Mac)     │
                         │ • AppleScript (Pages/Word)│
                         │ • Sistema de Arquivos     │
                         │ • Navegador Web Nativo    │
                         └───────────────────────────┘
```

- **Ambiente Containerizado Seguro:** O agente executa em uma imagem Linux baseada em `s6-overlay`, garantindo que credenciais permaneçam isoladas e protegidas.
- **Ponte Latch (macOS):** Todas as operações que demandam interação com o computador físico do usuário (Pages, Word, Finder) passam pelo canal seguro do Plow Latch.
- **LaunchAgent Sleep/Wake Recovery:** Quando o Mac entra em repouso (*sleep*), um LaunchAgent monitora o despertar e aciona o despachante com `caffeinate`, garantindo que automações atrasadas executem imediatamente.

---

## 🚀 Como Configurar e Utilizar

### 1. Pré-requisitos
- [Docker](https://www.docker.com/) e Docker Compose instalados.
- [Plow Latch](https://github.com/plow-pbc/latch) instalado e ativo no seu Mac.
- [uv](https://github.com/astral-sh/uv) (opcional, para rodar os testes locais).

### 2. Clonar o Repositório
```bash
git clone https://github.com/Rodrooj/product-developer-assistant.git
cd product-developer-assistant
```

### 3. Configurar Credenciais

O repositório fornece templates prontos para você preencher com suas credenciais:

#### a) Credenciais do Agente Plow (`plow-credentials`)
Copie o template de credenciais do Plow e defina a permissão restrita:
```bash
cp plow-credentials.example plow-credentials
chmod 600 plow-credentials
```
Preencha o arquivo com o token do seu agente obtido no CLI do Plow:
```env
PLOW_API_BASE=https://api.plow.co
PLOW_AGENT_TOKEN=seu_token_plow_aqui
```

#### b) Variáveis de Ambiente (.env) — E-mail e GitHub
Copie o template de ambiente:
```bash
cp .env.example .env
```
Edite o arquivo `.env` inserindo suas senhas de aplicativo e token do GitHub:
```env
# Gmail (Senha de App de 16 caracteres gerada na Conta Google)
PLOW_IMAP_GMAIL_USERNAME=seu_email@gmail.com
PLOW_IMAP_GMAIL_PASSWORD=sua_senha_de_app_gmail

# iCloud (Senha de App gerada em appleid.apple.com)
PLOW_IMAP_ICLOUD_USERNAME=seu_email@icloud.com
PLOW_IMAP_ICLOUD_PASSWORD=sua_senha_de_app_icloud

# GitHub Token (com escopos repo, read:org, workflow)
GH_TOKEN=gho_seu_token_github_aqui
GITHUB_TOKEN=gho_seu_token_github_aqui
```

#### c) Conectar o Figma MCP (OAuth)
A autenticação do Figma utiliza o fluxo oficial OAuth. Com o container em execução, conecte via:
```bash
docker exec -it product-developer-assistant-agent-1 hermes mcp auth figma
```
Siga o link exibido no terminal para autorizar no navegador. Os tokens são salvos no volume persistente do agente.

### 4. Instalar o LaunchAgent de Automação (macOS)
Para garantir que tarefas agendadas executem assim que o Mac acordar:
```bash
./image/seed/skills/productivity/automation/macos/install-launchagent.sh
```

### 5. Iniciar o Assistente
Inicie o container do agente em segundo plano:
```bash
docker compose up --build -d
```
Verifique os logs de inicialização:
```bash
docker compose logs -f agent
```

---

## 💬 Exemplos de Uso no Plow Chat

Assim que o agente inicializar, você pode interagir com ele naturalmente em Português no **Plow Chat**:

### 🔍 Pesquisa de Mercado
> *"Faça uma pesquisa de concorrentes sobre ferramentas de prototipação para desenvolvedores. Analise proposta de valor, preços e limitações, e salve um dossiê em Markdown na pasta research."*

### ✍️ Revisão de Documentos
> *"Abra o documento `CBL_Hackathon.pages` na minha Mesa e revise a introdução e os desafios para torná-los mais objetivos e claros."*

### 🎨 Design e Figma
> *"Inspecione o arquivo do projeto no Figma e me dê um resumo dos componentes do Design System e das cores principais definidas nas variáveis."*

### 🐙 Operações no GitHub
> *"Quais pull requests estão aguardando minha revisão no GitHub e quais foram os últimos commits no repositório `product-developer-assistant`?"*

### 📬 Leitura de E-mails
> *"Leia meus e-mails não lidos do Gmail e do iCloud das últimas 24 horas e me dê um resumo apenas do que for importante."*

### 📁 Organização de Pastas
> *"Organize a pasta 'Bagunça' na minha Mesa separando os arquivos em subpastas por tipo: Imagens, Documentos e Scripts."*

### ⏰ Automações Recorrentes
> *"Crie uma automação diária para as 09:00 que verifique minhas issues e PRs no GitHub e me envie um resumo matinal."*

---

## 🧪 Executando a suíte completa de testes

A suíte automatizada cobre inicialização e sanitização do container, configuração Hermes, bridge IMAP, skills e scripts auxiliares. O comando abaixo é o mesmo executado pelo workflow de regressão do GitHub Actions:

```bash
python -m pip install -r requirements-test.txt
python -m pytest -q tests
python -m compileall -q image/s6-overlay/scripts image/seed/skills/productivity/email-reader
```

No ambiente com `uv`, também é possível executar `just test`.

---

## 📄 Licença

Este projeto é licenciado sob os termos da [licença MIT](LICENSE).
