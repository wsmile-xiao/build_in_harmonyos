#!/usr/bin/env python3
"""Conan recipe for reniced 1.23.

reniced is a single-file Perl CLI that renices running processes based on
regular expressions from a config file.  There is no native compilation;
build() runs a Perl syntax check plus the upstream no-op mode test suite
(mock ps, no privileges required) when the host package can execute on the
current machine.

OHOS adaptations (documented in notes.md):
  - shebangs of the upstream test wrappers and mocked ps point to
    /bin/bash, which does not exist on OHOS (bash lives in
    /data/service/hnp/bin); tests run from a build-tree copy with
    rewritten, explicit interpreter invocation.
  - newly created files cannot be executed on the device regardless of
    permissions (SELinux label policy), so the reniced script and the
    mocked ps are always invoked through an explicit interpreter, and a
    one-line RENICED_PS_CMD override is injected into the packaged script
    so tests can substitute the ps command without exec'ing a mock file.
    Default behavior without the environment variable is unchanged.
"""
import os
import shutil
import stat
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv
from conan.tools.files import copy, get, save
from conan.tools.layout import basic_layout

# One-line OHOS adaptation injected into the packaged script: allow the ps
# command to be overridden through an environment variable.  Everything else
# in the script stays upstream verbatim.
_PS_OPEN_UPSTREAM = "    open PS, '-|', $cmdline or die \"can't open `$cmdline': $!\\n\";\n"
_PS_OPEN_PATCHED = (
    "    my $ps_cmd = defined $ENV{RENICED_PS_CMD} ? \"$ENV{RENICED_PS_CMD} $cmdline\" : $cmdline;\n"
    "    open PS, '-|', $ps_cmd or die \"can't open `$cmdline': $!\\n\";\n"
)

_MOCK_PS = r'''#!/data/service/hnp/bin/perl
# mocked ps command equivalent to upstream test/ps (invoked via explicit
# perl as a prefix to the original ps command line; the shebang is
# informational only)
shift @ARGV if @ARGV && $ARGV[0] eq 'ps';
my $argstring = join ':', '', @ARGV;
my $uid = $<;
if ($argstring eq ":H:-o:lwp,comm:--user:$uid") {
    print "     LWP COMMAND\n";
    print "     201 foo --quick\n";
    print "    2445 foo --slow\n";
    print "   19966 bar\n";
    print "   30176 bar --really --slow\n";
    print " 1234567 long-pid\n";
} else {
    print STDERR "ps called with unexpected parameters: ps$argstring\n";
    exit 1;
}
'''


