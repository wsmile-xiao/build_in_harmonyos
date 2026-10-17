#!/usr/bin/env python3
"""Conan recipe for signify 1.14 - random signature generator (Perl).

Upstream is a pure Perl script (signify.pl) with a simple Makefile that
does shebang rewriting via sed. No compilation is required.

OHOS adaptations:
  - Use /usr/bin/env perl shebang for portability (instead of which perl)
  - Install via file copy, not Makefile umask/mkdir logic
  - No upstream test suite (only examples/); declared as no_tests with audit
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class SignifyConan(ConanFile):
    name = "signify"
    version = "1.14"
    description = "Random signature generator for mail/news - generates semi-random signatures from rules"
    license = "public-domain"
    homepage = "http://signify.sf.net"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # OHOS: Use system perl (/data/service/hnp/bin/perl) to avoid conan perl 5.42.2 ABI mismatch
        # (conan perl XS modules like IO.so fail with Perl_croak_nocontext symbol not found on OHOS musl/BIND_NOW
        # because -Uuseshrplib builds static perl that doesn't export symbols for dlopen).
        # System perl is known to work for perl scripts on OHOS (see apertium/accel-config notes:
        # Cwd.so: Perl_my_cxt_init symbol not found with conan perl, system perl works).
        # No conan perl requirement; rely on system perl available on OHOS at /data/service/hnp/bin/perl.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        data = self.conan_data["sources"]
        # conandata may store sources as list (e.g. - url/sha256) or version-keyed dict; normalize to mapping
        if isinstance(data, list):
            data = data[0] if data else {}
        # version-keyed form: sources: "1.14": { url: ..., sha256: ... }
        if isinstance(data, dict) and str(self.version) in data:
            data = data[str(self.version)]
        elif isinstance(data, dict) and "url" not in data and "sha256" not in data and len(data) == 1:
            # single version key without explicit version match
            only_val = next(iter(data.values()))
            if isinstance(only_val, dict) and "url" in only_val:
                data = only_val
        get(self, **data, strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Pure Perl, no compilation. No upstream test suite to run.
        # HMBS evidence: emit no_tests marker here for first build; test_package re-emits on cache hits
        # (prevents missing marker when conan cache skips build()).
        try:
            import json as _json
            _up = {
                "status": "no_tests",
                "framework": "make",
                "command": "",
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "signify-1.14 audited: Makefile has no check/test target (default target only prints help); no tests/ directory; examples/ contains sample input files not test harness; tarball has no test source; make -n check fails with No rule to make target check"
            }
            print("HMBS_UPSTREAM_TEST_RESULT=" + _json.dumps(_up, ensure_ascii=False), flush=True)
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + _json.dumps(_up, ensure_ascii=False))
        except Exception:
            pass

    def package(self):
        src_pl = os.path.join(self.source_folder, "signify.pl")
        dst_bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(dst_bin_dir, exist_ok=True)
        with open(src_pl, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        lines = content.splitlines(True)
        if lines and lines[0].startswith("#!"):
            # OHOS: Prefer system perl at /data/service/hnp/bin/perl (avoids conan perl ABI mismatch
            # with XS modules like IO.so). Align recipe uses same strategy.
            if self.settings.os == "OHOS":
                lines[0] = "#!/data/service/hnp/bin/perl\n"
            else:
                lines[0] = "#!/usr/bin/env perl\n"
        content = "".join(lines)
        dst = os.path.join(dst_bin_dir, "signify")
        with open(dst, "w", encoding="utf-8", newline="\n") as out:
            out.write(content)
        os.chmod(dst, 0o755)
        copy(self, "signify.1", self.source_folder, os.path.join(self.package_folder, "share/man/man1"))
        copy(self, "*", os.path.join(self.source_folder, "examples"), os.path.join(self.package_folder, "share/signify/examples"))
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
