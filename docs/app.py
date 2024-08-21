# Chotto GPT - a chat communication tool that uses the multiai library.
# See instruction at https://sekika.github.io/multiai/

import clipboard
import multiai
import os
import streamlit as st
import sys
from datetime import datetime

# Edit settings here
st.set_page_config(page_title='Chotto GPT')
document_url = 'https://sekika.github.io/multiai/'
models = [
    'gpt-4o',
    'gpt-4o-mini',
    'claude-3-5-sonnet-20240620',
    'claude-3-haiku-20240307',
    'gemini-1.5-pro',
    'gemini-1.5-flash',
    'llama-3.1-sonar-huge-128k-online',
    'llama-3.1-sonar-small-128k-chat',
    'mistral-large-latest',
    'open-mistral-nemo']

log_file = 'chat-ai-DATE.md'
log_file = os.path.expanduser(log_file)
log_file = log_file.replace('DATE', datetime.today().strftime('%Y%m%d'))

# Function to get provider name from model name
def get_provider(model):
    if 'mistral' in model:
        return 'mistral'
    p = {'gp': 'openai', 'cl': 'anthropic', 'ge': 'google', 'll': 'perplexity'}
    if model[:2] in p:
        return p[model[:2]]
    st.write(f'''System message: `get_provider` function cannot get
              provider name from the model name `{model}`.
              Check model name or `get_provider` function.''')
    sys.exit()

# Functions for pressing buttons
def btn_copy(text):
    clipboard.copy(text)

def btn_clear():
    client.clear()
    st.session_state['chat_messages'] = []

# Reload client
if st.session_state.get('client') is None:
    st.session_state['client'] = multiai.Prompt()
    st.session_state['chat_messages'] = []
    initial = True
else:
    initial = False
client = st.session_state['client']
model = st.selectbox(label='model', options=models,
                     label_visibility='collapsed')
provider = get_provider(model)
client.set_model(provider, model)
save_log = st.checkbox('Save log file')

# Write sticky header
# https://discuss.streamlit.io/t/is-it-possible-to-create-a-sticky-header/33145/3
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
        You can change the location by editing the `log_file` parameter.''')

# Check if provider is changed
if len(st.session_state['chat_messages']) > 0:
    if provider != st.session_state['provider']:
        st.write('''Your chat history has been cleared because you switched
                AI providers. Chat history is stored separately for each
                provider. You can continue conversations with different
                models from the same provider, but not with models from
                different providers.''')
        btn_clear()
st.session_state['provider'] = provider

# Reload chat messages
if st.session_state.get('chat_messages') is None:
    st.session_state['chat_messages'] = []
for message in st.session_state['chat_messages']:
    st.chat_message(message['role']).write(message['content'])

# Write input and reply
if message := st.chat_input():
    st.chat_message('user').write(message)
    st.session_state['chat_messages'].append(
        {'role': 'user', 'content': message})
    with st.spinner('Waiting for response ...'):
        answer = client.ask(message)
    st.chat_message('assistant').write(answer)
    st.session_state['chat_messages'].append(
        {'role': 'assistant', 'content': answer})
    # Copy and clear button
    col1, col2 = st.columns(2)
    with col1:
        st.button("📋", on_click=btn_copy, args=(answer,))
    with col2:
        st.button("🗑️", on_click=btn_clear)
    # Write log file
    if save_log:
        log = f'### user:\n{message}\n### {model}:\n{answer}\n'
        if not os.path.exists(log_file):
            with open(log_file, 'w') as f:
                f.write("# AI chat log\n\n")
        with open(log_file, mode='a') as f:
            f.write(log)
