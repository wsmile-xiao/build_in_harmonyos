"""TDD coverage for the legacy Aspell prezip v1 decoder and French normalization."""
from pathlib import Path
import sys
import tempfile
import unittest

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))
try:
    from conanfile import WordsFrConan
except (ImportError, ModuleNotFoundError) as exc:
    WordsFrConan = None
    IMPORT_FAILURE = exc
else:
    IMPORT_FAILURE = None


def require_recipe(test: unittest.TestCase):
    test.assertIsNotNone(
        WordsFrConan,
        f"words-fr recipe implementation is missing: {IMPORT_FAILURE}",
    )
    return WordsFrConan


class PrezipV1DecoderTests(unittest.TestCase):
    def decode(self, data: bytes) -> list[bytes]:
        recipe = require_recipe(self)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "fixture.cwl"
            path.write_bytes(data)
            return recipe._decode_cwl(path)

    def test_decodes_v1_prefix_delta_records_and_eof_final_record(self) -> None:
        self.assertEqual(self.decode(b"\x01cat\x03r"), [b"cat", b"car"])

    def test_decodes_extended_prefix_control(self) -> None:
        first = b"abcdefghijklmnopqrstuvwx"
        self.assertEqual(
            self.decode(b"\x01" + first + b"\x00\x19y"),
            [first, b"abcdefghijklmnopqrstuvwxy"],
        )

    def test_rejects_empty_or_wrong_version_header(self) -> None:
        for data in (b"", b"\x02cat"):
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.decode(data)

    def test_rejects_header_without_a_word(self) -> None:
        with self.assertRaises(ValueError):
            self.decode(b"\x01")

    def test_rejects_truncated_extended_prefix(self) -> None:
        with self.assertRaises(ValueError):
            self.decode(b"\x01cat\x00")

    def test_rejects_prefix_beyond_previous_record(self) -> None:
        with self.assertRaises(ValueError):
            self.decode(b"\x01a\x03z")

    def test_rejects_extended_prefix_beyond_previous_record(self) -> None:
        with self.assertRaises(ValueError):
            self.decode(b"\x01a\x00\xffx")

    def test_rejects_empty_record(self) -> None:
        with self.assertRaises(ValueError):
            self.decode(b"\x01\x01x")


class NormalizationTests(unittest.TestCase):
    def normalize(self, records: list[bytes]) -> list[str]:
        recipe = require_recipe(self)
        return recipe._normalize_words(records)

    def test_decodes_latin1_and_removes_affix_suffix(self) -> None:
        self.assertEqual(self.normalize([b"caf\xe9/PS"]), ["caf\u00e9"])

    def test_removes_everything_after_first_slash(self) -> None:
        self.assertEqual(self.normalize([b"foo/PS/extra"]), ["foo"])

    def test_rejects_empty_base_record(self) -> None:
        for record in (b"", b"/PS"):
            with self.subTest(record=record), self.assertRaises(ValueError):
                self.normalize([record])

    def test_collapses_duplicates_and_sorts_deterministically(self) -> None:
        records = [b"z", b"foo/PS", b"a", b"A", b"alpha", b"foo", b"\xe4"]
        self.assertEqual(
            self.normalize(records),
            ["\u00e4", "A", "a", "alpha", "foo", "z"],
        )


class SourceInputTests(unittest.TestCase):
    def source_inputs(self, source: Path) -> tuple[Path, Path]:
        recipe = require_recipe(self)
        self.assertTrue(
            callable(getattr(recipe, "_source_cwl_inputs", None)),
            "source input validation helper is missing",
        )
        return recipe._source_cwl_inputs(source)

    def make_source(self, root: Path, charset: str, filenames: tuple[str, ...]) -> None:
        (root / "fr.dat").write_text(f"charset {charset}\n", encoding="ascii")
        for filename in filenames:
            (root / filename).write_bytes(b"fixture")

    def test_requires_iso8859_charset_and_uses_only_fr60_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir)
            self.make_source(
                source,
                "iso8859-1",
                ("fr-40-only.cwl", "fr-60-only.cwl", "fr-80-only.cwl", "fr_CH-only.cwl"),
            )
            selected = self.source_inputs(source)
            self.assertEqual(
                [path.name for path in selected],
                ["fr-40-only.cwl", "fr-60-only.cwl"],
            )

    def test_rejects_unexpected_charset(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir)
            self.make_source(source, "utf-8", ("fr-40-only.cwl", "fr-60-only.cwl"))
            with self.assertRaises(ValueError):
                self.source_inputs(source)

    def test_rejects_missing_selected_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir)
            self.make_source(source, "iso8859-1", ("fr-40-only.cwl",))
            with self.assertRaises(ValueError):
                self.source_inputs(source)

    def test_rejects_missing_fr_dat(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir)
            (source / "fr-40-only.cwl").write_bytes(b"fixture")
            (source / "fr-60-only.cwl").write_bytes(b"fixture")
            with self.assertRaises(ValueError):
                self.source_inputs(source)

if __name__ == "__main__":
    unittest.main()
