"""
print_long - print long text with pypager
"""
import shutil
import unicodedata
import pypager


def print_long(text):
    """
    Print long text with pypager.

    When text fits in 1 page in a terminal, it uses print,
    otherwise it uses pypager.

    :param text: str
        text to display
    """
    default_terminal_size = (80, 20)
    terminal_size = shutil.get_terminal_size(default_terminal_size)
    lines_per_page = terminal_size.lines - 1
    terminal_width = terminal_size.columns
    wrapped_lines = []
    for line in text.split('\n'):
        wrapped_lines.extend(wrap_text(line, terminal_width))
    total_lines = len(wrapped_lines)
    wrapped_text = '\n'.join(wrapped_lines)
    if total_lines <= lines_per_page:
        print(text)
    else:
        p = pypager.pager.Pager()
        p.add_source(pypager.source.StringSource(wrapped_text))
        p.run()


def calculate_display_width(text):
    """
    Calculate display width of a line.

    :param text: str
        text to count
    """
    width = 0
    for char in text:
        if unicodedata.east_asian_width(char) in 'WF':
            width += 2
        else:
            width += 1
    return width


def wrap_text(text, width):
    """
    Wrap text of a line.

    :param text: str
        text to wrap
    :param width: int
        display width
    """
    lines = []
    current_line = ""
    current_width = 0
    for line in text.split('\n'):
        if not line:
            lines.append("")
            continue
        for char in line:
            char_width = 2 if unicodedata.east_asian_width(char) in 'WF' else 1
            if current_width + char_width > width:
                lines.append(current_line)
                current_line = char
                current_width = char_width
            else:
                current_line += char
                current_width += char_width
        if current_line:
            lines.append(current_line)
            current_line = ""
            current_width = 0
    if current_line:
        lines.append(current_line)
    return lines
