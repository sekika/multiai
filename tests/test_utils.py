from multiai.printlong import calculate_display_width, wrap_text

def test_calculate_display_width():
    # ASCII characters have width 1
    assert calculate_display_width("abc") == 3
    # Wide East Asian characters have width 2
    assert calculate_display_width("あいう") == 6
    # Mixed characters
    assert calculate_display_width("aあb") == 4

def test_wrap_text():
    text = "あいうえお"
    # Wrap at width 4 -> "あい", "うえ", "お" (Since "あ" is width 2)
    wrapped = wrap_text(text, 4)
    assert wrapped == ["あい", "うえ", "お"]
    
    text2 = "abcde"
    # Wrap at width 3 -> "abc", "de"
    wrapped2 = wrap_text(text2, 3)
    assert wrapped2 == ["abc", "de"]
