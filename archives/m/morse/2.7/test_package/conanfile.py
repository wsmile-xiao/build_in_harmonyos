import os

from conan import ConanFile
from conan.tools.files import save


class MorseTestConan(ConanFile):
    """Consumer-side test for the morse 2.7 Conan package.

    Verifies the REAL installed `morse` / `QSO` CLIs (exposed on PATH
    through run_environment) against exact-output assertions derived
    from the upstream sources (morse.c getopt semantics, morse(1)):

      - morse -m -e: text -> on-screen Morse (exact dots/dashes)
      - morse -l -m -e: letter-by-letter scroll (exact pattern)
      - morse -c -m -e: complains on non-Morse chars (stderr, exit 1)
      - QSO: 16-line simulated QSO (callsign/RST/echo structure)
      - negative: unknown option -> usage on stderr, exit 1

    The audio sink (/dev/console) is redirected through the same
    build-time console shim used by the recipe's make check run (OHOS
    has no PC speaker); decoding/timing/output paths are fully real.
    """

    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # tests drive the prebuilt installed binaries directly

    def test(self):
        script = os.path.join(self.source_folder, "test.sh")
        # Compile the console shim into a throwaway temp dir: during
        # `conan create` the test_package build_folder IS its source
        # folder, and build residue there would pollute the repo.
        import tempfile
        tmpd = tempfile.mkdtemp(prefix="morse-shim-")
        shim_c = os.path.join(tmpd, "console_shim.c")
        shim_so = os.path.join(tmpd, "console_shim.so")
        save(self, shim_c, _CONSOLE_SHIM_C)
        cc = self._get_cc()
        self.run(f'"{cc}" -shared -fPIC -O2 -o "{shim_so}" "{shim_c}" -ldl')

        self.output.info("Running real morse/QSO CLI tests (test.sh)…")
        # LD_PRELOAD rides as a shell env prefix so the console shim
        # applies to the real morse/QSO binaries that test.sh execs.
        try:
            self.run(
                f'LD_PRELOAD="{shim_so}" bash "{script}"', env="conanrun"
            )
        finally:
            import shutil
            shutil.rmtree(tmpd, ignore_errors=True)
        self.output.info("All morse CLI tests passed.")

    def _get_cc(self):
        comp_execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return comp_execs.get("c") or "clang"


# Same build-time-only shim as the recipe: redirects the PC-speaker
# /dev/console open() to /dev/null on OHOS. Never installed.
_CONSOLE_SHIM_C = r"""
#include <fcntl.h>
#include <stdarg.h>
#include <string.h>
#include <dlfcn.h>

static int (*real_open)(const char *, int, ...);

int open(const char *path, int flags, ...) {
    if (!real_open) real_open = dlsym(RTLD_NEXT, "open");
    if (strcmp(path, "/dev/console") == 0) {
        return real_open("/dev/null", O_WRONLY);
    }
    va_list ap;
    va_start(ap, flags);
    mode_t m = va_arg(ap, mode_t);
    va_end(ap);
    return real_open(path, flags, m);
}
"""