class RenicedConan(ConanFile):
    name = "reniced"
    version = "1.23"
    description = "reniced renices running processes based on regular expressions"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/mmitch/reniced"
    url = "https://github.com/mmitch/reniced"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    _source_urls = [
        "https://ghfast.top/https://github.com/mmitch/reniced/archive/refs/tags/v1.23.tar.gz",
        "https://gh-proxy.com/https://github.com/mmitch/reniced/archive/refs/tags/v1.23.tar.gz",
        "https://mirror.ghproxy.com/https://github.com/mmitch/reniced/archive/refs/tags/v1.23.tar.gz",
        "https://github.com/mmitch/reniced/archive/refs/tags/v1.23.tar.gz",
    ]
    _source_sha256 = "237f8d54e3885eb0a4fad881ece5b51fbeaf74c63191ad0c9f017c38598be390"

    def requirements(self):
        self.requires("perl/5.42.2.3", headers=False, libs=False, run=True)

    def layout(self):
        basic_layout(self)

    def configure(self):
        self.settings.rm_safe("os.version")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"reniced supports Linux/OHOS style hosts, got {self.settings.os}"
            )

    def source(self):
        get(
            self,
            url=self._source_urls,
            sha256=self._source_sha256,
            strip_root=True,
        )

    def generate(self):
        VirtualRunEnv(self).generate()

    def _perl_path(self):
        perl = shutil.which("perl")
        if perl:
            return perl
        dep = os.path.join(self.dependencies["perl"].package_folder, "bin", "perl")
        return dep if os.path.isfile(dep) else "/data/service/hnp/bin/perl"

    def build(self):
        for relpath in ("reniced", "reniced.conf", "COPYRIGHT", "README.md"):
            path = os.path.join(self.source_folder, relpath)
            if not os.path.isfile(path):
                raise RuntimeError(f"upstream reniced artifact is missing: {relpath}")

        if not can_run(self):
            self.output.warning(
                "Cannot run host Perl on this build machine; upstream tests "
                "are deferred to native OHOS validation"
            )
            return

        self.run(f'"{self._perl_path()}" -c "reniced"', cwd=self.source_folder, env="conanrun")

        bash = shutil.which("bash")
        if bash is None:
            self.output.warning(
                "bash not found in PATH; upstream run-tests deferred to "
                "test_package no-op verification"
            )
            return

        # Upstream test suite: three no-op mode tests with a mocked ps.
        # Executed from a scratch copy because OHOS needs adapted invocation:
        #   - wrappers/mock ps shebang /bin/bash does not exist (bash is in
        #     /data/service/hnp/bin);
        #   - newly created files cannot be exec'd at all (SELinux labels),
        #     so ../reniced and the mocked ps run through an explicit
        #     interpreter and the ps command is overridden via RENICED_PS_CMD;
        #   - expected output is compared in Python (toybox diff lacks -p).
        perl = self._perl_path()
        harness_dir = tempfile.mkdtemp(prefix="reniced-upstream-")
        test_dir = os.path.join(harness_dir, "test")
        os.makedirs(test_dir)
        for name in ("test.conf", "show-help.expected", "normal-run.expected", "verbose-run.expected"):
            shutil.copy(os.path.join(self.source_folder, "test", name), os.path.join(test_dir, name))

        with open(os.path.join(self.source_folder, "reniced"), "r", encoding="utf-8") as src:
            script = src.read()
        if _PS_OPEN_UPSTREAM not in script:
            raise RuntimeError("ps invocation line not found in upstream reniced script")
        script = script.replace(_PS_OPEN_UPSTREAM, _PS_OPEN_PATCHED)
        script_path = os.path.join(harness_dir, "reniced")
        with open(script_path, "w", encoding="utf-8") as dst:
            dst.write(script)

        mock_ps = os.path.join(harness_dir, "mock-ps.pl")
        with open(mock_ps, "w", encoding="utf-8") as dst:
            dst.write(_MOCK_PS)

        import re

        for name in ("show-help", "normal-run", "verbose-run"):
            with open(os.path.join(self.source_folder, "test", f"{name}.test"), "r", encoding="utf-8") as fh:
                content = fh.read()
            # invoke the script through an explicit interpreter instead of
            # exec'ing ../reniced (which the device forbids); only the
            # invocation at line start is rewritten, never the ../reniced
            # argument of the grep that extracts the version number
            content, nsubst = re.subn(
                r"(?m)^(\s*)\.\./reniced ",
                lambda m: f'{m.group(1)}"{perl}" "{script_path}" ',
                content,
            )
            if nsubst != 1:
                raise RuntimeError(
                    f"expected exactly one ../reniced invocation in {name}.test, found {nsubst}"
                )
            path = os.path.join(test_dir, f"{name}.test")
            with open(path, "w", encoding="utf-8") as dst:
                dst.write(content)

        env_backup = dict(os.environ)
        os.environ["RENICED_PS_CMD"] = f'"{perl}" "{mock_ps}"'
        failures = []
        try:
            for name in ("show-help", "normal-run", "verbose-run"):
                self.output.info(f"running upstream test {name}")
                self.run(
                    f'"{bash}" "./{name}.test" > test-output.actual',
                    cwd=test_dir,
                    env="conanrun",
                )
                actual_path = os.path.join(test_dir, "test-output.actual")
                with open(actual_path, "r", encoding="utf-8", errors="replace") as fh:
                    actual = [ln.rstrip("\n") for ln in fh if ln.strip()]
                with open(os.path.join(test_dir, f"{name}.expected"), "r", encoding="utf-8", errors="replace") as fh:
                    expected = [ln.rstrip("\n") for ln in fh if ln.strip()]
                if actual != expected:
                    failures.append(name)
                    self.output.error(
                        f"upstream test {name} output differs:\n"
                        + "\n".join(f"- {ln}" for ln in expected[:6])
                        + "\n--- actual ---\n"
                        + "\n".join(f"+ {ln}" for ln in actual[:6])
                    )
        finally:
            os.environ.clear()
            os.environ.update(env_backup)
            shutil.rmtree(harness_dir, ignore_errors=True)
        if failures:
            raise RuntimeError(f"upstream reniced tests failed: {', '.join(failures)}")
        self.output.info("all 3 upstream reniced tests passed")

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        conf_dir = os.path.join(self.package_folder, "share", "reniced")
        doc_dir = os.path.join(self.package_folder, "share", "doc", "reniced")
        os.makedirs(bin_dir, exist_ok=True)
        os.makedirs(conf_dir, exist_ok=True)
        os.makedirs(doc_dir, exist_ok=True)

        with open(os.path.join(self.source_folder, "reniced"), "r", encoding="utf-8") as src:
            content = src.read()
        if _PS_OPEN_UPSTREAM not in content:
            raise RuntimeError("ps invocation line not found in upstream reniced script")
        content = content.replace(_PS_OPEN_UPSTREAM, _PS_OPEN_PATCHED)
        shebang = "#!/data/service/hnp/bin/perl" if str(self.settings.os) == "OHOS" else "#!/usr/bin/env perl"
        lines = content.splitlines()
        if lines and lines[0].startswith("#!"):
            lines[0] = shebang
        content = "\n".join(lines) + "\n"

        dst = os.path.join(bin_dir, "reniced")
        save(self, dst, content)
        os.chmod(dst, os.stat(dst).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

        copy(self, "reniced.conf", src=self.source_folder, dst=conf_dir, keep_path=False)
        copy(self, "README.md", src=self.source_folder, dst=doc_dir, keep_path=False)
        copy(self, "HISTORY", src=self.source_folder, dst=doc_dir, keep_path=False)
        copy(self, "COPYRIGHT", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        perl_bin = os.path.join(self.dependencies["perl"].package_folder, "bin")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.resdirs = ["share"]
        self.runenv_info.prepend_path("PATH", perl_bin)
        self.runenv_info.prepend_path("PATH", bin_dir)
