import json
import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk
from urllib import error, request


APP_TITLE = "SmartMail AI"
HISTORY_FILE = Path(__file__).with_name("historico.json")

OLLAMA_PROVIDER = "Ollama (Local grátis)"
GEMINI_PROVIDER = "Gemini (API Key)"
AI_PROVIDERS = (OLLAMA_PROVIDER, GEMINI_PROVIDER)

DEFAULT_MODELS = {
    OLLAMA_PROVIDER: "llama3.1:8b",
    GEMINI_PROVIDER: "gemini-1.5-flash",
}

STYLE_GUIDE = {
    "Formal": "Tom formal, respeitoso e objetivo.",
    "Profissional": "Tom profissional, claro e direto.",
    "Amigável": "Tom amigável, humano e acolhedor.",
    "Acadêmico": "Tom acadêmico, preciso e estruturado.",
    "Cobrança": "Tom firme de cobrança, mas educado e legalmente adequado.",
    "Marketing": "Tom persuasivo de marketing, com linguagem clara e foco em conversão.",
}

TEMPLATES = {
    "Reclamação": "Quero fazer uma reclamação clara sobre um serviço/produto e solicitar solução.",
    "Pedido": "Quero fazer um pedido formal e informar os detalhes necessários.",
    "Agradecimento": "Quero agradecer a oportunidade e reforçar meu interesse.",
    "Cobrança": "Quero cobrar um pagamento pendente com prazo e cordialidade.",
    "Convite": "Quero convidar uma pessoa/empresa para um evento ou reunião.",
    "Currículo": "Quero enviar meu currículo e me apresentar para uma vaga.",
    "Entrevista": "Quero agradecer uma empresa pela entrevista e reforçar meu interesse.",
    "Professor": "Quero enviar uma mensagem respeitosa para um professor com minha solicitação.",
    "Cliente": "Quero enviar um e-mail profissional para um cliente.",
    "Empresa": "Quero enviar um e-mail institucional para uma empresa.",
}

TRANSLATION_TARGETS = {
    "Inglês": "English",
    "Espanhol": "Spanish",
    "Francês": "French",
    "Alemão": "German",
}

SMTP_PRESETS = {
    "gmail.com": ("smtp.gmail.com", 587),
    "outlook.com": ("smtp.office365.com", 587),
    "hotmail.com": ("smtp.office365.com", 587),
    "live.com": ("smtp.office365.com", 587),
    "yahoo.com": ("smtp.mail.yahoo.com", 587),
    "icloud.com": ("smtp.mail.me.com", 587),
}


