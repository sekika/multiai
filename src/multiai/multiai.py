"""
multiai - A Python library for text-based AI interactions with multi-provider support.
"""
import anthropic
import configparser
import enum
import google.generativeai as genai
import json
import ollama
import openai
import os
import mistralai
import PyPDF2
import pyperclip
import requests
import sys
import trafilatura
from io import BytesIO
from importlib.metadata import distribution, PackageNotFoundError
from .printlong import print_long
import docx  # python-docx
from docx import Document

__all__ = [
    "Prompt",
    "Provider",
    "ColorCode",
]


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
            self.description = (md.get('Summary') or '').strip()
            # Project-URL: Homepage, https://... or Home-page
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

        for provider in Provider:
            env = os.getenv(provider.name + '_API_KEY')
            name = provider.name.lower()
            key = name + '_api_key'
            if env is None:
                ini = inifile.get('api_key', name, fallback=None)
                setattr(self, key, ini)
            else:
                setattr(self, key, env)
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

    def clear(self):
        """
        Clear chat history.
        """
        self.openai_messages = []
        self.anthropic_messages = []
        self.google_chat = None
        self.perplexity_messages = []
        self.deepseek_messages = []
        self.mistral_messages = []
        self.xai_messages = []
        self.local_messages = []

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
            self.response += '\n\nFinish reason: {self.finish_reason}'
            return self.response
        # Response not finished. Continue the request.
        request += 1
        if request > self.max_requests:
            self.response += '\n\nFinished because of max_tokens and max_requests.'
            return self.response
        if verbose:
            print(
                f'{self.color("Repeating...")} max_requests = {self.max_requests}, requests = {request}\r',
                end='')
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
            'google_chat': self.google_chat,
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
        self.google_chat = backups['google_chat']
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
        if len(self.ai_providers) == 1:
            answer = self.ask(prompt, verbose=True)
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
        print(' ' * 50 + '\r', end='')
        print_long(answer)
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
                reader = PyPDF2.PdfReader(pdf_file)
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
                    reader = PyPDF2.PdfReader(pdf_file)
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
            if self.model[:5] == 'gpt-5' or self.model[0] == 'o':
                # gpt-5, o1 and o3 series do not support variable temperature and
                # max_tokens is written as max_completion_tokens
                self.completion = openai.chat.completions.create(
                    messages=self.openai_messages,
                    model=self.model_openai,
                    max_completion_tokens=self.max_tokens
                )
            else:
                self.completion = openai.chat.completions.create(
                    messages=self.openai_messages,
                    model=self.model_openai,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )
            self.error = False
            self.response = self.completion.choices[0].message.content.strip(
            )
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
        if not self.prompt_continue:
            self.anthropic_messages += self.message
        try:
            self.completion = client.messages.create(
                messages=self.anthropic_messages,
                model=self.model_anthropic,
                temperature=self.temperature,
                max_tokens=self.max_tokens if self.max_tokens else self.max_tokens_anthropic
            )
            self.error = False
            self.response = self.completion.content[0].text.strip()
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
        Ask a question to Google.
        """
        # Suppress logging warnings of libraries
        os.environ["GRPC_VERBOSITY"] = "ERROR"
        os.environ["GLOG_minloglevel"] = "2"
        if self.google_api_key is None:
            self.error = True
            self.error_message = 'API key for Google is not set.'
            return
        genai.configure(api_key=self.google_api_key)
        model = genai.GenerativeModel(self.model_google)
        if self.google_chat is None:
            self.google_chat = model.start_chat(history=[])
        config = genai.types.GenerationConfig(
            temperature=self.temperature,
            max_output_tokens=self.max_tokens)
        try:
            self.completion = self.google_chat.send_message(
                self.prompt, generation_config=config)
            self.error = False
            self.response = self.completion.text.replace('•', '* ').strip()
            self.finish_reason = self.completion.candidates[0].finish_reason.name.lower(
            )
        except Exception as e:
            self.error = True
            try:
                self.error_message = e.message
            except Exception:
                self.error_message = e

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
            self.response = self.completion.choices[0].message.content.strip(
            )
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
            self.response = self.completion.choices[0].message.content.strip(
            )
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
            self.response = self.completion.choices[0].message.content.strip(
            )
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
            self.response = self.completion.choices[0].message.content.strip(
            )
            self.finish_reason = self.completion.choices[0].finish_reason
            self.perplexity_messages += [{"role": "assistant",
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
