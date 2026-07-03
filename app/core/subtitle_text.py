from __future__ import annotations

_TURKISH_FIRST_UPPER = str.maketrans("iıüşöçğ", "İIÜŞÖÇĞ")


def capitalize_first_char(char: str) -> str:
    if not char:
        return char
    lowered = char.lower()
    if lowered in "iıüşöçğ":
        return lowered.translate(_TURKISH_FIRST_UPPER)
    return char.upper()


def capitalize_subtitle_line(line: str) -> str:
    if not line:
        return line
    index = 0
    while index < len(line) and line[index].isspace():
        index += 1
    if index >= len(line):
        return line
    return line[:index] + capitalize_first_char(line[index]) + line[index + 1 :]


def capitalize_subtitle_text(text: str) -> str:
    if not text:
        return text
    return "\n".join(capitalize_subtitle_line(part) for part in text.split("\n"))


def capitalize_word_start(word: str) -> str:
    if not word:
        return word
    return capitalize_first_char(word[0]) + word[1:]
