import os
import shlex
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MalocConan(ConanFile):
    name = "maloc"
    version = "1.5"
    description = "Minimal Abstraction Layer for Object-oriented C (libmaloc)"
    license = "LGPL-2.1-or-later"
    homepage = "http://www.fetk.org/codes/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        if self.settings.os == "OHOS":
            # maloc bundles a 2005-era config.guess whose case table has no
            # aarch64 and no HarmonyOS branch; patch 0001 re-anchors both
            # scripts, and the explicit triplets below keep configure from
            # depending on native guessing at all.
            tc.configure_args.extend([
                "--build=aarch64-linux-ohos",
                "--host=aarch64-linux-ohos",
            ])
        tc.generate()
        # build() issues the OHOS configure call directly (see E386 shell
        # binding below), so the resolved argument list is kept here.  Same
        # approach as the merged logstalgia/1.1.4 recipe, which avoids the
        # Autotools private attributes.
        self._configure_args = list(tc.configure_args)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        if self.settings.os == "OHOS":
            # E386: on this platform /bin/sh (mksh) has a `print` builtin while
            # the CONFIG_SHELL injected by the profile (/data/service/hnp/bin/
            # bash, bash 5.3) does not.  configure detects "print -r" with the
            # shell that is running it and bakes ECHO='print -r' into
            # config.status, whose shebang is taken from CONFIG_SHELL -> the
            # two shells must be the same one.  The shell is therefore probed
            # from the real build directory first and then bound inline for
            # both configure and the config.status it generates.
            shell = self._capability_tested_shell()
            configure_script = os.path.join(self.source_folder, "configure")
            self._make_config_status_tmp_writable(configure_script)
            command = (
                f"CONFIG_SHELL={shell} SHELL={shell} "
                + shlex.join([shell, configure_script])
            )
            if self._configure_args:
                command += " " + " ".join(shlex.quote(a) for a in self._configure_args)
            self.run(command, cwd=self.build_folder)
        else:
            autotools.configure()
        # A single job avoids make jobserver/FIFO failures on HMDFS.
        autotools.make(args=["-j1"])

    def _capability_tested_shell(self):
        """Return a shell proven usable from *this* build directory (E386).

        Acceptance is `pwd` run as `<candidate> -c pwd` with cwd set to the
        real Conan build folder: exit code 0, empty diagnostics, and stdout
        equal to that folder (a getcwd failure would print a diagnostic even
        with exit code 0, so return codes alone prove nothing).
        """
        report = []
        chosen = None
        seen = set()
        for candidate in ("/bin/sh", "/system/bin/sh",
                          "/data/service/hnp/bin/bash", "/bin/bash"):
            if candidate in seen:
                continue
            seen.add(candidate)
            if not os.path.isfile(candidate):
                report.append(f"{candidate or '<empty>'}: absent")
                continue
            try:
                done = subprocess.run([candidate, "-c", "pwd"], cwd=self.build_folder,
                                      capture_output=True, text=True, timeout=60)
                printer = subprocess.run([candidate, "-c", "print -r -- z64"],
                                         capture_output=True, text=True, timeout=60)
            except (OSError, subprocess.SubprocessError) as exc:
                report.append(f"{candidate}: spawn-error {exc}")
                continue
            stdout = done.stdout.strip()
            usable = (done.returncode == 0 and done.stderr == ""
                      and stdout == self.build_folder)
            has_print = printer.returncode == 0 and printer.stdout.strip() == "z64"
            report.append(
                f"{candidate}: pwd rc={done.returncode} stderr={done.stderr.strip()!r} "
                f"stdout={stdout!r} print_builtin={has_print}")
            if usable and chosen is None:
                chosen = candidate
        for line in report:
            self.output.info("E386 shell probe: " + line)
        if chosen is None:
            raise ConanException(
                "no capability-tested shell for CONFIG_SHELL/SHELL: "
                + "; ".join(report))
        return chosen

    @staticmethod
    def _make_config_status_tmp_writable(path):
        """Make the embedded config.status temp directory writable on HMDFS.

        The autoconf template creates its scratch directory with
        `mktemp -d`, which is always mode 0700; on HMDFS the owner of a newly
        created directory is remapped to the folder owner while the build runs
        under the login uid, so even the process that just created the
        directory gets "Permission denied" when writing subs1.awk into it
        ("could not setup config files machinery").  Relaxing the umask around
        mktemp has no effect (the mode is forced), so the mktemp branch is
        replaced by the template's own fallback shape with an open umask, as
        recorded for cln/1.3.7; abx/0.1 and logstalgia/1.1.4 carry the same
        family of edit.
        """
        with open(path, "r", encoding="utf-8") as handle:
            content = handle.read()
        patched = content.replace(
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&\n'
            '  test -d "$tmp"\n',
            'tmp=./conf$$-$RANDOM &&\n'
            '  test -d "$tmp" || (umask 000 && mkdir "$tmp")\n',
        ).replace(
            '(umask 077 && mkdir "$tmp")',
            '(umask 000 && mkdir "$tmp")',
        )
        if patched == content:
            raise ConanException(
                "Autoconf config.status temporary-directory template changed: "
                f"no anchor found in {path}")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(patched)

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["maloc"]
        self.cpp_info.includedirs = ["include"]
        # Upstream declares bin_PROGRAMS = malocbridge in tools/Makefile.am:40,
        # but this recipe builds the library trees only: no bin/ artifact is
        # installed, so bindirs stays empty and the package ships a static
        # libmaloc.a plus headers (options.shared default = False).
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = ["lib"]
        if self.settings.os in ["Linux", "OHOS"]:
            self.cpp_info.system_libs = ["m"]
