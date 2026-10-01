"""TDD coverage for Aspell Finnish prezip decoding and word normalization."""
from pathlib import Path
import sys
import tempfile
import unittest

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))
from conanfile import WordsFiConan  # noqa: E402


def write_fixture(data: bytes) -> Path:
    temp = tempfile.NamedTemporaryFile(delete=False)
    temp.write(data)
    temp.close()
    return Path(temp.name)


class PrezipDecoderTests(unittest.TestCase):
    def decode(self, data: bytes) -> list[bytes]:
        path = write_fixture(data)
        try:
            return WordsFiConan._decode_cwl(path)
        finally:
            path.unlink()

    def test_valid_prefix_delta_records(self) -> None:
        # v2, "cat", then prefix "ca" + "r" => "car", then terminator.
        self.assertEqual(self.decode(b"\x02\x00cat\x02r\x00\x1f\xff"), [b"cat", b"car"])

    def test_rejects_wrong_header(self) -> None:
        with self.assertRaises(ValueError):
            self.decode(b"\x01\x00cat\x00\x1f\xff")

    def test_rejects_prefix_beyond_previous_record(self) -> None:
        with self.assertRaises(ValueError):
            self.decode(b"\x02\x01x\x00\x1f\xff")

    def test_rejects_malformed_escape(self) -> None:
        with self.assertRaises(ValueError):
            self.decode(b"\x02\x00A\x1f\x40\x00\x1f\xff")

    def test_rejects_truncated_escape(self) -> None:
        with self.assertRaises(ValueError):
            self.decode(b"\x02\x00A\x1f")

    def test_rejects_missing_terminator(self) -> None:
        with self.assertRaises(ValueError):
            self.decode(b"\x02\x00cat")

    def test_rejects_bytes_after_terminator(self) -> None:
        with self.assertRaises(ValueError):
            self.decode(b"\x02\x00cat\x00\x1f\xffx")


class NormalizationTests(unittest.TestCase):
    def normalize(self, records: list[bytes]) -> list[str]:
        return WordsFiConan._normalize_words(records)

    def test_decodes_latin1_and_removes_affix_suffix(self) -> None:
        self.assertEqual(self.normalize([b"a\xf1o/PS"]), ["año"])

    def test_removes_everything_after_first_slash(self) -> None:
        self.assertEqual(self.normalize([b"foo/PS/extra"]), ["foo"])

    def test_rejects_empty_base_record(self) -> None:
        for record in (b"", b"/PS"):
            with self.subTest(record=record), self.assertRaises(ValueError):
                self.normalize([record])

    def test_collapses_duplicates_and_sorts_by_dictionary_key(self) -> None:
        records = [b"z", b"foo/PS", b"a", b"A", b"alpha", b"foo", b"\xe4"]
        self.assertEqual(self.normalize(records), ["\u00e4", "A", "a", "alpha", "foo", "z"])

    def test_sort_key_uses_ascii_folded_dictionary_key_then_utf8_bytes(self) -> None:
        self.assertLess(WordsFiConan._sort_key("A"), WordsFiConan._sort_key("a"))
        self.assertLess(WordsFiConan._sort_key("\u00e4"), WordsFiConan._sort_key("z"))


if __name__ == "__main__":
    unittest.main()
