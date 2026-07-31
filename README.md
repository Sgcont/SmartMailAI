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

Para usar geração/tradução por IA com OpenAI:

- Defina `OPENAI_API_KEY` no ambiente **ou** preencha no campo da interface.

## Executar

```bash
python main.py
```

## Converter para `.exe` (PyInstaller)

```bash
pyinstaller --onefile main.py
```
