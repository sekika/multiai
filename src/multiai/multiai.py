"""
multiai - A Python library for text-based AI interactions
"""
import anthropic
import configparser
import enum
import google.generativeai as genai
import json
import openai
import os
import mistralai
import pkg_resources
import PyPDF2
import pyperclip
import requests
import sys
import trafilatura
from io import BytesIO
from .printlong import print_long

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
        distribution = pkg_resources.get_distribution('multiai')
        self.version = distribution.version
        metadata = distribution.get_metadata(distribution.PKG_INFO)
        for line in metadata.splitlines():
            if line.startswith('Summary:'):
                self.description = line.split(':', 1)[1].strip()
            elif line.startswith('Project-URL: Homepage,'):
                self.url = line.split(', ', 1)[1].strip()
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
        Set AI provider

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
        Set model

        :param prvider: str
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
        self.mistral_messages = []

    def ask(self, prompt, request=1, verbose=False):
        """
        Ask a question to AI.

        :param prompt: str
            prompt to ask AI
        :param request: int
            numbers of repetitive request
        :param verbose: boolean
            show repeat process
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

    def ask_print(self, prompt, prompt_summary=None):
        """
        Ask a question to AI and print, copy, log

        :param prompt: str
            prompt to ask AI
        :param prompt_summary: str
            prompt shortened for logging
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
                with open(self.log_file, mode='a') as f:
                    f.write(
                        f'### {self.role}:\n{prompt}\n### {self.model}:\n{answer}\n')
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
        Interactive mode

        :param pre_prompt: str
            pre-prompt to append before prompt
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
        Return colored text with color defined at self.prompt_color

        :param text: str
            Text
        :return: str
            Colored text
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
        :param verbose: boolean
            whether to print message
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
        # Supress logging warnings of libraries
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
                # print(f'e = {e.__dict__.keys()}')
                # for key in e.__dict__.keys():
                #     print(f'e.{key} = {getattr(e, key)}')
                message = trafilatura.extract(e.message)
                self.error_message = message.splitlines()[0]
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


class Provider(enum.Enum):
    """
    Provider is an Enum representing AI provider available at multiai.

    To add a provider definition,
    (1) Add the provider here. Note that the first letter should not
        overwrap other command-line options
    (2) Define ask_provider() function in Prompt class
    (3) Update clear() function in Prompt class
    (4) Define default model at system.ini
    """
    ANTHROPIC = enum.auto()
    GOOGLE = enum.auto()
    OPENAI = enum.auto()
    PERPLEXITY = enum.auto()
    MISTRAL = enum.auto()


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
