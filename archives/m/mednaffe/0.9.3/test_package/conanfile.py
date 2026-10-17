import glob
import os

from conan import ConanFile


class MednaffeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # VirtualRunEnv's conanrun.sh carries the conan closure only. The GTK
        # tree's C++ bits (pango/harfbuzz) may DT_NEEDED libc++_shared.so
        # from the OHOS SDK sysroot, and unversioned libffi.so may live only
        # in the HNP install (same closure gap documented by the klavaro/3.14
        # consumer test). Prepend those globs when present — no-op on hosts
        # that do not ship them.
        runsh = os.path.join(self.generators_folder, "conanrun.sh")
        if os.path.isfile(runsh):
            text = open(runsh, encoding="utf-8", errors="ignore").read()
            prepend = ""
            for extra_glob in (
                "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib/"
                "aarch64-linux-ohos",
                "/data/service/hnp/libffi.org/*/lib",
            ):
                extra = sorted(glob.glob(extra_glob))
                if extra:
                    prepend += ('export LD_LIBRARY_PATH="' + extra[0]
                                + ':$LD_LIBRARY_PATH"\n')
            if prepend and "hnp/" not in text:
                # Prepend (klavaro/3.14 pattern): appending would glue onto a
                # missing trailing newline and break `.` sourcing in conanrun.sh.
                with open(runsh, "w", encoding="utf-8") as f:
                    f.write(prepend + text)
                self.output.info("Augmented conanrun.sh with SDK/hnp lib paths")
        self.run('sh "%s"' % os.path.join(self.recipe_folder, "test.sh"),
                 env="conanrun")
