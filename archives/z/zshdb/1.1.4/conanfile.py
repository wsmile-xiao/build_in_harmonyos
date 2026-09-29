"""zshdb 1.1.4 for HarmonyOS PC's minimal zsh installation."""

import os
import shlex
import shutil
import tempfile

from conan import ConanFile
from conan.tools.files import copy, get, replace_in_file
from conan.tools.layout import basic_layout


class ZshdbConan(ConanFile):
    name = "zshdb"
    version = "1.1.4"
    description = "Command-line debugger for zsh scripts"
    homepage = "https://github.com/Trepan-Debuggers/zshdb"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    license = "GPL-2.0-or-later AND GPL-3.0-or-later AND HPND-sell-variant"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "functions/*", "test_fixtures/*"

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        source = self.source_folder
        # The 1.1.4 release tarball lists the integration test but omits
        # its three fixtures. Restore byte-identical files from the same
        # upstream 1.1.4 Git tag; do not fabricate expected output.
        fixtures = os.path.join(self.export_sources_folder, "test_fixtures")
        copy(self, "bug-step-subshell.cmd", fixtures,
             os.path.join(source, "test", "data"), keep_path=False)
        copy(self, "bug-step-subshell.right", fixtures,
             os.path.join(source, "test", "data"), keep_path=False)
        copy(self, "bug-step-subshell.sh", fixtures,
             os.path.join(source, "test", "example"), keep_path=False)

        # The system zsh has neither its standard is-at-least autoload
        # function nor the optional zsh/mapfile module. Read source files
        # with zsh's native newline splitting when mapfile is unavailable.
        filecache = os.path.join(source, "lib", "filecache.sh")
        replace_in_file(
            self, filecache,
            "zmodload -ap zsh/mapfile mapfile &> /dev/null",
            r'''typeset -i _Dbg_have_mapfile=0
zmodload zsh/mapfile >/dev/null 2>&1 && _Dbg_have_mapfile=1

_Dbg_read_file_array() {
    typeset raw="$(cat -- "$1"; printf '\001')"
    raw=${raw%$'\001'}
    typeset -a lines
    lines=( "${(f@)raw}" )
    set -A "$2" "${lines[@]}"
}''',
        )
        replace_in_file(
            self, filecache,
            r'''eval "$_Dbg_source_array_var=( \"\${(f@)mapfile[$fullname]}\" )"''',
            r'''if (( _Dbg_have_mapfile )); then
                eval "$_Dbg_source_array_var=( \"\${(f@)mapfile[$fullname]}\" )"
            else
                _Dbg_read_file_array "$fullname" "$_Dbg_source_array_var"
            fi''',
        )
        replace_in_file(
            self, filecache,
            r'''eval "$_Dbg_highlight_array_var=( \"\${(f@)mapfile[$tempfile]}\" )"''',
            r'''if (( _Dbg_have_mapfile )); then
                        eval "$_Dbg_highlight_array_var=( \"\${(f@)mapfile[$tempfile]}\" )"
                    else
                        _Dbg_read_file_array "$tempfile" "$_Dbg_highlight_array_var"
                    fi''',
        )
        for name in ("zshdb.in", "dbg-trace.sh.in"):
            replace_in_file(
                self, os.path.join(source, name),
                "typeset _Dbg_libdir=@PKGDATADIR@",
                'typeset _Dbg_libdir="${0:A:h}/../share/zshdb"; fpath=($_Dbg_libdir/functions $fpath)',
            )
        replace_in_file(
            self, os.path.join(source, "dbg-opts.sh"),
            "[[ -z $_Dbg_tmpdir ]] && typeset _Dbg_tmpdir=/tmp",
            "[[ -z $_Dbg_tmpdir ]] && typeset _Dbg_tmpdir=${TMPDIR:-/tmp}",
        )
        # This build of zsh has no PCRE capture module: =~ can report a
        # match but BASH_REMATCH is empty. Preserve eval? extraction using
        # the system's POSIX sed instead of silently evaluating empty text.
        replace_in_file(
            self, os.path.join(source, "lib", "fns.sh"),
            'orig="$1"\n    if [[ $orig =~',
            r'''orig="$1"
    extracted=$(printf '%s\n' "$orig" | sed -nE 's/^[[:blank:]]*(if|elif)[[:blank:]]+([^;]*)(;[[:blank:]]*then?)?$/\2/p')
    [[ -n $extracted ]] && return
    extracted=$(printf '%s\n' "$orig" | sed -nE 's/^[[:blank:]]*while[[:blank:]]+([^;]*)(;[[:blank:]]*do?)?$/\1/p')
    [[ -n $extracted ]] && return
    extracted=$(printf '%s\n' "$orig" | sed -nE 's/^[[:blank:]]*return[[:blank:]]+(.*)$/echo \1/p')
    [[ -n $extracted ]] && return
    extracted=$(printf '%s\n' "$orig" | sed -nE 's/^[[:blank:]]*[A-Za-z_][A-Za-z0-9_]*(\[[^]]+\])?(\+)?=(.*)$/echo \3/p')
    [[ -n $extracted ]] && return
    if [[ $orig =~''',
        )
        # The target zsh lacks the optional PCRE module. The patterns in this
        # particular test are POSIX extended expressions and work without it.
        replace_in_file(
            self, os.path.join(source, "test", "unit", "test-lib-eval.sh.in"),
            "setopt ksharrays bashrematch rematchpcre",
            "setopt ksharrays bashrematch",
        )
        # Preserve the upstream comparisons while placing their temporary
        # filtered files under the writable Conan build directory.
        replace_in_file(
            self, os.path.join(source, "test", "integration", "check-common.sh.in"),
            '"/tmp/${', '"${TMPDIR:-/tmp}/${',
        )
        replace_in_file(
            self, os.path.join(source, "test", "integration", "test-debug.in"),
            '"/tmp/${', '"${TMPDIR:-/tmp}/${',
        )

    def build(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise RuntimeError("This recipe is verified for HarmonyOS PC AArch64 only")
        with tempfile.TemporaryDirectory(prefix="zshdb-build-", dir="/data/storage/el2/base/cache") as work:
            shutil.copytree(self.source_folder, work, dirs_exist_ok=True)
            temp = shlex.quote(work)
            funcs = shlex.quote(os.path.join(work, "functions"))
            self.run(
                f"TMPDIR={temp} FPATH={funcs} ./configure --prefix=/ --with-zsh=/usr/bin/zsh",
                cwd=work,
            )
            self.run("make -j1", cwd=work)
            self.run(f"TMPDIR={temp} FPATH={funcs} make -j1 check", cwd=work)
            # make install needs the generated Makefiles in package().
            shutil.copytree(work, self.source_folder, dirs_exist_ok=True)

    def package(self):
        self.run(
            f"TMPDIR={shlex.quote(self.build_folder)} make -j1 "
            f"DESTDIR={shlex.quote(self.package_folder)} install",
            cwd=self.source_folder,
        )
        copy(self, "is-at-least", os.path.join(self.export_sources_folder, "functions"),
             os.path.join(self.package_folder, "share", "zshdb", "functions"),
             keep_path=False)
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "ZSH-LICENCE", os.path.join(self.export_sources_folder, "functions"),
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
