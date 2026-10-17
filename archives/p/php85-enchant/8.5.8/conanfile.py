#!/usr/bin/env python3
"""Conan recipe — php85-enchant 8.5.8 (PHP phpize/Autotools)."""
import os
import re
import shlex
import shutil
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PhpEnchantConan(ConanFile):
    name = "php85-enchant"
    version = "8.5.8"
    license = "PHP-3.01"
    description = "PHP 8.5 Enchant spell-checking extension"
    homepage = "https://www.php.net/manual/en/book.enchant.php"
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("php/8.5.8", run=True)
        self.requires("enchant/2.8.2")

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("This recipe supports Linux and OHOS")

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        AutotoolsToolchain(self).generate()
        if str(self.settings.os) == "OHOS":
            # Override the source macro before Autoconf generates configure.
            # HMDFS needs traversable temporary directories (E011).
            Path(self.build_folder, "ohos-tempdir.m4").write_text(
                'm4_define([AS_TMPDIR], m4_bpatsubst(m4_defn([AS_TMPDIR]), '
                '[umask 077], [umask 022]))\n')

    def _environment(self):
        env = Environment()
        for dep in self.dependencies.host.values():
            if dep.package_folder:
                for libdir in dep.cpp_info.aggregated_components().libdirs:
                    env.prepend_path("LD_LIBRARY_PATH", libdir)
        info = self.dependencies["enchant"].cpp_info.aggregated_components()
        env.define("ENCHANT2_CFLAGS", " ".join("-I" + shlex.quote(p) for p in info.includedirs))
        env.define("ENCHANT2_LIBS", " ".join(["-L" + shlex.quote(p) for p in info.libdirs] + ["-l" + p for p in info.libs]))
        env.define("NO_INTERACTION", "1")
        env.define("REPORT_EXIT_STATUS", "1")
        env.define("TEST_PHP_EXECUTABLE", os.path.join(self.dependencies["php"].package_folder, "bin", "php"))
        return env.vars(self)

    def _private_php_tools(self):
        prefix = self.dependencies["php"].package_folder
        tools = Path(self.build_folder, "php-tools")
        tools.mkdir(exist_ok=True)
        for name in ("phpize", "php-config"):
            text = Path(prefix, "bin", name).read_text()
            text, count = re.subn(r"(?m)^prefix=['\"]/['\"]$", "prefix=" + shlex.quote(prefix), text)
            if count != 1:
                raise ConanInvalidConfiguration("Unexpected PHP prefix metadata: " + name)
            if name == "phpize":
                # Published prefix=/ makes the tool replace every slash in phpize.m4.
                template = 'cp "$phpdir/phpize.m4" configure.ac'
                if str(self.settings.os) == "OHOS":
                    macro = shlex.quote(str(Path(self.build_folder, "ohos-tempdir.m4")))
                    template = f'cat {macro} "$phpdir/phpize.m4" > configure.ac'
                replacement = 'phpize_replace_prefix()\n{\n  ' + template + '\n}'
                text, count = re.subn(r"phpize_replace_prefix\(\)\s*\{[^}]*\}",
                                     lambda match: replacement, text, flags=re.DOTALL)
                if count != 1:
                    raise ConanInvalidConfiguration("Unexpected phpize template substitution")
            Path(tools, name).write_text(text)
            os.chmod(tools / name, 0o755)
        return tools

    def build(self):
        apply_conandata_patches(self)
        work = Path(self.build_folder, "extension")
        shutil.copytree(Path(self.source_folder, "ext", "enchant"), work, dirs_exist_ok=True)
        tools = self._private_php_tools()
        shell = os.environ.get("CONFIG_SHELL") or shutil.which("bash")
        if not shell:
            raise ConanInvalidConfiguration("bash is required for PHP configure")
        q = shlex.quote
        with self._environment().apply():
            self.run(f"{q(shell)} {q(str(tools / 'phpize'))}", cwd=str(work), env="conanbuild")
            if str(self.settings.os) == "OHOS":
                generated = (work / "configure").read_text()
                if "umask 077" in generated or "umask 022" not in generated:
                    raise ConanInvalidConfiguration("AS_TMPDIR source override was not generated")
            self.run(f"{q(shell)} ./configure "
                     f"--with-php-config={q(str(tools / 'php-config'))} --with-enchant", cwd=str(work), env="conanbuild")
            self.run("make -j2", cwd=str(work), env="conanbuild")
            if can_run(self):
                if len(list((work / "tests").glob("*.phpt"))) != 33:
                    raise ConanInvalidConfiguration("Expected all 33 upstream PHPT files")
                php = os.path.join(self.dependencies["php"].package_folder, "bin", "php")
                module = str(work / "modules" / "enchant.so")
                self.output.info("UPSTREAM_PHPT_EXPECTED=33")
                self.run(f"{q(php)} -n {q(os.path.join(self.source_folder, 'run-tests.php'))} "
                         f"-n -d extension={q(module)} --show-diff tests", cwd=str(work), env="conanbuild")

    def package(self):
        copy(self, "enchant.so", src=os.path.join(self.build_folder, "extension", "modules"),
             dst=os.path.join(self.package_folder, "lib", "php", "extensions"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = ["lib/php/extensions"]
        self.runenv_info.define("PHP85_ENCHANT_EXTENSION", os.path.join(self.package_folder, "lib", "php", "extensions", "enchant.so"))
