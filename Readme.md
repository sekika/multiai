# multiai

`multiai` is a Python library and command-line tool designed to interact with text-based generative AI models from the following providers:

| AI Provider  | Web Service                        | Models Available                                               |
|--------------|------------------------------------|----------------------------------------------------------------|
| **OpenAI**   | [ChatGPT](https://chat.openai.com/) | [GPT Models](https://platform.openai.com/docs/models) |
| **Anthropic**| [Claude](https://claude.ai/) | [Claude Models](https://docs.anthropic.com/en/docs/about-claude/models) |
| **Google**   | [Gemini](https://gemini.google.com/)| [Gemini Models](https://ai.google.dev/gemini-api/docs/models/gemini) |
| **Perplexity** | [Perplexity](https://www.perplexity.ai/) | [Perplexity Models](https://docs.perplexity.ai/docs/model-cards) |
| **Mistral**  | [Mistral](https://chat.mistral.ai/chat) | [Mistral Models](https://docs.mistral.ai/getting-started/models/) |

## Key Features

- **Interactive Chat:** Communicate with AI directly from your terminal.
- **Multi-Line Input:** Supports multi-line prompts for complex queries.
- **Pager for Long Responses:** View lengthy responses conveniently using a pager.
- **Continuation Handling:** Automatically handle and request continuations if responses are cut off.
- **Automatic Chat Logging:** Automatically save your chat history for future reference.

## Usage

Install `multiai`, then configure your API keys for your chosen AI providers as environment variables or in a user-setting file. Once that's done, you can start interacting with the AI.

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

To see a list of all command-line options, use:

```bash
ai -h
```

For more detailed documentation, you can open the [manual](https://sekika.github.io/multiai/) in a web browser with:

```bash
ai -d
```

## Using `multiai` as a Python Library

`multiai` can also be used as a Python library. Here’s a simple example:

```python
import multiai

# Initialize the client
client = multiai.Prompt()
client.set_model('openai', 'gpt-4o')  # Set model
client.temperature = 0.5  # Set temperature

# Send a prompt and get a response
answer = client.ask('hi')
print(answer)

# Continue the conversation with context
answer = client.ask('how are you')
print(answer)

# Clear the conversation context
client.clear()
```

The manual includes the following sample codes:

- A script that translates a text file into English.
- A local chat app that allows you to easily select from various AI models provided by different providers and engage in conversations with them.
