# Chotto GPT - a chat communication tool that uses the multiai library.
# See instruction at https://sekika.github.io/multiai/

import clipboard
import multiai
import os
import streamlit as st
import sys
from datetime import datetime

# Page config
st.set_page_config(page_title='Chotto GPT')
document_url = 'https://sekika.github.io/multiai/'

# Models (editable)
models = [
    'gpt-5.5',
    'claude-opus-4-8',
    'claude-sonnet-4-6',
    'gemini-3.5-flash',
    'sonar-pro',
    'sonar',
    'deepseek-chat',
    'deepseek-reasoner',
    'grok-4-latest'
]

# Log file
log_file = 'chat-ai-DATE.md'
log_file = os.path.expanduser(log_file)
log_file = log_file.replace('DATE', datetime.today().strftime('%Y%m%d'))

# Helper: provider by model prefix


def get_provider(model):
    if 'mistral' in model:
        return 'mistral'
    p = {
        'gp': 'openai',
        'cl': 'anthropic',
        'ge': 'google',
        'so': 'perplexity',
        'de': 'deepseek',
        'gr': 'xai'}
    if model[:2] in p:
        return p[model[:2]]
    st.write(f'''System message: `get_provider` function cannot get
              provider name from the model name `{model}`.
              Check model name or `get_provider` function.''')
    sys.exit()

# Button callbacks


def btn_copy(text):
    clipboard.copy(text)


def btn_clear():
    client.clear()
    st.session_state['chat_messages'] = []


# Init client
if st.session_state.get('client') is None:
    st.session_state['client'] = multiai.Prompt()
    st.session_state['chat_messages'] = []
    initial = True
else:
    initial = False
client = st.session_state['client']

# Model selector
model = st.selectbox(
    label='model',
    options=models,
    label_visibility='collapsed')
provider = get_provider(model)
client.set_model(provider, model)

# Save log checkbox
save_log = st.checkbox('Save log file')

# Sticky header
header = st.container()
if initial:
    header.title('Chotto GPT')
else:
    header.title(f"Chat with {client.model}")
header.write("""<div class='fixed-header'/>""", unsafe_allow_html=True)

st.markdown(
    """
<style>
    div[data-testid="stVerticalBlock"] div:has(div.fixed-header) {
        position: sticky;
        top: 2.875rem;
        background-color: white;
        z-index: 999;
    }
    .fixed-header {
        border-bottom: 1px solid black;
    }
</style>
    """,
    unsafe_allow_html=True
)

# Welcome message
if initial:
    st.write(
        f'''Welcome to `Chotto GPT`, a chat communication tool that uses
        the [multiai]({document_url}) library (version {client.version}).
        Select a model from the menu above. You can modify the list by
        editing the `models` parameter in the source code. If you check
        "Save log file," the file will be saved to `{log_file}`.
        You can change the location by editing the `log_file` parameter.'''
    )

# Provider change notice
if len(st.session_state['chat_messages']) > 0:
    if provider != st.session_state['provider']:
        st.write('''Your chat history has been cleared because you switched
                AI providers. Chat history is stored separately for each
                provider. You can continue conversations with different
                models from the same provider, but not with models from
                different providers.''')
        btn_clear()
st.session_state['provider'] = provider

# File uploader (in-memory processing only)
st.subheader('Attachments')
uploaded_files = st.file_uploader(
    "Upload files (any extension; non-text or unsupported formats will be rejected)",
    accept_multiple_files=True)
include_attachments = st.checkbox(
    "Include uploaded files in next message", value=True)

# Use a safe default in case the installed multiai is older
attach_limit_default = getattr(client, 'attach_char_limit', 40000)
attach_limit = st.number_input(
    "Attachment character limit (per file)",
    value=attach_limit_default,
    min_value=1000,
    step=1000
)

# Show uploaded file names
if uploaded_files:
    st.write("Uploaded:", ", ".join([f.name for f in uploaded_files]))

# Reload chat messages
for i, message in enumerate(st.session_state['chat_messages']):
    with st.chat_message(message['role']):
        st.write(message['content'])
        if message['role'] == 'assistant':
            st.button(
                "📋 Copy",
                key=f"copy_history_{i}",
                on_click=btn_copy,
                args=(message['content'],)
            )

# Input and reply
if message := st.chat_input():
    # Build attachment section (in-memory)
    attachments_section = ''
    attached_names = []
    if include_attachments and uploaded_files:
        blocks = []
        for f in uploaded_files:
            try:
                raw = f.getvalue()
                text = client.retrieve_from_file(
                    raw, filename=f.name, verbose=False)
                n = len(text)
                if n > attach_limit:
                    st.info(
                        f'Attachment "{f.name}" has {n} characters and exceeds the limit {attach_limit}. Summarizing the attachment.')
                    # Summarize using the current model without polluting
                    # history
                    text = client.summarize_text(text)
                blocks.append(f'=== Attachment: {f.name} ===\n{text}')
                attached_names.append(f.name)
            except Exception as e:
                st.warning(f'Failed to process {f.name}: {e}')
        if blocks:
            attachments_section = '\n\n'.join(blocks)

    # Show user message
    st.chat_message('user').write(message)
    st.session_state['chat_messages'].append(
        {'role': 'user', 'content': message})

    # Build final prompt
    final_prompt = message
    prompt_summary = message
    if attachments_section:
        final_prompt = message + '\n\n' + attachments_section
        prompt_summary = f'{message}\n\nAttachments: {", ".join(attached_names)}'

    with st.spinner('Waiting for response ...'):
        answer = client.ask(final_prompt)

    # Show assistant message
    st.chat_message('assistant').write(answer)
    st.session_state['chat_messages'].append(
        {'role': 'assistant', 'content': answer})

    # Action buttons (only copy and clear; no downloads)
    col1, col2 = st.columns(2)
    with col1:
        st.button("📋 Copy", on_click=btn_copy, args=(answer,))
    with col2:
        st.button("🗑️ Clear", on_click=btn_clear)

    # Write log file if requested (does not persist uploaded files)
    if save_log:
        log = f'### user:\n{prompt_summary}\n### {model}:\n{answer}\n'
        if not os.path.exists(log_file):
            with open(log_file, 'w') as f:
                f.write("# AI chat log\n\n")
        with open(log_file, mode='a') as f:
            f.write(log)
