from conan import ConanFile
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout

import os

REQUIRED_ASSERTIONS = 8   # product assertions only; keep in sync with MANIFEST.yml,
                          # notes.md 4, 34/manifest.yaml test_package, software manifest tests:
PLATFORM_OBSERVATIONS = 1   # unix_bind_probe: platform, not the deliverable -> never counted


class InputlircTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self, src_folder="src")

    def generate(self):
        AutotoolsToolchain(self).generate()

    def build(self):
        # Compile the consumer probe with the same toolchain the package used.
        # CC comes from the generated AutotoolsToolchain environment; fall back to
        # clang (the profile's compiler) rather than to a bare "cc", which does not
        # exist on this image.
        src = os.path.join(self.recipe_folder, "unix_bind_probe.c")
        out_bin = os.path.join(self.build_folder, "unix_bind_probe")
        cmd = '"${CC:-clang}" -O1 -w "%s" -o "%s"' % (src, out_bin)
        self.run(cmd, env="conan")
        if not os.path.isfile(out_bin):
            raise Exception("probe was not produced: %s" % out_bin)

    def test(self):
        script = os.path.join(self.recipe_folder, "test_inputlirc.sh")
        if not os.path.isfile(script):
            raise Exception("missing consumer test script: %s" % script)
        dep = self.dependencies["inputlirc"]
        bindirs = dep.cpp_info.bindirs or ["bin"]
        binary = None
        for b in bindirs:
            d = b if os.path.isabs(b) else os.path.join(dep.package_folder, b)
            cand = os.path.join(d, "inputlircd")
            if os.path.isfile(cand):
                binary = cand
                break
        if binary is None:
            raise Exception("inputlircd not found under %s (bindirs=%s)"
                            % (dep.package_folder, bindirs))
        self.output.info("testing binary: %s" % binary)
        os.chdir(self.build_folder)
        self.run("bash '%s' '%s' '%s'" % (script, binary,
                                          os.path.join(self.build_folder,
                                                       "unix_bind_probe")),
                 env="conan")
        self.output.info("consumer assertions required: >= %d" % REQUIRED_ASSERTIONS)
