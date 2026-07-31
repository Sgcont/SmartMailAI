# SmartMail AI

Gere, personalize e envie e-mails profissionais usando Inteligência Artificial.

## Recursos

- Formulário com remetente, senha/app password, destinatário, assunto e objetivo.
- Geração automática de **assunto + mensagem** por IA.
- Edição manual da mensagem antes de enviar.
- Envio via SMTP com `starttls`.
- Templates rápidos:
  - Reclamação, Pedido, Agradecimento, Cobrança, Convite
  - Currículo, Entrevista, Professor, Cliente, Empresa
- Tradução do e-mail para:
  - Inglês, Espanhol, Francês, Alemão
- Histórico local em `historico.json`.

## Requisitos

- Python 3.10+
- Dependências:

```bash
pip install -r requirements.txt
```

## Opções de IA (sem pagar por OpenAI)

O app agora permite escolher o provider de IA na interface:

1. **Ollama (Local grátis)** *(recomendado para uso sem custo por request)*  
   - Instale: https://ollama.com/download  
   - Baixe um modelo (exemplo):
     ```bash
     ollama pull llama3.1:8b
     ```
   - Deixe o Ollama rodando em `http://localhost:11434`.

2. **Gemini (API Key)**  
   - Gere uma chave no Google AI Studio.
   - Preencha no campo `API Key (Gemini)` ou use `GEMINI_API_KEY` / `GOOGLE_API_KEY`.

## Executar

```bash
python main.py
```

## Converter para `.exe` (PyInstaller)

```bash
pyinstaller --onefile main.py
```
