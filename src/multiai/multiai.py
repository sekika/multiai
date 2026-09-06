"""
multiai - A Python library for text-based AI interactions with multi-provider support.
"""
import anthropic
from anthropic.types import TextBlock
import base64
import configparser
from dataclasses import dataclass, field
from datetime import datetime
import enum
from google import genai
import json
import mimetypes
import ollama
import openai
import os
import re
import mistralai
import pypdf
import pyperclip
import requests
import sys
import trafilatura
from io import BytesIO
from importlib.metadata import distribution, PackageNotFoundError
from typing import Any, Dict, List, Optional
from .printlong import print_long
import docx  # python-docx
from docx import Document

__all__ = [
    "Prompt",
    "Provider",
    "ColorCode",
    "ResponseAttachment",
]


@dataclass
class ResponseAttachment:
    """
    Attachment returned by an AI response.
    """
    id: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    name: Optional[str] = None
    mime_type: Optional[str] = None
    extension: Optional[str] = None
    size: Optional[int] = None
    data: Optional[bytes] = None
    text: Optional[str] = None
    url: Optional[str] = None
    file_id: Optional[str] = None
    source_type: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)
    saved_path: Optional[str] = None
    created_at: str = field(
        default_factory=lambda: datetime.now().isoformat(
            timespec="seconds"))


