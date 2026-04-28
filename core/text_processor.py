"""Post-processing pipeline for raw Tesseract output.

Handles:
- OCR artifact cleanup (noise lines, character substitutions)
- Spell correction (requires pyspellchecker)
- Table / tab-stop alignment
"""
import re
import logging

logger = logging.getLogger(__name__)

# Words that should never be "corrected" (technical / domain vocabulary)
_DOMAIN_WORDS = {
    'ocr', 'tesseract', 'jpeg', 'png', 'pdf', 'rgb', 'bgr', 'api',
    'url', 'http', 'https', 'json', 'xml', 'csv', 'html', 'css',
    'opencv', 'numpy', 'python', 'gui', 'usb', 'hdmi', 'cpu', 'gpu',
    'kb', 'mb', 'gb', 'tb', 'hz', 'mhz', 'ghz', 'rpm', 'dpi',
}

# Compiled patterns for common OCR character substitutions
_CHAR_FIXES = [
    (re.compile(r'(?<=[a-z])rn(?=[a-z])'), 'm'),   # rn → m between lowercase letters
    (re.compile(r'\bI(?=\d)'), '1'),                 # I before a digit → 1
    (re.compile(r'(?<=\d)l\b'), '1'),                # l after a digit at word end → 1
    (re.compile(r'(?<!\S)\|{2,}(?!\S)'), '|'),       # multiple pipes → single pipe
]


class TextProcessor:
    """Apply post-processing to raw OCR text."""

    def __init__(self):
        self._spell = None
        try:
            from spellchecker import SpellChecker
            self._spell = SpellChecker()
            self._spell.word_frequency.load_words(_DOMAIN_WORDS)
            logger.info("SpellChecker loaded.")
        except ImportError:
            logger.warning("pyspellchecker not installed — spell correction disabled.")

    def process(self, text: str, mode: str = "Plain text") -> str:
        """Run the full post-processing pipeline for the given content mode."""
        text = self._clean_artifacts(text)
        if mode == "Table":
            text = self._format_table(text)
        elif self._spell is not None:
            text = self._spell_correct(text)
        return text

    # ------------------------------------------------------------------
    # Internal passes
    # ------------------------------------------------------------------

    def _clean_artifacts(self, text: str) -> str:
        """Remove OCR noise and fix common character-level substitutions."""
        for pattern, replacement in _CHAR_FIXES:
            text = pattern.sub(replacement, text)
        # Collapse multiple spaces within a line (preserve newlines)
        text = re.sub(r'[^\S\n]+', ' ', text)
        # Drop lines that contain no alphanumeric content (pure symbol noise)
        lines = [l for l in text.splitlines()
                 if re.search(r'[A-Za-z0-9]', l) or l.strip() == '']
        # Collapse runs of more than two consecutive blank lines
        return re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip()

    def _spell_correct(self, text: str) -> str:
        """Apply word-level spell correction, preserving capitalisation."""
        if self._spell is None:
            return text

        def _fix(match: re.Match) -> str:
            word = match.group()
            # Skip: short words, ALL-CAPS acronyms, words with digits, domain terms
            if (len(word) <= 2
                    or word.isupper()
                    or not word.isalpha()
                    or word.lower() in _DOMAIN_WORDS):
                return word
            corrected = self._spell.correction(word)
            if corrected is None or corrected == word.lower():
                return word
            # Preserve original capitalisation pattern
            if word[0].isupper():
                return corrected.capitalize()
            return corrected

        return re.sub(r'\b[A-Za-z]+\b', _fix, text)

    def _format_table(self, text: str) -> str:
        """Align columns detected via tabs or two-or-more consecutive spaces."""
        lines = text.splitlines()
        rows = [re.split(r'\t|  +', line) for line in lines if line.strip()]
        if not rows:
            return text

        col_count = max(len(r) for r in rows)
        if col_count < 2:
            return text  # Not actually tabular — return as-is

        widths = [0] * col_count
        for row in rows:
            for i, cell in enumerate(row):
                widths[i] = max(widths[i], len(cell.strip()))

        formatted = []
        for row in rows:
            cells = [
                (row[i].strip() if i < len(row) else '').ljust(widths[i])
                for i in range(col_count)
            ]
            formatted.append('  '.join(cells))

        return '\n'.join(formatted)
