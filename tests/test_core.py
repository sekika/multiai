import pytest
from unittest.mock import MagicMock, patch, mock_open
from multiai.multiai import Prompt, Provider

class TestPromptCore:
    
    def test_initialization(self, mock_config, mock_environment):
        """Test if the Prompt class initializes correctly with mocked config."""
        client = Prompt()
        assert client.ai_provider == Provider.OPENAI
        assert client.model_openai == 'gpt-4o'
        assert client.openai_api_key == 'sk-dummy-openai'
        assert client.temperature == 0.7

    def test_set_provider(self, mock_config, mock_environment):
        """Test switching AI providers."""
        client = Prompt()
        client.set_provider('ANTHROPIC')
        assert client.ai_provider == Provider.ANTHROPIC

        # Test invalid provider calls sys.exit(1)
        with pytest.raises(SystemExit):
            client.set_provider('INVALID_PROVIDER')

    @patch('multiai.multiai.openai.chat.completions.create')
    def test_ask_openai(self, mock_create, mock_config, mock_environment):
        """Test the logic for asking OpenAI (mocking the API response)."""
        # Mock the OpenAI response object structure
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Hello, world!"
        mock_response.choices[0].finish_reason = "stop"
        mock_create.return_value = mock_response

        client = Prompt()
        client.set_provider('OPENAI')
        
        # FIX: The Prompt class requires .model to be set before calling ask_openai.
        client.model = client.model_openai

        response = client.ask("Hi")

        assert response == "Hello, world!"
        assert len(client.openai_messages) == 2  # user message + assistant response
        assert client.openai_messages[0]['content'] == "Hi"

    def test_retrieve_from_file_text(self, mock_config, tmp_path):
        """Test retrieving text from a standard text file."""
        client = Prompt()
        
        # Create a temporary text file
        p = tmp_path / "hello.txt"
        p.write_text("Hello file content", encoding="utf-8")
        
        text = client.retrieve_from_file(str(p), verbose=False)
        assert text == "Hello file content"

    # Changed from PyPDF2.PdfReader to pypdf.PdfReader
    @patch('multiai.multiai.pypdf.PdfReader')
    def test_retrieve_from_file_pdf(self, mock_pdf_reader, mock_config):
        """Test PDF extraction logic (mocking pypdf)."""
        client = Prompt()
        
        # Mock PDF reader behavior
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "PDF Page Content"
        mock_pdf_instance = mock_pdf_reader.return_value
        mock_pdf_instance.pages = [mock_page]

        # Use mock_open to bypass actual file reading, passing bytes for PDF check
        with patch('builtins.open', mock_open(read_data=b'%PDF-1.4...')) as m:
            text = client.retrieve_from_file("dummy.pdf", verbose=False)
            assert "PDF Page Content" in text

    @patch('multiai.multiai.Prompt.ask_once')
    def test_summarize_text(self, mock_ask_once, mock_config, mock_environment):
        """Test the summarization helper."""
        client = Prompt()
        mock_ask_once.return_value = "Summarized content"
        
        long_text = "A" * 50000
        result = client.summarize_text(long_text)
        
        assert result == "Summarized content"
        mock_ask_once.assert_called_once()
