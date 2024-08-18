"""
Entry point of multiai
"""
import argparse
import configparser
import os
import readline
import subprocess
import sys
import webbrowser
from datetime import datetime
from .multiai import Prompt, Provider

__all__ = [
    "entry",
]


def entry():
    """
    Entry point of multiai

    to be invoked with ai command
    """
    client = Prompt()
    # Load user setting from config file in the order of
    # data/system.ini, ~/.multiai, .multiai
    inifile = configparser.ConfigParser()
    here = os.path.abspath(os.path.dirname(__file__))
    inifile.read(os.path.join(here, 'data/system.ini'))
    inifile.read(os.path.expanduser('~/.multiai'))
    inifile.read('.multiai')
    # Start reading [command] section of the config file
    # log_file: file name of the log file.
    log_file = inifile.get('command', 'log_file')
    log_file = os.path.expanduser(log_file)
    log_file = log_file.replace('DATE', datetime.today().strftime('%Y%m%d'))
    client.log_file = log_file
    # user_agent: user agent when retrieving web data
    client.user_agent = inifile.get('command', 'user_agent', fallback=None)
    # [promot] section
    prompt_english = inifile.get('prompt', 'english')
    prompt_factual = inifile.get('prompt', 'factual')
    prompt_url = inifile.get('prompt', 'url')
    # Load commandline argument
    parser = argparse.ArgumentParser(
        description=f'multiai {client.version} - {client.description}')
    parser.add_argument('prompt', nargs='*',
                        help='prompt for AI')
    parser.add_argument('-d', '--document',
                        action='store_true', help='open document page and exit')
    for provider in Provider:
        name = provider.name.lower()
        help = 'use ' + name
        if client.ai_provider == provider:
            help += ' (Default)'
        parser.add_argument(
            '-' + name.replace('m', '')[0],
            '--' + name,
            action='store_true',
            help=help)
    parser.add_argument('-m', '--model',
                        help='set model')
    parser.add_argument('-t', '--temperature',
                        help=f'set temperature. 0 is deterministic. Default is {client.temperature}.')
    parser.add_argument('-e', '--english',
                        action='store_true', help='correct if English, translate into English otherwise')
    parser.add_argument('-f', '--factual',
                        action='store_true', help='factual information')
    parser.add_argument('-u', '--url',
                        help='retrieve text from the URL')
    if not client.always_copy:
        parser.add_argument('-c', '--copy',
                            action='store_true', help='copy the latest answer')
    if not client.always_log:
        parser.add_argument('-l', '--log',
                            action='store_true', help=f'save log as {log_file}')
    args = parser.parse_args()
    # Get prompt
    prompt = ' '.join(args.prompt)
    # -d option
    if args.document:
        webbrowser.open(client.url)
        sys.exit()
    # Set ai_provider, ai_providers and model
    client.ai_providers = []
    for provider in Provider:
        if getattr(args, provider.name.lower()):
            client.ai_provider = provider
            client.ai_providers.append(provider)
    if len(client.ai_providers) == 0:
        client.ai_providers = [client.ai_provider]
    if len(client.ai_providers) == 1:
        default_model = 'model_' + client.ai_provider.name.lower()
        if args.model:
            setattr(client, default_model, args.model)
        client.model = getattr(client, default_model, None)
    # -t option
    if args.temperature:
        try:
            client.temperature = float(args.temperature)
        except ValueError:
            print("Invalid 'temperature': should be a number.")
            sys.exit(1)
        if client.temperature < 0:
            print("Invalid 'temperature': should be >=0.")
            sys.exit(1)
    # -c option
    if client.always_copy:
        args.copy = True
    client.copy = args.copy
    # -l option
    if client.always_log:
        args.log = True
    client.log = args.log
    if args.log:
        if not os.path.exists(log_file):
            with open(log_file, 'w') as file:
                file.write("# AI chat log\n\n")
    # -e and -f option
    pre_prompt = ''
    if args.english:
        pre_prompt = prompt_english + '\n\n'
    if args.factual:
        pre_prompt = prompt_factual + '\n'
    # -u option
    if args.url:
        text = client.retrieve_from_url(args.url)
        if prompt == '':
            prompt = prompt_url
        print(f'{client.color(client.role)}> {prompt}\n\nText of {args.url}')
        prompt_summary = f'{prompt_url}\n\nText of {args.url}'
        prompt += '\n' + text
        client.ask_print(prompt, prompt_summary=prompt_summary)
    # Finished loading arguments and run
    if prompt == '' or args.url:
        client.interactive(pre_prompt=pre_prompt)
    else:
        client.ask_print(pre_prompt + prompt)
