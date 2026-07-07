# multiai Release Notes

The release history is listed from newest to oldest. To check your installed version, run: `python -m pip show multiai`. To upgrade to the latest version, run: `python -m pip install --upgrade multiai`.

## 1.6.1 - 2026/7/7
- Fix: Anthropic requests now stream internally, avoiding the SDK's default 10-minute timeout on long-running (e.g. reasoning) responses. The complete response text is still returned as before.
- Fix: Prevent a crash when an Anthropic response contains a text block whose text is `None` (`TypeError`/`AttributeError` when building the response).

## 1.6.0 - 2026/6/16
- New: Added response attachment support. When a provider API returns actual file-like data in an AI response, `multiai` can now receive it, expose it through the Python API, and save it from the CLI.
  - Added the `ResponseAttachment` data structure.
  - Added `client.response_attachments` to access attachments returned by the latest response.
  - Added `client.save_attachment(attachment, filename)` to explicitly save a response attachment when using `multiai` as a Python library.
  - Added automatic saving of actual response attachments in the CLI.
  - Added `[response_attachment] directory` setting to configure the save directory. If not set, `./multiai_attachments` is used.
  - Added `--response-attachment-dir DIR` CLI option to override the response attachment save directory.
  - If a response attachment is returned as a URL, `multiai` displays the URL but does not download it.
- Note: In the current chat-based API usage, most providers usually return text only, so response attachments are uncommon. This feature is mainly a foundation for future support of APIs and tools that can return actual files, such as image generation, code interpreter outputs, Gemini inline data, or OpenAI Responses API file outputs.

## 1.5.2 - 2026/6/10
- Added support for Anthropic's Claude Fable model. The temperature parameter is now only available for Sonnet and Haiku models.

## 1.5.1 - 2026/5/1
- Not using the temperature parameter for Anthropic's Claude Opus model, due to a specification change introduced in Claude Opus 4.7.

## 1.5.0 - 2026/1/19
- New: Added `--list` CLI option to list available models
- New: Added support for loading the Azure Speech API key for use with multiai-tts

## 1.4.3 - 2026/1/12
- New: Released [multiai-tts](https://pypi.org/project/multiai-tts/), an official extension library adding Text-to-Speech capabilities via OpenAI and Google GenAI.

## 1.4.2 - 2025/12/24
- Replaced deprecated PyPDF2 with pypdf.

## 1.4.1 - 2025/12/18
- Migrated Gemini client from google.generativeai to google.genai as google.generativeai is being [deprecated](https://github.com/google-gemini/deprecated-generative-ai-python/blob/main/README.md).

## 1.4.0 - 2025/10/10
- New: file attachments for text-like inputs (CLI and library). Special handling for txt/md/pdf/docx/html/htm/csv; unknown extensions accepted if valid UTF-8 text (no NUL bytes), otherwise rejected.
- New: CLI options -f/--file and --attach-limit (auto-summarizes oversized attachments with a notice); when no prompt is provided, attachments are applied only to the first turn before entering interactive mode.
- New: library helpers retrieve_from_file(), summarize_text(), and attach_char_limit config.
- Change: removed -f/--factual option (breaking change); added dependency on python-docx for .docx support.

## 1.3.2 - 2025/9/30
- Migrated from pkg_resources to importlib.metadata as pkg_resources is being deprecated.

## 1.3.1 - 2025/8/8
- Adapt to gpt-5 series

## 1.3.0 - 2025/5/2
- Resolve conflict with the -l option

## 1.2.0 - 2025/2/21
- xAI support

## 1.1.0 - 2025/2/6
- DeepSeek and local LLM support

## 1.0.0 - 2024/12/6
- First stable version

## 0.1 - 2024/8/16
- First release

## See also
- [Release at PyPI](https://pypi.org/project/multiai/#history)
- [GitHub commits](https://github.com/sekika/multiai/commits)
- [X post](https://x.com/seki/status/1976601995428745238)
