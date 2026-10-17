from pathlib import Path
from tempfile import TemporaryDirectory

from in_place import InPlace


with TemporaryDirectory() as directory:
    target = Path(directory) / "sample.txt"
    target.write_text("alpha\nbeta\n", encoding="utf-8")
    with InPlace(target, encoding="utf-8") as stream:
        for line in stream:
            stream.write(line.upper())
    assert target.read_text(encoding="utf-8") == "ALPHA\nBETA\n"

print("in-place consumer: passed")
