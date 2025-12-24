import pytest
from unittest.mock import patch, MagicMock
import sys
from multiai.entry import entry
from multiai.multiai import Provider

class TestEntryCLI:

    @patch('multiai.entry.Prompt')
    @patch('multiai.entry.sys.argv', ['ai', 'hello world'])
    def test_entry_simple_prompt(self, MockPrompt, mock_config):
        """Test simple CLI usage: ai "hello world" """
        mock_client = MockPrompt.return_value
        # Mock default client attributes
        mock_client.ai_provider = Provider.OPENAI
        mock_client.ai_providers = []
        mock_client.always_copy = False
        mock_client.always_log = False
        mock_client.role = 'user'
        mock_client.color.return_value = '' 

        entry()

        # Ensure ask_print was called with the prompt
        mock_client.ask_print.assert_called()
        args, _ = mock_client.ask_print.call_args
        assert "hello world" in args[0]

    @patch('multiai.entry.Prompt')
    @patch('multiai.entry.sys.argv', ['ai', '-o', 'hello'])
    def test_entry_provider_flag(self, MockPrompt, mock_config):
        """Test provider flags: ai -o (OpenAI)"""
        mock_client = MockPrompt.return_value
        mock_client.ai_provider = Provider.OPENAI # default
        mock_client.ai_providers = []
        mock_client.always_copy = False
        mock_client.always_log = False
        
        entry()
        
        # Check if the CLI logic updated the ai_providers list
        assert Provider.OPENAI in mock_client.ai_providers

    @patch('multiai.entry.Prompt')
    @patch('multiai.entry.os.path.exists', return_value=True)
    @patch('multiai.entry.sys.argv', ['ai', 'summarize', '-f', 'doc.txt'])
    def test_entry_file_attachment(self, mock_exists, MockPrompt, mock_config):
        """Test file attachment: ai summarize -f doc.txt"""
        mock_client = MockPrompt.return_value
        mock_client.ai_provider = Provider.OPENAI
        mock_client.ai_providers = []
        mock_client.always_copy = False
        mock_client.always_log = False
        mock_client.attach_char_limit = 50000
        
        # Mock return value of file retrieval
        mock_client.retrieve_from_file.return_value = "File Content Here"

        entry()

        # Ensure retrieval was called
        mock_client.retrieve_from_file.assert_called_with('doc.txt', verbose=True)
        
        # Ensure the prompt passed to ask_print contains the attachment
        args, _ = mock_client.ask_print.call_args
        prompt_sent = args[0]
        assert "=== Attachment: doc.txt ===" in prompt_sent
        assert "File Content Here" in prompt_sent

    @patch('multiai.entry.Prompt')
    @patch('multiai.entry.sys.argv', ['ai']) # No arguments
    def test_entry_interactive_mode(self, MockPrompt, mock_config):
        """Test interactive mode when no prompt is provided."""
        mock_client = MockPrompt.return_value
        mock_client.ai_provider = Provider.OPENAI
        mock_client.ai_providers = []
        mock_client.always_copy = False
        mock_client.always_log = False

        entry()

        # interactive() method should be called
        mock_client.interactive.assert_called_once()
