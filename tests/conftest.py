import pytest
from unittest.mock import MagicMock, patch
import sys
import os

# Add src directory to sys.path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

@pytest.fixture
def mock_config():
    """
    Mock configparser.ConfigParser to simulate configuration loading.
    This prevents the tests from depending on actual .ini files.
    """
    with patch('configparser.ConfigParser') as MockConfig:
        instance = MockConfig.return_value
        
        # Define default behavior for get()
        # Simulates content from system.ini or .multiai
        instance.get.side_effect = lambda section, key, fallback=None: {
            ('command', 'log_file'): 'test_log.md',
            ('command', 'user_agent'): 'test-agent',
            ('command', 'blank_lines'): '1',
            ('command', 'always_copy'): 'False',
            ('prompt', 'english'): 'Correct this English:',
            ('prompt', 'url'): 'Summarize this URL:',
            ('prompt', 'color'): 'GREEN',
            ('model', 'ai_provider'): 'OPENAI',
            ('model', 'openai'): 'gpt-4o',
            ('model', 'anthropic'): 'claude-3-5-sonnet',
            ('model', 'google'): 'gemini-1.5-pro',
            ('model', 'perplexity'): 'llama-3',
            ('model', 'mistral'): 'mistral-large',
            ('model', 'deepseek'): 'deepseek-chat',
            ('model', 'xai'): 'grok-beta',
            ('model', 'local'): 'llama3',
        }.get((section, key), fallback)

        # Mock getfloat
        instance.getfloat.return_value = 0.7
        
        # Mock getint
        instance.getint.side_effect = lambda section, key, fallback=None: {
            ('default', 'max_requests'): 3,
            ('default', 'max_tokens'): 1000,
            ('default', 'attach_char_limit'): 40000,
            ('command', 'blank_lines'): 1,
        }.get((section, key), fallback)

        # Mock getboolean
        instance.getboolean.return_value = False
        
        yield instance

@pytest.fixture
def mock_environment():
    """Mock environment variables for API keys."""
    with patch.dict(os.environ, {
        "OPENAI_API_KEY": "sk-dummy-openai",
        "ANTHROPIC_API_KEY": "sk-dummy-anthropic",
    }):
        yield