class Prompt():
    """
    The Prompt main application.

    Usage:
        client = Prompt()
        answer = client.ask(prompt)
    """

    def __init__(self):
        # Values independent of system or user setting file
        self.role = 'user'
        # Anthropic requires max_tokens, so default value is given.
        # It can be overwritten by max_tokens.
        self.max_tokens_anthropic = 4096
        self.ai_providers = []
        # Load package data
        try:
            dist = distribution('multiai')
            self.version = dist.version
            md = dist.metadata  # email.message.Message
            # Project-URL: Homepage, https://... or Home-page
            self.description = (md.get('Summary') or '').strip()
            self.url = None
            for item in md.get_all('Project-URL') or []:
                label, _, link = item.partition(', ')
                if label.strip().lower() == 'homepage' and link:
                    self.url = link.strip()
                    break
            if not self.url:
                self.url = (md.get('Home-page') or '').strip() or None
        except PackageNotFoundError:
            self.version = None
            self.description = None
            self.url = None
        # Load user setting from config file in the order of
        # data/system.ini, ~/.multiai, .multai
        # It overwrites the system default values
        inifile = configparser.ConfigParser()
        here = os.path.abspath(os.path.dirname(__file__))
        inifile.read(os.path.join(here, 'data/system.ini'))
        conf_file = os.path.expanduser('~/.multiai')
        inifile.read(conf_file)
        inifile.read('.multiai')
        self.set_provider(inifile.get('model', 'ai_provider'))
        for provider in Provider:
            name = provider.name.lower()
            model = inifile.get('model', name, fallback=None)
            if model is None:
                print(f'multiai system error: {name} not found in [model].')
                sys.exit(1)
            setattr(self, 'model_' + name, model)
        self.temperature = inifile.getfloat('default', 'temperature')
        self.max_requests = inifile.getint('default', 'max_requests')
        self.blank_lines = inifile.getint('command', 'blank_lines')
        prompt_color = inifile.get('prompt', 'color')
        self.always_copy = inifile.getboolean('command', 'always_copy')
        self.copy = self.always_copy
        self.always_log = inifile.getboolean('command', 'always_copy')
        self.log = self.always_log
        try:
            self.prompt_color = ColorCode[prompt_color.upper()].value
        except Exception:
            print(f'Error in the settings file: color = {prompt_color}')
            available_colors = [name.lower()
                                for name in ColorCode.__members__.keys()]
            print(f'Available colors: {", ".join(available_colors)}')
            sys.exit(1)
        # No system default value is given from here.
        # Default values are given by fallback values.
        self.max_tokens = inifile.getint(
            'default', 'max_tokens', fallback=None)

        # From version 1.4.0: attachment character limit (per attachment)
        self.attach_char_limit = inifile.getint(
            'default', 'attach_char_limit', fallback=40000)

        # Response attachment directory
        self.response_attachment_dir = os.path.expanduser(
            inifile.get(
                'response_attachment',
                'directory',
                fallback='./multiai_attachments'
            )
        )

        for provider in Provider:
            env = os.getenv(provider.name + '_API_KEY')
            name = provider.name.lower()
            key = name + '_api_key'
            if env is None:
                ini = inifile.get('api_key', name, fallback=None)
                setattr(self, key, ini)
            else:
                setattr(self, key, env)

        # --- Azure TTS (not part of Provider) ---
        # Azure Text-to-Speech uses Azure Speech Services, which is a separate service
        # from Azure OpenAI. It requires its own dedicated API key and region.
        # The Azure OpenAI API key cannot be used for Speech (TTS/STT), so we load
        # the Speech-specific key explicitly and keep it independent from LLM
        # providers.

        # API key
        env = os.getenv('AZURE_TTS_API_KEY')
        if env is None:
            self.azure_tts_api_key = inifile.get(
                'api_key', 'azure_tts', fallback=None)
        else:
            self.azure_tts_api_key = env

        # region
        env = os.getenv('AZURE_TTS_REGION')
        if env is None:
            self.azure_tts_region = inifile.get(
                'azure_tts', 'region', fallback=None)
        else:
            self.azure_tts_region = env

        self.clear()

    def set_provider(self, provider):
        """
        Set AI provider.

        :param provider: str
            AI provider (case insensitive)
        """
        try:
            self.ai_provider = Provider[provider.upper()]
        except Exception:
            print(f'AI provider "{provider}" is not available.')
            sys.exit(1)

    def set_model(self, provider, model):
        """
        Set model.

        :param provider: str
            AI provider (case insensitive)
        :param model: str
            AI model
        """
        self.set_provider(provider)
        self.model = model
        setattr(self, 'model_' + provider.lower(), model)

    @staticmethod
    def _openai_supports_temperature(model):
        """Return whether an OpenAI chat model supports ``temperature``.

        GPT-5 and newer GPT models, plus the o-series reasoning models, do not
        accept a caller-supplied temperature. Keep older GPT models compatible
        while treating future GPT generations conservatively.
        """
        if model.startswith('o'):
            return False
        match = re.match(r'^gpt-(\d+)', model)
        return not (match and int(match.group(1)) >= 5)

    def clear(self):
        """
        Clear chat history.
        """
        self.openai_messages = []
        self.anthropic_messages = []
        self.google_messages = []
        self.perplexity_messages = []
        self.deepseek_messages = []
        self.mistral_messages = []
        self.xai_messages = []
        self.local_messages = []
        self.response_attachments = []

    def ask(self, prompt, request=1, verbose=False):
        """
        Ask a question to AI.

        :param prompt: str
            Prompt to ask AI
        :param request: int
            Numbers of repetitive requests when the response is cut by token limit
        :param verbose: bool
            Show repeat process
        :return: str
            Answer from AI
        """
        if request == 1:
            self.response_attachments = []
        self.message = [
            {
                "role": self.role,
                "content": prompt,
            }
        ]
        self.prompt = prompt
        if request == 1:
            self.prompt_continue = False
        else:
            self.prompt_continue = True
        # For example, call ask_openai() for openai
        func_name = 'ask_' + self.ai_provider.name.lower()
        try:
            func = getattr(self, func_name)
        except AttributeError:
            print(
                f'multiai system error: {func_name}() function is not defined.')
            sys.exit(1)
        func()
        # Error
        if self.error:
            return self.error_message
        # Finish successfully
        if self.finish_reason in ['stop', 'end_turn']:
            return self.response
        # Unexpected finish reason
        if self.finish_reason not in ['length', 'max_tokens']:
            self.response += f'\n\nFinish reason: {self.finish_reason}'
            return self.response
        # Response not finished. Continue the request.
        request += 1
        if request > self.max_requests:
            self.response += '\n\nFinished because of max_tokens and max_requests.'
            return self.response
        if verbose:
            msg = f'{self.color("Repeating...")} max_requests={self.max_requests}, requests={request}'
            print(f'{msg}\r', end='')
        response = self.response
        answer = self.ask('continue', request=request, verbose=verbose)
        if self.error:
            return answer
        return response + answer

    def ask_once(self, prompt):
        """
        Ask a single-turn question without polluting the chat history.

        This calls the same provider but restores all internal message lists
        after the request completes.

        :param prompt: str
            Prompt to ask AI
        :return: str
            Answer from AI
        """
        # Backup histories
        backups = {
            'openai_messages': list(self.openai_messages),
            'anthropic_messages': list(self.anthropic_messages),
            'google_messages': list(self.google_messages),
            'perplexity_messages': list(self.perplexity_messages),
            'deepseek_messages': list(self.deepseek_messages),
            'mistral_messages': list(self.mistral_messages),
            'xai_messages': list(self.xai_messages),
            'local_messages': list(self.local_messages),
        }
        # Ask
        answer = self.ask(prompt)
        # Restore histories regardless of error
        self.openai_messages = backups['openai_messages']
        self.anthropic_messages = backups['anthropic_messages']
        self.google_messages = backups['google_messages']
        self.perplexity_messages = backups['perplexity_messages']
        self.deepseek_messages = backups['deepseek_messages']
        self.mistral_messages = backups['mistral_messages']
        self.xai_messages = backups['xai_messages']
        self.local_messages = backups['local_messages']
        return answer

    def summarize_text(self, text, max_words_hint=600):
        """
        Summarize a long piece of text.

        Uses ask_once() to avoid altering conversation history.

        :param text: str
            Raw text to summarize
        :param max_words_hint: int
            A rough upper bound to guide the summary length
        :return: str
            Summarized text (best-effort)
        """
        prompt = (
            "Summarize the following content concisely. Preserve key facts, structure, and any code blocks. "
            f"Target up to roughly {max_words_hint} words. Do not include commentary about being an AI.\n\n"
            "Content begins below:\n\n"
            f"{text}"
        )
        return self.ask_once(prompt)

    def ask_print(self, prompt, prompt_summary=None):
        """
        Ask a question to AI and print, copy, log.

        :param prompt: str
            Prompt to ask AI
        :param prompt_summary: str
            Prompt shortened for logging
        """
        print(f'{self.color("Please wait ......")}\r', end='')
        saved_paths = []
        attachment_urls = []
        failed_attachments = []
        if len(self.ai_providers) == 1:
            answer = self.ask(prompt, verbose=True)
            attachments = list(self.response_attachments)
            saved_paths, attachment_urls, failed_attachments = \
                self._save_response_attachments_for_cli(attachments)
            print(' ' * 50 + '\r', end='')
            if self.error:
                print(f'{self.color("Error message")}> {answer}')
                sys.exit(1)
            print(f'{self.color(self.model)}>')
            if self.log:
                if prompt_summary is not None:
                    prompt = prompt_summary
                try:
                    with open(self.log_file, mode='a') as f:
                        f.write(
                            f'### {self.role}:\n{prompt}\n### {self.model}:\n{answer}\n')
                        f.write(self._response_attachment_log(
                            saved_paths, attachment_urls, failed_attachments))
                except Exception as e:
                    print(e)
                    print('Check the setting of log_file.')
                    sys.exit(1)
        else:
            answer = ''
            if prompt_summary is None:
                prompt_log = prompt
            else:
                prompt_log = prompt_summary
            for provider in (self.ai_providers):
                self.ai_provider = provider
                single_answer = self.ask(prompt, verbose=True)
                attachments = list(self.response_attachments)
                s, u, f = self._save_response_attachments_for_cli(
                    attachments, provider=provider.name.lower())
                saved_paths += s
                attachment_urls += u
                failed_attachments += f
                model = getattr(self, 'model_' + provider.name.lower(), None)
                if self.error:
                    print(
                        f'{self.color("Error message from " + provider.name.lower())}> {single_answer}')
                    sys.exit(1)
                answer += f'### {model}:\n{single_answer}\n\n'
            answer = answer.strip()
            if self.log:
                with open(self.log_file, mode='a') as f:
                    f.write(
                        f'### {self.role}:\n{prompt_log}\n{answer}\n')
                    f.write(self._response_attachment_log(
                        saved_paths, attachment_urls, failed_attachments))
        print(' ' * 50 + '\r', end='')
        print_long(answer)
        self._print_response_attachment_summary(
            saved_paths, attachment_urls, failed_attachments)
        if self.copy:
            pyperclip.copy(answer)

    def interactive(self, pre_prompt=''):
        """
        Interactive mode.

        :param pre_prompt: str
            Pre-prompt to append before prompt
        """
        prompt = ''
        blank = 0
        b = self.blank_lines
        if len(self.ai_providers) == 0:
            self.ai_providers = [self.ai_provider]
        if b > 0:
            print(
                f'\nInput {b} blank line{"s" if b > 1 else ""} to finish input.')
        while True:
            try:
                if prompt == '':
                    line = input(f'{self.color(self.role)}> ')
                else:
                    line = input()
            except EOFError:
                sys.exit()
            except KeyboardInterrupt:
                sys.exit()
            if line == '':
                if prompt == '':
                    print('Blank text entered. Enter "q" to quit.')
                    continue
                blank += 1
                if blank < self.blank_lines:
                    prompt += line + '\n'
                else:
                    self.ask_print(pre_prompt + prompt.strip())
                    prompt = ''
                    blank = 0
            elif prompt == '' and line in ['q', 'x', 'quit', 'exit']:
                sys.exit()
            else:
                if self.blank_lines == 0:
                    self.ask_print(pre_prompt + line)
                    prompt = ''
                else:
                    prompt += line + '\n'
                    blank = 0

    def color(self, text):
        """
        Return colored text with color defined at self.prompt_color.

        :param text: str
            Text
        :return: str
            Colored text (no color if not TTY)
        """
        if sys.stdout.isatty():
            return f'\033[{self.prompt_color}m{text}\033[0m'
        else:
            return text

    def retrieve_from_url(self, url, verbose=True):
        """
        Retrieve text from URL.

        When URL ends with ".pdf", PDF file is converted to text.

        :param url: str
            URL to retrieve data from
        :param verbose: bool
            Whether to print message
        :return: str
            Retrieved text
        """
        if verbose:
            print('Retrieving ...\r', end='')
        headers = {
            'User-Agent': self.user_agent if hasattr(self, 'user_agent') else None}
        try:
            response = requests.get(url, headers=headers)
        except Exception as e:
            if verbose:
                print(e)
            sys.exit(1)
        if response.status_code != 200:
            if verbose:
                print(f'{response.status_code} - {response.reason}')
            sys.exit(1)
        if verbose:
            print('Converting to text.\r', end='')
        if url.lower().endswith('.pdf'):
            with BytesIO(response.content) as pdf_file:
                reader = pypdf.PdfReader(pdf_file)
                text = ""
                for page in range(len(reader.pages)):
                    text += reader.pages[page].extract_text()
        else:
            text = trafilatura.extract(response.text)
            if text is None:
                if verbose:
                    print(f'{url} could not be retrieved.')
                sys.exit(1)
        return text

    def retrieve_from_file(self, source, filename=None, verbose=True):
        """
        Retrieve text from a file path or bytes.

        Supported extensions (special handling): txt, md, pdf, docx, html/htm, csv.
        For unknown extensions, if the content is valid UTF-8 text (no NUL bytes and UTF-8 decodable),
        it will be treated as plain text; otherwise an error is raised.

        :param source: str | bytes | file-like
            File path (str) or in-memory bytes (e.g., from upload).
        :param filename: str | None
            Original file name (used for extension detection and messages).
        :param verbose: bool
            Whether to print progress messages
        :return: str
            Extracted text
        """
        def _ext_from_name(name):
            return os.path.splitext(name)[1].lower()

        # Determine extension and load bytes
        if isinstance(source, (str, os.PathLike)):
            path = os.fspath(source)
            ext = _ext_from_name(path)
            if verbose:
                print('Reading file ...\r', end='')
            with open(path, 'rb') as f:
                data = f.read()
            name = os.path.basename(path)
        else:
            # in-memory data
            if hasattr(source, 'read'):
                data = source.read()
            else:
                data = source
            if not isinstance(data, (bytes, bytearray)):
                print('retrieve_from_file expects bytes/file-like for in-memory data.')
                sys.exit(1)
            if not filename:
                print('filename is required when passing in-memory data.')
                sys.exit(1)
            name = filename
            ext = _ext_from_name(filename)

        if verbose:
            print('Converting file to text.\r', end='')

        try:
            if ext in ['.txt', '.md', '.csv']:
                # Known simple text types: decode as UTF-8 (replace errors to
                # avoid crash)
                text = data.decode('utf-8', errors='replace')

            elif ext == '.pdf':
                with BytesIO(data) as pdf_file:
                    reader = pypdf.PdfReader(pdf_file)
                    text = ""
                    for page in range(len(reader.pages)):
                        text += reader.pages[page].extract_text()

            elif ext == '.docx':
                if Document is None:
                    print('python-docx is not installed. Please install "python-docx".')
                    sys.exit(1)
                with BytesIO(data) as stream:
                    doc = Document(stream)
                    text = "\n".join(p.text for p in doc.paragraphs)

            elif ext in ['.html', '.htm']:
                html = data.decode('utf-8', errors='replace')
                text = trafilatura.extract(html)
                if text is None:
                    print(f'{name} could not be converted from HTML.')
                    sys.exit(1)

            else:
                # Unknown extension: treat as text only if it is valid UTF-8
                # and not binary.
                if b'\x00' in data:
                    print(
                        f'Unsupported file type or binary content detected: {name}')
                    sys.exit(1)
                try:
                    # strict; will fail if not UTF-8
                    text = data.decode('utf-8')
                except UnicodeDecodeError:
                    print(
                        f'{name} is not a supported file format or not UTF-8 text.')
                    sys.exit(1)

        except Exception as e:
            print(f'Failed to parse {name}: {e}')
            sys.exit(1)

        return text

    def save_attachment(self, attachment, filename=None):
        """
        Save a response attachment.

        :param attachment: ResponseAttachment
            Attachment to save
        :param filename: str
            Output file name or path
        :return: str
            Saved file path
        """
        if isinstance(attachment, dict):
            attachment = ResponseAttachment(**attachment)
        if not isinstance(attachment, ResponseAttachment):
            raise TypeError('attachment should be ResponseAttachment.')
        if attachment.data is None and attachment.text is None:
            if attachment.url:
                raise ValueError('URL attachments are not downloaded.')
            raise ValueError('Attachment has no data to save.')

        if filename is None:
            filename = self._attachment_default_filename(attachment, 1)

        filename = os.path.expanduser(filename)
        dirname = os.path.dirname(filename)
        basename = self._sanitize_filename(os.path.basename(filename))
        if dirname:
            path = os.path.join(dirname, basename)
        else:
            path = os.path.join(self.response_attachment_dir, basename)

        directory = os.path.dirname(path) or '.'
        os.makedirs(directory, exist_ok=True)
        path = self._unique_path(path)

        if attachment.data is not None:
            with open(path, 'wb') as f:
                f.write(attachment.data)
        else:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(attachment.text)

        attachment.saved_path = path
        return path

    def save_response_attachments(self, attachments=None):
        """
        Save response attachments with generated file names.

        :param attachments: list[ResponseAttachment]
            Attachments to save
        :return: list[str]
            Saved file paths
        """
        saved_paths, _, _ = self._save_response_attachments_for_cli(
            self.response_attachments if attachments is None else attachments)
        return saved_paths

    def _get_value(self, obj, key, default=None):
        """
        Get a value from dict or object.
        """
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def _decode_attachment_data(self, data):
        """
        Decode inline attachment data.
        """
        if data is None:
            return None
        if isinstance(data, bytes):
            return data
        if isinstance(data, bytearray):
            return bytes(data)
        if isinstance(data, str):
            if data.startswith('data:'):
                m = re.match(r'^data:([^;]+);base64,(.*)$', data, re.S)
                if m:
                    data = m.group(2)
            try:
                return base64.b64decode(data)
            except Exception:
                return data.encode('utf-8')
        return None

    def _extension_from_mime_type(self, mime_type):
        """
        Guess an extension from MIME type.
        """
        if not mime_type:
            return '.bin'
        table = {
            'image/png': '.png',
            'image/jpeg': '.jpg',
            'image/jpg': '.jpg',
            'image/webp': '.webp',
            'application/pdf': '.pdf',
            'text/csv': '.csv',
            'text/plain': '.txt',
            'application/json': '.json',
            'text/html': '.html',
        }
        if mime_type in table:
            return table[mime_type]
        ext = mimetypes.guess_extension(mime_type)
        return ext or '.bin'

    def _sanitize_filename(self, filename):
        """
        Sanitize a file name.
        """
        filename = os.path.basename(filename or '')
        filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', filename)
        filename = filename.strip().strip('.')
        return filename or 'attachment.bin'

    def _unique_path(self, path):
        """
        Return a non-existing path.
        """
        if not os.path.exists(path):
            return path
        root, ext = os.path.splitext(path)
        n = 1
        while True:
            candidate = f'{root}-{n}{ext}'
            if not os.path.exists(candidate):
                return candidate
            n += 1

    def _attachment_default_filename(
            self, attachment, index=1, timestamp=None, provider=None):
        """
        Generate a default attachment file name.
        """
        if timestamp is None:
            timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        name = attachment.name
        if not name:
            ext = attachment.extension or self._extension_from_mime_type(
                attachment.mime_type)
            name = f'attachment-{index}{ext}'
        name = self._sanitize_filename(name)
        if provider:
            return f'{timestamp}-{provider}-{name}'
        return f'{timestamp}-{name}'

    def _add_response_attachment(
            self, provider=None, name=None, mime_type=None, data=None,
            text=None, url=None, file_id=None, source_type='unknown',
            metadata=None):
        """
        Add a response attachment.
        """
        binary = self._decode_attachment_data(data)
        extension = self._extension_from_mime_type(mime_type)
        size = None
        if binary is not None:
            size = len(binary)
        elif text is not None:
            size = len(text.encode('utf-8'))
        attachment = ResponseAttachment(
            id=file_id or url,
            provider=provider,
            model=getattr(
                self,
                'model_' + provider,
                None) if provider else getattr(
                self,
                'model',
                None),
            name=name,
            mime_type=mime_type,
            extension=extension,
            size=size,
            data=binary,
            text=text,
            url=url,
            file_id=file_id,
            source_type=source_type,
            metadata=metadata or {},
        )
        self.response_attachments.append(attachment)
        return attachment

    def _extract_common_parts(self, parts, provider):
        """
        Extract text and attachments from content parts.
        """
        text_chunks = []
        for part in parts or []:
            text = self._get_value(part, 'text')
            if text:
                text_chunks.append(str(text))

            inline_data = self._get_value(part, 'inline_data')
            if inline_data is None:
                inline_data = self._get_value(part, 'inlineData')
            if inline_data is not None:
                mime_type = self._get_value(inline_data, 'mime_type')
                if mime_type is None:
                    mime_type = self._get_value(inline_data, 'mimeType')
                data = self._get_value(inline_data, 'data')
                name = self._get_value(inline_data, 'name')
                self._add_response_attachment(
                    provider=provider,
                    name=name,
                    mime_type=mime_type,
                    data=data,
                    source_type='inline',
                    metadata={'part': str(type(part))}
                )

            file_data = self._get_value(part, 'file_data')
            if file_data is None:
                file_data = self._get_value(part, 'fileData')
            if file_data is not None:
                mime_type = self._get_value(file_data, 'mime_type')
                if mime_type is None:
                    mime_type = self._get_value(file_data, 'mimeType')
                url = self._get_value(file_data, 'file_uri')
                if url is None:
                    url = self._get_value(file_data, 'fileUri')
                if url is None:
                    url = self._get_value(file_data, 'uri')
                name = self._get_value(file_data, 'name')
                file_id = self._get_value(file_data, 'file_id')
                if file_id is None:
                    file_id = self._get_value(file_data, 'fileId')
                self._add_response_attachment(
                    provider=provider,
                    name=name,
                    mime_type=mime_type,
                    url=url,
                    file_id=file_id,
                    source_type='url' if url else 'file_id',
                    metadata={'part': str(type(part))}
                )

            image_url = self._get_value(part, 'image_url')
            if image_url is not None:
                url = self._get_value(image_url, 'url')
                name = self._get_value(image_url, 'name')
                if isinstance(url, str) and url.startswith('data:'):
                    mime_type = None
                    m = re.match(r'^data:([^;]+);base64,', url, re.S)
                    if m:
                        mime_type = m.group(1)
                    self._add_response_attachment(
                        provider=provider,
                        name=name,
                        mime_type=mime_type,
                        data=url,
                        source_type='inline',
                        metadata={'part': str(type(part))}
                    )
                elif url:
                    self._add_response_attachment(
                        provider=provider,
                        name=name,
                        mime_type=self._get_value(image_url, 'mime_type'),
                        url=url,
                        source_type='url',
                        metadata={'part': str(type(part))}
                    )

            url = self._get_value(part, 'url')
            if url and not text:
                self._add_response_attachment(
                    provider=provider,
                    name=self._get_value(part, 'name'),
                    mime_type=self._get_value(part, 'mime_type'),
                    url=url,
                    source_type='url',
                    metadata={'part': str(type(part))}
                )

        return ''.join(text_chunks)

    def _extract_message_text_and_attachments(self, message, provider):
        """
        Extract text and attachments from a chat message.
        """
        content = self._get_value(message, 'content')
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            text = self._extract_common_parts(content, provider)
        else:
            text = '' if content is None else str(content)

        audio = self._get_value(message, 'audio')
        if audio is not None:
            data = self._get_value(audio, 'data')
            url = self._get_value(audio, 'url')
            file_id = self._get_value(audio, 'id')
            self._add_response_attachment(
                provider=provider,
                name=self._get_value(audio, 'name'),
                mime_type=self._get_value(audio, 'mime_type') or 'audio/mpeg',
                data=data,
                url=url,
                file_id=file_id,
                source_type='inline' if data else (
                    'url' if url else 'file_id'),
                metadata={'message_field': 'audio'}
            )

        annotations = self._get_value(message, 'annotations')
        for ann in annotations or []:
            file_path = self._get_value(ann, 'file_path')
            if file_path is not None:
                file_id = self._get_value(file_path, 'file_id')
                self._add_response_attachment(
                    provider=provider,
                    name=self._get_value(file_path, 'filename'),
                    file_id=file_id,
                    source_type='file_id',
                    metadata={'annotation': str(type(ann))}
                )

        return text

    def _extract_anthropic_text_and_attachments(self, content):
        """
        Extract text and attachments from Anthropic content blocks.
        """
        text_chunks = []
        for block in content or []:
            if isinstance(block, TextBlock):
                if block.text is not None:
                    text_chunks.append(block.text)
                continue

            text = self._get_value(block, 'text')
            if text:
                text_chunks.append(str(text))

            source = self._get_value(block, 'source')
            if source is not None:
                data = self._get_value(source, 'data')
                mime_type = self._get_value(source, 'media_type')
                if mime_type is None:
                    mime_type = self._get_value(source, 'mime_type')
                url = self._get_value(source, 'url')
                self._add_response_attachment(
                    provider='anthropic',
                    name=self._get_value(block, 'name'),
                    mime_type=mime_type,
                    data=data,
                    url=url,
                    source_type='inline' if data else (
                        'url' if url else 'unknown'),
                    metadata={'block': str(type(block))}
                )

            file_id = self._get_value(block, 'file_id')
            if file_id:
                self._add_response_attachment(
                    provider='anthropic',
                    name=self._get_value(block, 'name'),
                    file_id=file_id,
                    source_type='file_id',
                    metadata={'block': str(type(block))}
                )

        return ''.join(text_chunks)

    def _save_response_attachments_for_cli(self, attachments, provider=None):
        """
        Save response attachments for command output.
        """
        saved_paths = []
        urls = []
        failed = []
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        for i, attachment in enumerate(attachments or [], start=1):
            if attachment.url and attachment.data is None and attachment.text is None:
                urls.append(attachment.url)
                continue
            try:
                filename = self._attachment_default_filename(
                    attachment, i, timestamp=timestamp, provider=provider)
                saved_paths.append(self.save_attachment(attachment, filename))
            except Exception as e:
                failed.append((attachment, e))
        return saved_paths, urls, failed

    def _print_response_attachment_summary(self, saved_paths, urls, failed):
        """
        Print response attachment summary.
        """
        if saved_paths:
            print('\nResponse attachments saved:')
            for path in saved_paths:
                print(f'- {path}')
        if urls:
            print('\nResponse attachment URLs:')
            for url in urls:
                print(f'- {url}')
        if failed:
            print('\nResponse attachments not saved:')
            for attachment, error in failed:
                name = attachment.name or attachment.file_id or 'attachment'
                print(f'- {name}: {error}')

    def _response_attachment_log(self, saved_paths, urls, failed):
        """
        Return response attachment log text.
        """
        if not saved_paths and not urls and not failed:
            return ''
        lines = ['### response attachments:']
        for path in saved_paths:
            lines.append(f'- saved: {path}')
        for url in urls:
            lines.append(f'- url: {url}')
        for attachment, error in failed:
            name = attachment.name or attachment.file_id or 'attachment'
            lines.append(f'- not saved: {name}: {error}')
        return '\n' + '\n'.join(lines) + '\n'

    # Implementations for each providers
    def ask_openai(self):
        """
        Ask a question to OpenAI.
        """
        if self.openai_api_key is None:
            self.error = True
            self.error_message = 'API key for OpenAI is not set.'
            return
        openai.api_key = self.openai_api_key
        if not self.prompt_continue:
            self.openai_messages += self.message
        try:
            params = {
                'messages': self.openai_messages,
                'model': self.model_openai,
            }
            # ``max_tokens`` is deprecated for recent OpenAI models and is not
            # accepted by reasoning models. Do not send either limit parameter
            # when it is unset: the API expects an integer, not null.
            if self.max_tokens is not None:
                params['max_completion_tokens'] = self.max_tokens
            if self._openai_supports_temperature(self.model):
                params['temperature'] = self.temperature
            self.completion = openai.chat.completions.create(**params)
            self.error = False
            message = self.completion.choices[0].message
            self.response = self._extract_message_text_and_attachments(
                message, 'openai').strip()
            self.finish_reason = self.completion.choices[0].finish_reason
            self.openai_messages += [{"role": "assistant",
                                      "content": self.response}]
        except openai.APIError as e:
            self.error = True
            try:
                self.error_code = e.status_code
                self.error_dict = e.body
                self.error_type = f"Error {self.error_code}: {self.error_dict['code']}"
                self.error_message = f"{self.error_type}\n{self.error_dict['message']}"
            except Exception:
                self.error_message = e

    def ask_anthropic(self):
        """
        Ask a question to Anthropic.
        """
        if self.anthropic_api_key is None:
            self.error = True
            self.error_message = 'API key for Anthropic is not set.'
            return
        client = anthropic.Anthropic(api_key=self.anthropic_api_key)
        if self.anthropic_messages and self.anthropic_messages[-1]['role'] == 'assistant':
            self.anthropic_messages.pop()
        if not self.prompt_continue:
            self.anthropic_messages += self.message
        try:
            # Stream internally to avoid the SDK's default 10-minute timeout on
            # long-running (e.g. reasoning) requests, then take the final
            # message and return the complete text as before.
            if 'haiku' in self.model_anthropic or 'sonnet' in self.model_anthropic:
                stream_ctx = client.messages.stream(
                    messages=self.anthropic_messages,
                    model=self.model_anthropic,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens if self.max_tokens else self.max_tokens_anthropic
                )
            else:
                stream_ctx = client.messages.stream(
                    messages=self.anthropic_messages,
                    model=self.model_anthropic,
                    max_tokens=self.max_tokens if self.max_tokens else self.max_tokens_anthropic
                )
            with stream_ctx as stream:
                self.completion = stream.get_final_message()
            self.error = False
            self.response = self._extract_anthropic_text_and_attachments(
                self.completion.content).strip()
            self.finish_reason = self.completion.stop_reason
            self.anthropic_messages += [{"role": "assistant",
                                         "content": self.response}]
        except Exception as e:
            self.error = True
            try:
                self.error_code = e.status_code
                self.error_dict = e.body['error']
                self.error_type = f"{self.error_code}: {self.error_dict['type']}"
                self.error_message = f"{self.error_type}\n{self.error_dict['message']}"
            except Exception:
                self.error_message = e

    def ask_google(self):
        """
        Ask a question to Google (google.genai).
        """
        # Suppress logging warnings of libraries
        os.environ["GRPC_VERBOSITY"] = "ERROR"
        os.environ["GLOG_minloglevel"] = "2"

        if self.google_api_key is None:
            self.error = True
            self.error_message = 'API key for Google is not set.'
            return

        # google.genai client
        client = genai.Client(api_key=self.google_api_key)

        if not hasattr(self, "google_messages"):
            self.google_messages = []

        if not self.prompt_continue:
            # {"role":"user","content":...}
            self.google_messages += self.message

        contents = []
        for m in self.google_messages:
            role = m.get("role", "user")
            if role == "assistant":
                role = "model"
            elif role == "system":
                role = "user"

            contents.append({
                "role": role,
                "parts": [{"text": m.get("content", "")}],
            })

        # generation config
        config = {}
        if self.temperature is not None:
            config["temperature"] = float(self.temperature)
        if self.max_tokens is not None:
            # google.genai uses max_output_tokens
            config["max_output_tokens"] = int(self.max_tokens)

        try:
            resp = client.models.generate_content(
                model=self.model_google,
                contents=contents,
                config=config if config else None,
            )
            self.error = False

            text = ""
            try:
                cand0 = resp.candidates[0]
                parts = cand0.content.parts
                text = self._extract_common_parts(parts, 'google')
            except Exception:
                pass

            if not text:
                text = getattr(resp, "text", None) or ""

            self.response = (text or "").replace('• ', '* ').strip()

            # finish_reason
            self.finish_reason = "stop"
            try:
                fr = resp.candidates[0].finish_reason
                name = getattr(fr, "name", None)
                if name:
                    self.finish_reason = str(name).lower()
                else:
                    s = str(fr).strip().lower()
                    if "." in s:
                        s = s.split(".")[-1]
                    self.finish_reason = s
            except Exception:
                pass

            self.google_messages += [{"role": "assistant",
                                      "content": self.response}]

        except Exception as e:
            self.error = True
            self.error_message = str(e)

    def ask_perplexity(self):
        """
        Ask a question to perplexity.
        """
        if self.perplexity_api_key is None:
            self.error = True
            self.error_message = 'API key for Perplexity is not set.'
            return
        base_url = 'https://api.perplexity.ai'
        client = openai.OpenAI(
            api_key=self.perplexity_api_key,
            base_url=base_url)
        self.perplexity_messages += self.message
        try:
            self.completion = client.chat.completions.create(
                messages=self.perplexity_messages,
                model=self.model_perplexity,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            self.error = False
            message = self.completion.choices[0].message
            self.response = self._extract_message_text_and_attachments(
                message, 'perplexity').strip()
            self.finish_reason = self.completion.choices[0].finish_reason
            self.perplexity_messages += [{"role": "assistant",
                                          "content": self.response}]
        except openai.APIError as e:
            self.error = True
            try:
                message = trafilatura.extract(e.message)
                self.error_message = message.splitlines()[0]
            except Exception:
                self.error_message = e

    def ask_deepseek(self):
        """
        Ask a question to DeepSeek.
        """
        if self.deepseek_api_key is None:
            self.error = True
            self.error_message = 'API key for DeepSeek is not set.'
            return
        base_url = 'https://api.deepseek.com'
        client = openai.OpenAI(
            api_key=self.deepseek_api_key,
            base_url=base_url)
        if not self.prompt_continue:
            self.deepseek_messages += self.message
        try:
            self.completion = client.chat.completions.create(
                messages=self.deepseek_messages,
                model=self.model_deepseek,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=False
            )
            self.error = False
            message = self.completion.choices[0].message
            self.response = self._extract_message_text_and_attachments(
                message, 'deepseek').strip()
            self.finish_reason = self.completion.choices[0].finish_reason
            self.deepseek_messages += [{"role": "assistant",
                                        "content": self.response}]
        except json.JSONDecodeError:
            self.error = True
            self.error_message = 'Error: Invalid JSON response from DeepSeek API.'
        except openai.APIError as e:
            self.error = True
            try:
                self.error_code = e.status_code
                self.error_dict = e.body
                self.error_type = f"Error {self.error_code}: {self.error_dict['code']}"
                self.error_message = f"{self.error_type}\n{self.error_dict['message']}"
            except Exception:
                self.error_message = e

    def ask_mistral(self):
        """
        Ask a question to mistral.
        """
        if self.mistral_api_key is None:
            self.error = True
            self.error_message = 'API key for Mistral is not set.'
            return
        client = mistralai.Mistral(api_key=self.mistral_api_key)
        self.mistral_messages += self.message
        try:
            self.completion = client.chat.complete(
                messages=self.mistral_messages,
                model=self.model_mistral,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            self.error = False
            message = self.completion.choices[0].message
            self.response = self._extract_message_text_and_attachments(
                message, 'mistral').strip()
            self.finish_reason = self.completion.choices[0].finish_reason
            self.mistral_messages += [{"role": "assistant",
                                       "content": self.response}]
        except mistralai.SDKError as e:
            self.error = True
            try:
                self.error_code = e.status_code
                self.error_dict = json.loads(e.body)
                self.error_message = f"Error {self.error_code}: {self.error_dict['message']}"
            except Exception:
                self.error_message = e

    def ask_xai(self):
        """
        Ask a question to xAI.
        """
        if self.xai_api_key is None:
            self.error = True
            self.error_message = 'API key for xAI is not set.'
            return
        base_url = 'https://api.x.ai/v1'
        client = openai.OpenAI(
            api_key=self.xai_api_key,
            base_url=base_url)
        self.xai_messages += self.message
        try:
            self.completion = client.chat.completions.create(
                messages=self.xai_messages,
                model=self.model_xai,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            self.error = False
            message = self.completion.choices[0].message
            self.response = self._extract_message_text_and_attachments(
                message, 'xai').strip()
            self.finish_reason = self.completion.choices[0].finish_reason
            self.xai_messages += [{"role": "assistant",
                                   "content": self.response}]
        except openai.APIError as e:
            self.error = True
            try:
                self.error_code = e.status_code
                self.error_type = f"Error {self.error_code}"
                self.error_message = f"{self.error_type}: {e.body}"
            except Exception:
                self.error_message = e

    def ask_local(self):
        """
        Ask a question to local language model.
        """
        if not self.prompt_continue:
            self.local_messages += self.message
        try:
            self.response = ollama.chat(
                messages=self.local_messages,
                model=self.model_local
            )
            self.error = False
            self.response = self.response.message.content.strip()
            self.finish_reason = 'stop'
            self.local_messages += [{"role": "assistant",
                                     "content": self.response}]
        except ConnectionError as e:
            self.error = True
            self.error_message = f'{e}\nInstall ollama and run "ollama serve".'
        except Exception as e:
            self.error = True
            try:
                self.error_code = e.status_code
                self.error_message = e.error
                if self.error_code == 404:
                    self.error_message += f'\nRun "ollama pull {self.model}" and try again.'
            except Exception:
                self.error_message = e

    def list_models(self):
        """
        Retrieves and prints the list of available models for the currently selected AI provider.

        This method dynamically dispatches the call to a specific `list_models_<provider>`
        function based on the `self.ai_provider` attribute. If the specific function is
        not defined, it prints an error message and exits the program.
        """
        func_name = 'list_models_' + self.ai_provider.name.lower()
        try:
            func = getattr(self, func_name)
        except AttributeError:
            print(
                f'multiai system error: {func_name}() function is not defined.')
            sys.exit(1)
        models = func()
        for m in models:
            print(m)

    def _list_models_openai_compatible(self, api_key, base_url):
        """
        Helper method to fetch model lists from OpenAI-compatible APIs.

        Args:
            api_key (str): The API key for authentication.
            base_url (str): The base URL of the API endpoint.

        Returns:
            list[str]: A list of model IDs available at the endpoint. Returns an error message if an error occurs.
        """
        try:
            client = openai.OpenAI(api_key=api_key, base_url=base_url)
            models = []
            for m in client.models.list():
                models.append(m.id)
            return models
        except Exception as e:
            return [f"Error fetching models from {base_url}: {e}", ]

    def list_models_openai(self):
        """
        Retrieves the list of available models from the official OpenAI API.
        """
        return self._list_models_openai_compatible(
            api_key=self.openai_api_key,
            base_url="https://api.openai.com/v1"
        )

    def list_models_anthropic(self):
        """
        Returns a reference to Anthropic's model documentation.
        Note: Anthropic does not currently provide a standardized endpoint for listing models dynamically.
        """
        return [
            "See https://platform.claude.com/docs/en/about-claude/models/overview",
        ]

    def list_models_google(self):
        """
        Retrieves the list of available Gemini models via Google's OpenAI-compatible API endpoint.
        """
        base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"

        return self._list_models_openai_compatible(
            api_key=self.google_api_key,
            base_url=base_url
        )

    def list_models_perplexity(self):
        """
        Returns a reference to Perplexity's model documentation.
        """
        return [
            "See https://docs.perplexity.ai/getting-started/models",
        ]

    def list_models_mistral(self):
        """
        Retrieves the list of available models from Mistral AI via their OpenAI-compatible API.
        """
        return self._list_models_openai_compatible(
            api_key=self.mistral_api_key,
            base_url="https://api.mistral.ai/v1"
        )

    def list_models_deepseek(self):
        """
        Retrieves the list of available models from DeepSeek via their OpenAI-compatible API.
        """
        return self._list_models_openai_compatible(
            api_key=self.deepseek_api_key,
            base_url="https://api.deepseek.com"
        )

    def list_models_xai(self):
        """
        Retrieves the list of available models from xAI (Grok) via their OpenAI-compatible API.
        """
        return self._list_models_openai_compatible(
            api_key=self.xai_api_key,
            base_url="https://api.x.ai/v1"
        )

    def list_models_local(self):
        """
        Returns a message indicating that listing local models is currently unavailable or not implemented.
        """
        return [
            "Unavailable to list models for local.",
        ]


class Provider(enum.Enum):
    """
    Provider is an Enum representing AI provider available at multiai.

    To add a provider definition,
    (1) Add the provider here. Note that the first letter should not
        overwrap other command-line options.
    (2) Define ask_provider() function in Prompt class.
    (3) Update clear() function in Prompt class.
    (4) Define default model at system.ini.
    """
    OPENAI = enum.auto()
    ANTHROPIC = enum.auto()
    GOOGLE = enum.auto()
    PERPLEXITY = enum.auto()
    MISTRAL = enum.auto()
    DEEPSEEK = enum.auto()
    XAI = enum.auto()
    LOCAL = enum.auto()


class ColorCode(enum.Enum):
    """
    ColorCode is an Enum representing ANSI color codes.

    Each member of this Enum corresponds to a specific color used in terminal output.
    """
    BLACK = 30
    RED = 31
    GREEN = 32
    YELLOW = 33
    BLUE = 34
    MAGENTA = 35
    CYAN = 36
    WHITE = 37
    BACK_BLACK = 40
    BACK_RED = 41
    BACK_GREEN = 42
    BACK_YELLOW = 43
    BACK_BLUE = 44
    BACK_MAGENTA = 45
    BACK_CYAN = 46
    BACK_WHITE = 47
