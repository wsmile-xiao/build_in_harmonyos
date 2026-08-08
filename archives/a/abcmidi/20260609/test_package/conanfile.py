from conan import ConanFile


class AbcMidiTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "sample.abc", "verify_midi.py", "verify_abc.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        self.run("abc2midi sample.abc -o sample.mid", env="conanrun")
        self.run("python3 verify_midi.py sample.mid")
        self.run("midi2abc sample.mid > roundtrip.abc", env="conanrun")
        self.run("python3 verify_abc.py roundtrip.abc")
