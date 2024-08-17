[ [English](index.md) 日本語 ]

# multiai

`multiai`は、OpenAI、Anthropic、Google、Perplexity、Mistralのテキスト生成AIモデルとやり取りするためのPythonライブラリおよびコマンドラインツールです。このマニュアルでは、`multiai`のインストール、設定、および使用方法について説明します。

## 目次

- [対応しているAIプロバイダーとモデル](#対応しているaiプロバイダーとモデル)
- [主な機能](#主な機能)
- [はじめに](#はじめに)
  - [インストール](#インストール)
  - [環境設定](#環境設定)
  - [基本的な使い方](#基本的な使い方)
  - [インタラクティブモードの詳細](#インタラクティブモードの詳細)
  - [設定](#設定)
    - [設定ファイル](#設定ファイル)
    - [モデルとプロバイダーの選択](#モデルとプロバイダーの選択)
    - [APIキー管理](#apiキー管理)
- [高度な使用法](#高度な使用法)
  - [モデルパラメータ](#モデルパラメータ)
  - [入力オプション](#入力オプション)
  - [出力オプション](#出力オプション)
  - [コマンドラインオプション](#コマンドラインオプション)
- [Pythonライブラリとしての`multiai`の使用](#pythonライブラリとしてのmultiaiの使用)
- [ローカルチャットアプリの実行](#ローカルチャットアプリの実行)

## 対応しているAIプロバイダーとモデル

`multiai`は、以下のプロバイダーのAIモデルとやり取りすることができます。

| AIプロバイダー   | Webサービス                       | 使用可能なモデル                                             |
|-----------------|----------------------------------|------------------------------------------------------------|
| **OpenAI**      | [ChatGPT](https://chatgpt.com/) | [GPTモデル](https://platform.openai.com/docs/models) |
| **Anthropic**   | [Claude](https://claude.ai/) | [Claudeモデル](https://docs.anthropic.com/en/docs/about-claude/models) |
| **Google**      | [Gemini](https://gemini.google.com/)| [Geminiモデル](https://ai.google.dev/gemini-api/docs/models/gemini)  |
| **Perplexity** | [Perplexity](https://www.perplexity.ai/) | [Perplexityモデル](https://docs.perplexity.ai/docs/model-cards) |
| **Mistral**  | [Mistral](https://chat.mistral.ai/chat) | [Mistralモデル](https://docs.mistral.ai/getting-started/models/) |

## 主な機能

- **インタラクティブチャット:** ターミナルから直接AIと対話できます。
- **複数行入力:** 複雑なクエリのために複数行のプロンプトをサポートします。
- **長文応答のページャー:** 長い応答をページャーで表示できます。
- **継続処理:** 応答が途中で切れた場合に、続きのリクエストを自動的に処理します。
- **自動チャットログ:** チャット履歴を自動的に保存できます。

## はじめに

### インストール

`multiai`をインストールするには、以下のコマンドを使用してください：

```bash
pip install multiai
```

### 環境設定

`multiai`を使用する前に、選択したAIプロバイダーのAPIキーを設定します。APIキーは環境変数として、またはユーザー設定ファイルで設定できます：

```bash
export OPENAI_API_KEY=your_openai_api_key_here
```

### 基本的な使い方

APIキーの設定が完了したら、AIとの対話を開始できます。

- 簡単な質問を送信するには：

  ```bash
  ai こんにちは
  ```

  以下のような応答が表示されるはずです：

  ```bash
  gpt-4o-mini>
  こんにちは！今日はどんなことをお手伝いできますか？
  ```

- インタラクティブセッションを行うには、インタラクティブモードに入ります：

  ```bash
  ai
  ```

  このモードでは、会話を続けることができます：

  ```bash
  user> こんにちは
  gpt-4o-mini>
  こんにちは！ 何かお困りですか？ 何かお手伝いできることがあれば、遠慮なくお申し付けください。
  user> 元気ですか？
  gpt-4o-mini>
  ありがとう！元気です！ あなたはどうですか？ 何か楽しいことはありましたか？
  user>
  ```

### インタラクティブモードの詳細

インタラクティブモードでは、複数行のテキストを入力するために、設定ファイルの`[command]`セクションにある`blank_lines`パラメータを使用して入力完了を制御できます。以下はその仕組みです：

- **1行入力:** デフォルトでは、行の最後にEnterを押すと入力が完了します。
- **複数行入力:** `blank_lines = 1`と設定すると、空行（つまりEnterを2回押す）後にのみ入力が完了します。複数行のテキストをコピー＆ペーストするときに特に便利です。入力に空行が含まれている場合は、`blank_lines`パラメータを適宜増やします。

インタラクティブモードを終了するには：

- `q`、`x`、`quit`または`exit`を入力。
- `Ctrl-D`でEOFを送信。
- `Ctrl-C`でキーボード割り込みを送信。

### 設定

#### 設定ファイル

`multiai`は、設定ファイルから設定を読み込みます。設定ファイルの検索順序は次のとおりです：

1. **システムデフォルト:** [システムデフォルト設定](https://github.com/sekika/multiai/blob/master/src/multiai/data/system.ini)
2. **ユーザーレベル:** `~/.multiai`
3. **プロジェクトレベル:** `./.multiai`

後者のファイルからの設定は、前者の設定を上書きします。

以下は設定ファイルの例です：

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
factual = 自信がないことは回答を拒否して。
url = 以下のテキストを日本語で200文字程度で要約してください。

[api_key]
openai = (Your OpenAI API key)
anthropic = (Your Claude API key)
google = (Your Gemini API key)
perplexity = (Your Perplexity API key)
mistral = (Your Mistral API key)
```

#### モデルとプロバイダーの選択

デフォルトのAIプロバイダーは、設定ファイルの`[model]`セクションで指定されますが、コマンドラインオプションでこれを上書きすることができます：

- `-o` OpenAI
- `-a` Anthropic
- `-g` Google
- `-p` Perplexity
- `-i` Mistral

また、`-m`オプションを使用してモデルを指定することもできます。例えば、OpenAIの`gpt-4o`モデルを使用するには：

```bash
ai -om gpt-4o
```

複数のAIプロバイダーオプションが与えられた場合、例えば:

```bash
ai -oa
```
複数のモデルと同時に会話できます。各プロバイダーのデフォルトモデルが使用されます。

#### APIキー管理

APIキーは、環境変数として保存できます：

- `OPENAI_API_KEY` OpenAI用
- `ANTHROPIC_API_KEY` Anthropic用
- `GOOGLE_API_KEY` Google用
- `PERPLEXITY_API_KEY` Perplexity用
- `MISTRAL_API_KEY` Mistral用

環境変数が設定されていない場合、`multiai`は設定ファイルの`[api_key]`セクションにあるキーを探します。

---

## 高度な使用法

### モデルパラメータ

`temperature`や`max_tokens`などのパラメータは、設定ファイルまたはコマンドラインオプションで設定できます：

- `-t`オプションを使用して`temperature`を設定します。
- `max_tokens`パラメータは省略可能です。

応答が不完全な場合、`multiai`は`max_requests`で指定された回数に達するまで、追加情報を要求します。

### 入力オプション

`multiai`は、プロンプトを簡素化するために、いくつかのコマンドラインオプションを提供します：

- **`-e`オプション:** 英語テキストの修正や翻訳を行う前置プロンプトを追加します。この前置プロンプトは、設定ファイルの`[prompt]`セクションにある`english`パラメータで定義されます。

  使用例：
  ```bash
  ai -e This are a test
  ```
  
- **`-f`オプション:** 虚偽の情報を防ぐための前置プロンプトを追加します。これは設定ファイルの`factual`パラメータで定義されています。

  使用例：
  ```bash
  ai -f 土壌物理学について説明して
  ```
  
- **`-u URL`オプション:** 指定されたURLの内容を自動的に取得してテキストに変換します。URLが`.pdf`で終わる場合、そのPDFファイルの内容もテキストに変換されます。このプログラムは、前置プロンプトに基づいてテキストを要約し、その後、内容に関してインタラクティブモードで質問を受け付けます。要約を母国語で得たい場合は、設定ファイルの`url`パラメータに定義されている前置プロンプトを書き換えます。

  使用例：
  ```bash
  ai -u https://sekika.github.io/2020/05/11/society50/
  ```

### 出力オプション

- **長い応答のページング:** 応答が端末の1ページを超える場合、`multiai`は[pypager](https://pypi.org/project/pypager/)を使用して表示します。

- **クリップボードへのコピー:** `-c`オプションを使用して、最後の応答をクリップボードにコピーします。`always_copy = yes`が`[command]`セクションで設定されている場合、このオプションは常に有効です。

  使用例：
  ```bash
  ai -c "What is the capital of France?"
  ```

- **チャットのログ保存:** `-l`オプションを使用して、チャットを現在のディレクトリにある`chat-ai-DATE.md`という名前のファイルに保存します。`DATE`は今日の日付に置き換えられます。ファイル名は、`[command]`セクションの`log_file`キーで変更できます。`always_log = yes`が設定されている場合、このオプションは常に有効です。

  使用例：
  ```bash
  ai -l Tell me a joke
  ```

### コマンドラインオプション

すべてのコマンドラインオプションの一覧を見るには、以下を使用します：

```bash
ai -h
```

より詳細なドキュメントを見るには、このマニュアル（英語版）をウェブブラウザで開くことができます：

```bash
ai -d
```

## Pythonライブラリとしての`multiai`の使用

`multiai`はPythonライブラリとしても使用できます。以下は簡単な例です：

```python
import multiai

# クライアントの初期化
client = multiai.Prompt()
# モデルとtemperatureの設定。省略するとデフォルト設定となる。
client.set_model('openai', 'gpt-4o')
client.temperature = 0.5

# プロンプトを送信して応答を取得
answer = client.ask('hi')
print(answer)

# 文脈を持った会話の継続
answer = client.ask('how are you')
print(answer)

# 会話の文脈をクリア
client.clear()
```

`client.ask`でエラーが発生した場合、エラーメッセージが返され、`client.error`が`True`に設定されます。

もう1つの例を示します。次のコードを `english.py` として保存してください。

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

たとえば、`text.md`という日本語のファイルがあったとします。次のコマンドを実行します。

```
python english.py text.md
```

すると、翻訳された英語が表示されます。結果を`output.md`というファイルに保存するには、リダイレクトを使って

```
python english.py text.md > output.md
```
とします。`pre_prompt`パラメータを変えることで、色々なスクリプトを作ることができます。

## ローカルチャットアプリの実行

`streamlit`を使用してローカルチャットアプリを実行できます。以下のコマンドを実行して`streamlit`をインストールしてください。
```bash
pip install streamlit
```

[app.py](https://github.com/sekika/multiai/blob/main/docs/app.py)をダウンロードして、以下のコマンドでローカルサーバーを起動してください。
```bash
streamlit run app.py
```

サーバーが起動すると、デフォルトのウェブブラウザが開き、チャットアプリケーション(Chotto GPT)が表示されます。このアプリでは、さまざまなプロバイダーからのAIモデルを簡単に選択し、それらと会話を楽しむことができます。利用可能なモデルのリストやログファイルの場所は、ソースコードを直接編集することでカスタマイズできます。