def strip_markdown_code_fence(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


def parse_json_from_model_text(raw: str) -> dict:
    cleaned = strip_markdown_code_fence(raw)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("A resposta da IA não veio em JSON válido.") from None
        parsed = json.loads(cleaned[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("A resposta da IA não veio em formato de objeto JSON.")
    return parsed


def generate_fallback_email(
    sender_name: str,
    recipient_email: str,
    objective: str,
    style: str,
    custom_subject: str,
) -> tuple[str, str]:
    recipient_label = recipient_email.split("@")[0].replace(".", " ").title()
    subject = custom_subject.strip() or f"{objective.strip()[:60].rstrip('.! ')}"
    if not subject:
        subject = "Contato"

    opening = {
        "Formal": f"Prezado(a) {recipient_label},",
        "Profissional": f"Olá {recipient_label},",
        "Amigável": f"Oi {recipient_label},",
        "Acadêmico": f"Prezado(a) {recipient_label},",
        "Cobrança": f"Olá {recipient_label},",
        "Marketing": f"Olá {recipient_label},",
    }.get(style, f"Olá {recipient_label},")

    body = (
        f"{opening}\n\n"
        f"Escrevo para {objective.strip().lower()}.\n\n"
        "Fico à disposição para quaisquer esclarecimentos e próximos passos.\n\n"
        f"Atenciosamente,\n{sender_name}"
    )
    return subject, body


class SmartMailApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1080x790")
        self.minsize(960, 700)
        self.configure(padx=14, pady=14)

        self.sender_name_var = tk.StringVar()
        self.sender_email_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.recipient_var = tk.StringVar()
        self.subject_var = tk.StringVar()
        self.style_var = tk.StringVar(value="Profissional")
        self.smtp_server_var = tk.StringVar(value="smtp.gmail.com")
        self.smtp_port_var = tk.StringVar(value="587")
        self.ai_provider_var = tk.StringVar(value=OLLAMA_PROVIDER)
        self.ai_model_var = tk.StringVar(value=DEFAULT_MODELS[OLLAMA_PROVIDER])
        self.ai_api_key_var = tk.StringVar(
            value=os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")
        )
        self.ollama_url_var = tk.StringVar(value="http://localhost:11434")

        self._build_ui()

    def _build_ui(self) -> None:
        ttk.Label(self, text=APP_TITLE, font=("Segoe UI", 20, "bold")).pack(anchor="w", pady=(0, 10))
        ttk.Label(
            self,
            text="Gere, personalize e envie e-mails profissionais usando Inteligência Artificial.",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(0, 14))

        top_frame = ttk.Frame(self)
        top_frame.pack(fill="x")

        form = ttk.LabelFrame(top_frame, text="Dados do envio")
        form.pack(side="left", fill="both", expand=True, padx=(0, 8))

        self._add_labeled_entry(form, "Nome do remetente", self.sender_name_var, 0)
        sender_entry = self._add_labeled_entry(form, "Email do remetente", self.sender_email_var, 1)
        sender_entry.bind("<FocusOut>", self._auto_fill_smtp)
        self._add_labeled_entry(form, "Senha / App Password", self.password_var, 2, show="*")
        self._add_labeled_entry(form, "Destinatário", self.recipient_var, 3)
        self._add_labeled_entry(form, "Assunto (opcional)", self.subject_var, 4)
        self._add_labeled_entry(form, "SMTP Server", self.smtp_server_var, 5)
        self._add_labeled_entry(form, "SMTP Port", self.smtp_port_var, 6)
        self._add_labeled_combobox(form, "IA Provider", self.ai_provider_var, list(AI_PROVIDERS), 7)
        self._add_labeled_entry(form, "Modelo IA", self.ai_model_var, 8)
        self._add_labeled_entry(form, "API Key (Gemini)", self.ai_api_key_var, 9, show="*")
        self._add_labeled_entry(form, "Ollama URL", self.ollama_url_var, 10)
        self.ai_provider_var.trace_add("write", self._on_provider_change)

        objective_frame = ttk.LabelFrame(top_frame, text="Objetivo do e-mail")
        objective_frame.pack(side="right", fill="both", expand=True)

        self.objective_text = tk.Text(objective_frame, height=12, wrap="word")
        self.objective_text.pack(fill="both", expand=True, padx=8, pady=8)

        template_frame = ttk.LabelFrame(self, text="Templates rápidos")
        template_frame.pack(fill="x", pady=(10, 0))
        for idx, (name, value) in enumerate(TEMPLATES.items()):
            ttk.Button(
                template_frame,
                text=name,
                command=lambda content=value: self._set_template(content),
            ).grid(row=idx // 5, column=idx % 5, padx=4, pady=4, sticky="ew")
        for col in range(5):
            template_frame.columnconfigure(col, weight=1)

        style_frame = ttk.LabelFrame(self, text="Estilo")
        style_frame.pack(fill="x", pady=(10, 0))
        for idx, style in enumerate(STYLE_GUIDE.keys()):
            ttk.Radiobutton(style_frame, text=style, value=style, variable=self.style_var).grid(
                row=0, column=idx, padx=8, pady=8, sticky="w"
            )

        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=(12, 6))
        ttk.Button(actions, text="Gerar Email", command=self.generate_email).pack(side="left")
        ttk.Button(actions, text="Enviar Email", command=self.send_email).pack(side="left", padx=8)
        ttk.Button(actions, text="Ver histórico", command=self.show_history).pack(side="left")

        translation_frame = ttk.LabelFrame(self, text="Traduzir para")
        translation_frame.pack(fill="x", pady=(0, 6))
        for idx, lang_pt in enumerate(TRANSLATION_TARGETS.keys()):
            ttk.Button(
                translation_frame,
                text=lang_pt,
                command=lambda l=lang_pt: self.translate_generated_email(l),
            ).grid(row=0, column=idx, padx=8, pady=8, sticky="w")

        result_frame = ttk.LabelFrame(self, text="Mensagem gerada (editável)")
        result_frame.pack(fill="both", expand=True)
        self.generated_text = tk.Text(result_frame, height=15, wrap="word")
        self.generated_text.pack(fill="both", expand=True, padx=8, pady=8)

    @staticmethod
    def _add_labeled_entry(
        parent: ttk.LabelFrame,
        label: str,
        variable: tk.StringVar,
        row: int,
        show: str | None = None,
    ) -> ttk.Entry:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=8, pady=(6, 2))
        entry = ttk.Entry(parent, textvariable=variable, show=show if show else "")
        entry.grid(row=row, column=1, sticky="ew", padx=8, pady=(0, 6))
        parent.columnconfigure(1, weight=1)
        return entry

    @staticmethod
    def _add_labeled_combobox(
        parent: ttk.LabelFrame,
        label: str,
        variable: tk.StringVar,
        values: list[str],
        row: int,
    ) -> ttk.Combobox:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=8, pady=(6, 2))
        combo = ttk.Combobox(parent, textvariable=variable, values=values, state="readonly")
        combo.grid(row=row, column=1, sticky="ew", padx=8, pady=(0, 6))
        parent.columnconfigure(1, weight=1)
        return combo

    def _on_provider_change(self, *_args) -> None:
        provider = self.ai_provider_var.get()
        self.ai_model_var.set(DEFAULT_MODELS.get(provider, self.ai_model_var.get()))

    def _set_template(self, content: str) -> None:
        self.objective_text.delete("1.0", "end")
        self.objective_text.insert("1.0", content)

    def _auto_fill_smtp(self, _event=None) -> None:
        email = self.sender_email_var.get().strip().lower()
        if "@" not in email:
            return
        domain = email.split("@", 1)[1]
        preset = SMTP_PRESETS.get(domain)
        if preset:
            self.smtp_server_var.set(preset[0])
            self.smtp_port_var.set(str(preset[1]))

    def _build_generation_prompt(self) -> str:
        objective = self.objective_text.get("1.0", "end").strip()
        return (
            f"Nome do remetente: {self.sender_name_var.get().strip()}\n"
            f"Destinatário: {self.recipient_var.get().strip()}\n"
            f"Assunto informado pelo usuário: {self.subject_var.get().strip() or '(crie o assunto)'}\n"
            f"Objetivo do e-mail: {objective}\n"
            f"Estilo desejado: {self.style_var.get().strip()} ({STYLE_GUIDE.get(self.style_var.get().strip(), '')})\n\n"
            "Responda exclusivamente em JSON válido no formato:\n"
            '{"subject":"...", "body":"..."}\n'
            "O corpo deve vir pronto para envio, com saudação, conteúdo e fechamento."
        )

    @staticmethod
    def _http_post_json(url: str, payload: dict, timeout_seconds: int = 45) -> dict:
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url=url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=timeout_seconds) as response:
                data = response.read().decode("utf-8")
        except error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            raise ValueError(f"HTTP {exc.code}: {raw}") from None
        except error.URLError as exc:
            raise ValueError(f"Falha de conexão: {exc.reason}") from None
        try:
            parsed = json.loads(data)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Resposta inválida da IA: {exc}") from None
        if not isinstance(parsed, dict):
            raise ValueError("Resposta da IA não veio em formato JSON de objeto.")
        return parsed

    def _call_ollama(self, system_prompt: str, user_prompt: str) -> str:
        model = self.ai_model_var.get().strip() or DEFAULT_MODELS[OLLAMA_PROVIDER]
        base_url = self.ollama_url_var.get().strip().rstrip("/")
        if not base_url:
            base_url = "http://localhost:11434"

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {"temperature": 0.6},
        }
        data = self._http_post_json(f"{base_url}/api/chat", payload)
        if data.get("error"):
            raise ValueError(f"Ollama retornou erro: {data['error']}")
        message = data.get("message")
        if not isinstance(message, dict):
            raise ValueError("Resposta do Ollama sem campo 'message'.")
        content = (message.get("content") or "").strip()
        if not content:
            raise ValueError("Resposta do Ollama vazia.")
        return content

    def _call_gemini(self, system_prompt: str, user_prompt: str) -> str:
        api_key = (
            self.ai_api_key_var.get().strip()
            or os.getenv("GEMINI_API_KEY", "").strip()
            or os.getenv("GOOGLE_API_KEY", "").strip()
        )
        if not api_key:
            raise ValueError("API Key do Gemini não configurada.")

        model = self.ai_model_var.get().strip() or DEFAULT_MODELS[GEMINI_PROVIDER]
        prompt = f"SYSTEM:\n{system_prompt}\n\nUSER:\n{user_prompt}"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.6},
        }
        data = self._http_post_json(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
            payload,
        )
        candidates = data.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise ValueError(f"Resposta do Gemini sem candidates: {data}")
        first = candidates[0]
        content = first.get("content") if isinstance(first, dict) else None
        parts = content.get("parts") if isinstance(content, dict) else None
        if not isinstance(parts, list) or not parts:
            raise ValueError("Resposta do Gemini sem parts.")
        text_parts = [p.get("text", "") for p in parts if isinstance(p, dict)]
        result = "\n".join(part for part in text_parts if part).strip()
        if not result:
            raise ValueError("Resposta do Gemini vazia.")
        return result

    def _call_ai(self, system_prompt: str, user_prompt: str) -> str:
        provider = self.ai_provider_var.get().strip()
        if provider == OLLAMA_PROVIDER:
            return self._call_ollama(system_prompt, user_prompt)
        if provider == GEMINI_PROVIDER:
            return self._call_gemini(system_prompt, user_prompt)
        raise ValueError("Provider de IA não suportado.")

    def generate_email(self) -> None:
        sender_name = self.sender_name_var.get().strip()
        sender_email = self.sender_email_var.get().strip()
        recipient = self.recipient_var.get().strip()
        objective = self.objective_text.get("1.0", "end").strip()
        style = self.style_var.get().strip()
        subject_input = self.subject_var.get().strip()

        if not sender_name or not sender_email or not recipient or not objective:
            messagebox.showwarning(
                APP_TITLE,
                "Preencha nome, e-mail do remetente, destinatário e objetivo.",
            )
            return

        generated_subject = ""
        generated_body = ""
        error_message = ""

        try:
            raw = self._call_ai(
                system_prompt=(
                    "Você é um assistente especialista em redação de e-mails profissionais."
                    " Siga exatamente o idioma do pedido (pt-BR por padrão)."
                ),
                user_prompt=self._build_generation_prompt(),
            )
            parsed = parse_json_from_model_text(raw)
            generated_subject = (parsed.get("subject") or "").strip()
            generated_body = (parsed.get("body") or "").strip()
        except Exception as exc:
            error_message = str(exc)

        if not generated_subject or not generated_body:
            generated_subject, generated_body = generate_fallback_email(
                sender_name=sender_name,
                recipient_email=recipient,
                objective=objective,
                style=style,
                custom_subject=subject_input,
            )
            if error_message:
                messagebox.showinfo(
                    APP_TITLE,
                    "Não foi possível usar a IA neste momento. Um e-mail base foi gerado automaticamente.\n\n"
                    f"Detalhe: {error_message}",
                )

        self.subject_var.set(generated_subject)
        self.generated_text.delete("1.0", "end")
        self.generated_text.insert("1.0", generated_body)

    def translate_generated_email(self, language_pt: str) -> None:
        body = self.generated_text.get("1.0", "end").strip()
        subject = self.subject_var.get().strip()
        if not body:
            messagebox.showwarning(APP_TITLE, "Gere ou escreva uma mensagem antes de traduzir.")
            return

        target_language = TRANSLATION_TARGETS.get(language_pt)
        if not target_language:
            messagebox.showerror(APP_TITLE, "Idioma de tradução não suportado.")
            return

        try:
            prompt = (
                f"Traduza o assunto e corpo abaixo para {target_language}.\n"
                "Mantenha tom, intenção, nomes e estrutura profissional.\n"
                "Retorne JSON válido no formato:\n"
                '{"subject":"...", "body":"..."}\n\n'
                f"Assunto:\n{subject}\n\n"
                f"Corpo:\n{body}"
            )
            raw = self._call_ai(
                system_prompt="Você é um tradutor profissional de e-mails corporativos.",
                user_prompt=prompt,
            )
            parsed = parse_json_from_model_text(raw)
            translated_subject = (parsed.get("subject") or "").strip()
            translated_body = (parsed.get("body") or "").strip()
            if not translated_subject or not translated_body:
                raise ValueError("A IA não retornou subject/body válidos.")

            self.subject_var.set(translated_subject)
            self.generated_text.delete("1.0", "end")
            self.generated_text.insert("1.0", translated_body)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Falha ao traduzir: {exc}")

    @staticmethod
    def _load_history() -> list[dict]:
        if not HISTORY_FILE.exists():
            return []
        with HISTORY_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                return []
            return data

    @staticmethod
    def _save_history(entry: dict) -> None:
        history = SmartMailApp._load_history()
        history.append(entry)
        with HISTORY_FILE.open("w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

    def send_email(self) -> None:
        sender_name = self.sender_name_var.get().strip()
        sender_email = self.sender_email_var.get().strip()
        password = self.password_var.get().strip()
        recipient = self.recipient_var.get().strip()
        subject = self.subject_var.get().strip()
        body = self.generated_text.get("1.0", "end").strip()
        smtp_server = self.smtp_server_var.get().strip()
        smtp_port_raw = self.smtp_port_var.get().strip()
        objective = self.objective_text.get("1.0", "end").strip()
        style = self.style_var.get().strip()

        if not sender_name or not sender_email or not password:
            messagebox.showwarning(APP_TITLE, "Preencha remetente, e-mail e senha/App Password.")
            return
        if not recipient or not subject or not body:
            messagebox.showwarning(APP_TITLE, "Preencha destinatário, assunto e mensagem.")
            return
        if not smtp_server or not smtp_port_raw:
            messagebox.showwarning(APP_TITLE, "Preencha SMTP Server e SMTP Port.")
            return
        try:
            smtp_port = int(smtp_port_raw)
        except ValueError:
            messagebox.showerror(APP_TITLE, "SMTP Port deve ser um número inteiro.")
            return

        msg = EmailMessage()
        msg["From"] = f"{sender_name} <{sender_email}>"
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.set_content(body)

        try:
            with smtplib.SMTP(smtp_server, smtp_port, timeout=20) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(sender_email, password)
                server.send_message(msg)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Falha ao enviar e-mail: {exc}")
            return

        SmartMailApp._save_history(
            {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "sender_name": sender_name,
                "sender_email": sender_email,
                "recipient": recipient,
                "subject": subject,
                "objective": objective,
                "style": style,
                "body": body,
                "smtp_server": smtp_server,
                "smtp_port": smtp_port,
                "ai_provider": self.ai_provider_var.get().strip(),
                "ai_model": self.ai_model_var.get().strip(),
            }
        )
        messagebox.showinfo(APP_TITLE, "E-mail enviado com sucesso.")

    def show_history(self) -> None:
        history = self._load_history()
        window = tk.Toplevel(self)
        window.title("Histórico de e-mails")
        window.geometry("860x520")

        columns = ("timestamp", "recipient", "subject")
        tree = ttk.Treeview(window, columns=columns, show="headings")
        tree.heading("timestamp", text="Data/Hora")
        tree.heading("recipient", text="Destinatário")
        tree.heading("subject", text="Assunto")
        tree.column("timestamp", width=170, anchor="w")
        tree.column("recipient", width=210, anchor="w")
        tree.column("subject", width=440, anchor="w")
        tree.pack(fill="both", expand=True, padx=8, pady=8)

        details = tk.Text(window, height=8, wrap="word")
        details.pack(fill="both", expand=False, padx=8, pady=(0, 8))

        reversed_history = list(reversed(history))
        for idx, item in enumerate(reversed_history):
            tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(
                    item.get("timestamp", ""),
                    item.get("recipient", ""),
                    item.get("subject", ""),
                ),
            )

        def on_select(_event=None):
            selected = tree.selection()
            if not selected:
                return
            selected_idx = int(selected[0])
            real_item = reversed_history[selected_idx]
            details.delete("1.0", "end")
            details.insert(
                "1.0",
                f"Objetivo: {real_item.get('objective', '')}\n"
                f"Estilo: {real_item.get('style', '')}\n"
                f"Provider IA: {real_item.get('ai_provider', '')}\n"
                f"Modelo IA: {real_item.get('ai_model', '')}\n"
                f"Mensagem:\n{real_item.get('body', '')}",
            )

        tree.bind("<<TreeviewSelect>>", on_select)


if __name__ == "__main__":
    app = SmartMailApp()
    app.mainloop()
