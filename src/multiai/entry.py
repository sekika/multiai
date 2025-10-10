"""
Entry point for multiai CLI with file attachment support.

Usage examples:
  ai "Explain this" -f doc1.pdf notes.md --attach-limit 50000
  ai -u https://example.com/article.html -f table.csv
  ai -e -f report.docx  # English helper + attachments
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
    Entry point of multiai CLI (invoked by `ai` command).
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
    # [prompt] section
    prompt_english = inifile.get('prompt', 'english')
    prompt_url = inifile.get('prompt', 'url')

    # Load command-line arguments
    parser = argparse.ArgumentParser(
        description=f'multiai {client.version} - {client.description} {client.url}')
    parser.add_argument('prompt', nargs='*',
                        help='prompt for AI')
    for provider in Provider:
        name = provider.name.lower()
        help_msg = 'use ' + name
        if client.ai_provider == provider:
            help_msg += ' (Default)'
        parser.add_argument(
            # -i for mistral, -a for anthropic, etc.
            '-' + name.replace('m', '')[0],
            '--' + name,
            action='store_true',
            help=help_msg)
    parser.add_argument('-m', '--model',
                        help='set model')
    parser.add_argument('-t', '--temperature',
                        help=f'set temperature. 0 is deterministic. Default is {client.temperature}.')
    parser.add_argument('-e', '--english',
                        action='store_true', help='correct if English, translate into English otherwise')
    parser.add_argument('-u', '--url',
                        help='retrieve text from the URL')

    # From version 1.4.0: file attachment option (replaces old -f/--factual)
    parser.add_argument('-f', '--file', nargs='+', action='append',
                        help='attach one or more files (txt, md, pdf, docx, html/htm, csv)')
    parser.add_argument('--attach-limit', type=int, default=client.attach_char_limit,
                        help=f'character limit per attachment before auto-summarization (default {client.attach_char_limit})')

    if not client.always_copy:
        parser.add_argument('-c', '--copy',
                            action='store_true', help='copy the latest answer')
    if not client.always_log:
        parser.add_argument('-s', '--save',
                            action='store_true', help=f'save log as {log_file}')
    args = parser.parse_args()

    # Get prompt
    prompt = ' '.join(args.prompt).strip()

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

    # -s option
    if client.always_log:
        args.save = True
    client.log = args.save
    if args.save:
        if not os.path.exists(log_file):
            try:
                with open(log_file, 'w') as file:
                    file.write("# AI chat log\n\n")
            except Exception as e:
                print(e)
                print('Check the setting of log_file.')
                sys.exit(1)

    # -e option
    pre_prompt = ''
    if args.english:
        pre_prompt = prompt_english + '\n\n'

    # Track if the user did not provide a prompt originally
    original_prompt_empty = (len(' '.join(args.prompt).strip()) == 0)

    # Build attachment text if any
    attached_texts = []
    attached_names = []
    if args.file:
        # Flatten nested lists
        all_files = [f for group in args.file for f in group]
        for fpath in all_files:
            if not os.path.exists(fpath):
                print(f'File not found: {fpath}')
                sys.exit(1)
            text = client.retrieve_from_file(fpath, verbose=True)
            n = len(text)
            if n > args.attach_limit:
                print(
                    f'Attachment "{os.path.basename(fpath)}" has {n} characters and exceeds the limit {args.attach_limit}. Summarizing the attachment.')
                text = client.summarize_text(text)
            attached_texts.append((os.path.basename(fpath), text))
            attached_names.append(os.path.basename(fpath))

    attachments_section = ''
    if attached_texts:
        blocks = []
        for name, text in attached_texts:
            blocks.append(f'=== Attachment: {name} ===\n{text}')
        attachments_section = '\n\n'.join(blocks)

    # One-shot send when prompt is empty and attachments are present
    did_one_shot_with_attachments = False
    if original_prompt_empty and attachments_section:
        base_prompt = prompt_url
        print(
            f'{client.color(client.role)}> {base_prompt}\n\nAttachments: {", ".join(attached_names)}')
        prompt_summary = f'{prompt_url}\n\nAttachments: {", ".join(attached_names)}'
        one_shot_prompt = base_prompt + '\n' + attachments_section
        client.ask_print(one_shot_prompt, prompt_summary=prompt_summary)
        did_one_shot_with_attachments = True

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
    # Enter interactive mode if:
    # - no prompt was provided originally, or
    # - URL was used (keeps old behavior), or
    # - we already did a one-shot with attachments above.
    if original_prompt_empty or args.url or did_one_shot_with_attachments:
        client.interactive(pre_prompt=pre_prompt)
    else:
        # Prompt provided; attach attachments immediately and send once
        if attachments_section:
            # For logging, keep a concise summary line about attachments
            prompt_summary = f'{prompt}\n\nAttachments: {", ".join(attached_names)}'
            prompt = pre_prompt + prompt + '\n\n' + attachments_section
            client.ask_print(prompt, prompt_summary=prompt_summary)
        else:
            client.ask_print(pre_prompt + prompt)
