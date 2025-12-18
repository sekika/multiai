# multiai Release Notes

The release history is listed from newest to oldest. To check your installed version, run: `python -m pip show multiai`. To upgrade to the latest version, run: `python -m pip install --upgrade multiai`.

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
