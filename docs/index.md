[ English [日本語](index-ja.md) ]

# multiai

`multiai` is a Python library and command-line tool designed to interact with text-based generative AI models from OpenAI, Anthropic, Google, Perplexity, and Mistral. This manual will guide you through the installation, configuration, and usage of `multiai`.

## Table of Contents

- [Supported AI Providers and Models](#supported-ai-providers-and-models)
- [Key Features](#key-features)
- [Getting Started](#getting-started)
  - [Installation](#installation)
  - [Setting Up Your Environment](#setting-up-your-environment)
  - [Basic Usage](#basic-usage)
  - [Interactive Mode Details](#interactive-mode-details)
  - [Configuration](#configuration)
    - [Settings File](#settings-file)
    - [Selecting Models and Providers](#selecting-models-and-providers)
    - [API Key Management](#api-key-management)
- [Advanced Usage](#advanced-usage)
  - [Model Parameters](#model-parameters)
  - [Input Options](#input-options)
  - [Output Options](#output-options)
  - [Command-Line Options](#command-line-options)
- [Using `multiai` as a Python Library](#using-multiai-as-a-python-library)
  - [Running on Google Colab](#running-on-google-colab)
  - [Running your local chat app](#running-your-local-chat-app)

## Supported AI Providers and Models

`multiai` allows you to interact with AI models from the following providers:

| AI Provider  | Web Service                        | Models Available                                               |
|--------------|------------------------------------|----------------------------------------------------------------|
| **OpenAI**   | [ChatGPT](https://chatgpt.com/) | [GPT Models](https://platform.openai.com/docs/models) |
| **Anthropic**| [Claude](https://claude.ai/) | [Claude Models](https://docs.anthropic.com/en/docs/about-claude/models) |
| **Google**   | [Gemini](https://gemini.google.com/)| [Gemini Models](https://ai.google.dev/gemini-api/docs/models/gemini)  |
| **Perplexity** | [Perplexity](https://www.perplexity.ai/) | [Perplexity Models](https://docs.perplexity.ai/docs/model-cards) |
| **Mistral**  | [Mistral](https://chat.mistral.ai/chat) | [Mistral Models](https://docs.mistral.ai/getting-started/models/) |

## Key Features

- **Interactive Chat:** Communicate with AI directly from your terminal.
- **Multi-Line Input:** Supports multi-line prompts for complex queries.
- **Pager for Long Responses:** View lengthy responses conveniently using a pager.
- **Continuation Handling:** Automatically handle and request continuations if responses are cut off.
- **Automatic Chat Logging:** Automatically save your chat history for future reference.

## Getting Started

### Installation

To install `multiai`, use the following command:

```bash
pip install multiai
```

### Setting Up Your Environment

Before using `multiai`, configure your API key(s) for your chosen AI provider(s). Set your API key as an environment variable or in a user-setting file:

```bash
export OPENAI_API_KEY=your_openai_api_key_here
```

### Basic Usage

Once your API key is set up, you can start interacting with the AI:

- To send a simple query:

  ```bash
  ai hi
  ```

  You should see a response like:

  ```bash
  gpt-4o-mini>
  Hello! How can I assist you today?
  ```

- For an interactive session, enter interactive mode:

  ```bash
  ai
  ```

  In this mode, you can continue the conversation:

  ```bash
  user> hi
  gpt-4o-mini>
  Hello! How can I assist you today?
  user> how are you
  gpt-4o-mini>
  I'm just a program, so I don't have feelings, but I'm here and ready to help you! How about you? How are you doing?
  user>
  ```

### Interactive Mode Details

In interactive mode, you can input multi-line text and control when the input is finished using the `blank_lines` parameter in the `[command]` section of the settings file. Here’s how it works:

- **Single-Line Input:** By default, input is finished when you press Enter after a line.
- **Multi-Line Input:** If you set `blank_lines = 1`, input will finish only after a blank line (i.e., pressing Enter twice). This is particularly useful when you want to copy and paste text with multiple lines. If your input includes blank lines, increase the `blank_lines` parameter accordingly.

Interactive mode can be exited by:

- Input `q`, `x`, `quit` or `exit`.
- Sending EOF with `Ctrl-D`.
- Sending a KeyboardInterrupt with `Ctrl-C`.

### Configuration

#### Settings File

`multiai` reads its settings from a configuration file, which can be located in the following order of precedence:

1. **System Default:** [system default settings](https://github.com/sekika/multiai/blob/master/src/multiai/data/system.ini)
2. **User-Level:** `~/.multiai`
3. **Project-Level:** `./.multiai`

Settings from the latter files overwrite those from the former.

Here’s an example of a configuration file:

```ini
[model]
ai_provider = openai
openai = gpt-4o-mini
anthropic = claude-3-haiku-20240307
google = gemini-1.5-flash
perplexity = llama-3.1-sonar-small-128k-chat
mistral = mistral-large-latest

[default]
temperature = 0.7
max_requests = 5

[command]
blank_lines = 0
always_copy = no
always_log = no
log_file = chat-ai-DATE.md

[prompt]
color = blue
english = If the following sentence is English, revise the text to improve its readability and clarity in English. If not, translate into English. No need to explain. Just output the result English text.
factual = Do not hallucinate. Do not make up factual information.
url = Summarize following text very briefly.

[api_key]
openai = (Your OpenAI API key)
anthropic = (Your Claude API key)
google = (Your Gemini API key)
perplexity = (Your Perplexity API key)
mistral = (Your Mistral API key)
```

#### Selecting Models and Providers

The default AI provider is specified in the `[model]` section of the settings file. However, you can override this via command-line options:

- `-o` for OpenAI
- `-a` for Anthropic
- `-g` for Google
- `-p` for Perplexity
- `-i` for Mistral

You can also specify the model using the `-m` option. For example, to use the `gpt-4o` model from OpenAI:

```bash
ai -om gpt-4o
```

When multiple AI provider options are given, for example:
```bash
ai -oa
```
you can communicate with multiple models simultaneously. Default model for each provider is used.

#### API Key Management

API keys can be stored as environment variables:

- `OPENAI_API_KEY` for OpenAI
- `ANTHROPIC_API_KEY` for Anthropic
- `GOOGLE_API_KEY` for Google
- `PERPLEXITY_API_KEY` for Perplexity
- `MISTRAL_API_KEY` for Mistral

If environment variables are not set, `multiai` will look for keys in the `[api_key]` section of your settings file.

---

## Advanced Usage

### Model Parameters

Parameters such as `temperature` and `max_tokens` can be configured in the settings file or via command-line options:

- Use the `-t` option to set the `temperature`.
- `max_tokens` parameter can be omitted.

If the response is incomplete, `multiai` will request additional information until the specified number of requests, `max_requests`, is reached.

### Input Options

`multiai` provides several command-line options to simplify specific types of prompts:

- **`-e` Option:** Adds a pre-prompt to correct or translate English text. This pre-prompt is defined in the `english` parameter in the `[prompt]` section of the settings file.
  
  Example usage:
  ```bash
  ai -e This are a test
  ```
  
- **`-f` Option:** Adds a pre-prompt to prevent hallucination or fabricated information. This is defined in the `factual` parameter in the settings file.

  Example usage:
  ```bash
  ai -f Explain quantum mechanics
  ```
  
- **`-u URL` Option:** Automatically retrieves and converts the content of a given URL to text. If the URL ends in `.pdf`, the content of the PDF file is also converted to text. The program will summarize the text based on a pre-prompt and then allow for further interactive queries about the content. If you want the program to summarize in your native language, rewrite the pre-prompt defined in the `url` parameter in the settings file in your language.

  Example usage:
  ```bash
  ai -u https://en.wikipedia.org/wiki/Artificial_intelligence
  ```

### Output Options

- **Paging Long Responses:** If a response exceeds one page in your terminal, `multiai` uses [pypager](https://pypi.org/project/pypager/) to display it.

- **Copy to Clipboard:** Use the `-c` option to copy the last response to the clipboard. If `always_copy = yes` is set in the `[command]` section of the settings file, this option is always enabled.

  Example usage:
  ```bash
  ai -c "What is the capital of France?"
  ```

- **Logging Chats:** Use the `-l` option to log the chat to a file named `chat-ai-DATE.md` in the current directory, where `DATE` is replaced by today’s date. The file name can be changed with the `log_file` key in the `[command]` section. If `always_log = yes` is set in the `[command]` section, this option is always enabled.

  Example usage:
  ```bash
  ai -l Tell me a joke
  ```

### Command-Line Options

To see a list of all command-line options, use:

```bash
ai -h
```

For more detailed documentation, you can open this manual in a web browser with:

```bash
ai -d
```

## Using `multiai` as a Python Library

`multiai` can also be used as a Python library. Here’s a simple example:

```python
import multiai

# Initialize the client
client = multiai.Prompt()
# Set model and temperature.
# If not written, default setting is used.
client.set_model('openai', 'gpt-4o')
client.temperature = 0.5

# Send a prompt and get a response
answer = client.ask('hi')
print(answer)

# Continue the conversation with context
answer = client.ask('how are you')
print(answer)

# Clear the conversation context
client.clear()
```

If an error occurs during `client.ask`, the error message will be returned, and `client.error` will be set to `True`.

Another example. Save the following code as `english.py`.

```python
import multiai
import sys
pre_prompt = "Translate the following text into English. Just answer the translated text and nothing else."
file = sys.argv[1]
with open(file) as f:
    prompt = f.read()
client = multiai.Prompt()
client.set_model('openai', 'gpt-4o')
answer = client.ask(pre_prompt + '\n\n' + prompt)
print(answer)
```

Then if you have a markdown file of `text.md` in Japanese, for example, run

```
python english.py text.md
```

Then the translated English is shown. If you want to save it to `output.md`, just redirect the result by

```
python english.py text.md > output.md
```
If you change `pre_prompt` parameter, you can make various kinds of script.

### Running on Google Colab

To run on Google Colab, use [this notebook](https://colab.research.google.com/github/sekika/multiai/blob/main/docs/multiai.ipynb). You will need to set API keys in your Colab Secrets.

### Running your local chat app

You can run your local chat app using `streamlit`. Install `streamlit` by running the following command:
```bash
pip install streamlit
```

Download [app.py](https://github.com/sekika/multiai/blob/main/docs/app.py) and run your local server with the following command:

```bash
streamlit run app.py
```

Once the server is running, your default web browser will open and display the chat application, Chotto GPT. This app allows you to easily select from a variety of AI models from different providers and engage in conversations with them. You can customize the list of available models and the log file location by directly editing the source code.
