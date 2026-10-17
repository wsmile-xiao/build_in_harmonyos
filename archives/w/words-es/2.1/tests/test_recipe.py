import importlib.util
import tempfile
import unittest
from pathlib import Path


RECIPE_PATH = Path(__file__).parents[1] / "conanfile.py"
SPEC = importlib.util.spec_from_file_location("words_es_conanfile", RECIPE_PATH)
RECIPE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RECIPE)


class PrezipDecoderTests(unittest.TestCase):
    def decode(self, data):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "es.cwl"
            source.write_bytes(data)
            return RECIPE.WordsEsConan._decode_cwl(source)

    def test_decodes_prefix_deltas_and_latin1(self):
        encoded = b"\x02\x00hola/S\x04s/S\x00a\xf1o/PS\x00\x1f\xff"

        self.assertEqual(
            self.decode(encoded),
            [b"hola/S", b"holas/S", b"a\xf1o/PS"],
        )

    def test_rejects_unknown_prezip_version(self):
        with self.assertRaisesRegex(ValueError, "prezip v2"):
            self.decode(b"\x01anything")

    def test_rejects_prefix_beyond_previous_word(self):
        with self.assertRaisesRegex(ValueError, "previous word"):
            self.decode(b"\x02\x01x\x00\x1f\xff")

    def test_rejects_invalid_escape(self):
        with self.assertRaisesRegex(ValueError, "escape"):
            self.decode(b"\x02\x00\x1fA\x00\x1f\xff")

    def test_rejects_missing_terminator(self):
        with self.assertRaisesRegex(ValueError, "no prezip terminator"):
            self.decode(b"\x02\x00hola/S")

    def test_normalizes_affixes_to_sorted_utf8_unique_words(self):
        words = RECIPE.WordsEsConan._normalize_words(
            [b"hola/S", b"a\xf1o/PS", b"hola/", b"\xe1rbol"]
        )

        self.assertEqual(words, ["año".encode(), b"hola", "árbol".encode()])


if __name__ == "__main__":
    unittest.main()
