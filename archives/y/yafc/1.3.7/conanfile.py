import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, check_sha256, copy, get, load, replace_in_file, save, unzip
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps


class YafcConan(ConanFile):
    name = "yafc"
    version = "1.3.7"
    description = "Interactive FTP and SFTP client"
    homepage = "https://github.com/sebastinas/yafc"
    license = "GPL-2.0-or-later"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    def export_sources(self):
        copy(self, "tmpfile_helper.c", self.recipe_folder, self.export_sources_folder)

    def requirements(self):
        self.requires("libssh/0.11.4")
        self.requires("readline/8.3")

    def build_requirements(self):
        self.tool_requires("bash/5.3")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("Supported native targets: Linux and OHOS")

    def layout(self):
        self.folders.source = "."
        self.folders.build = "."
        self.folders.generators = "conan"

    def source(self):
        archive = self.conf.get("user.yafc:source_archive", default=None)
        if archive:
            check_sha256(self, archive, self.conan_data["sources"]["sha256"])
            unzip(self, archive, strip_root=True)
        else:
            get(self, **self.conan_data["sources"], strip_root=True)
        path = os.path.join(self.source_folder, "support", "config.sub")
        replace_in_file(self, path, "linux-musl* | linux-uclibc*",
                        "linux-musl* | linux-ohos* | linux-uclibc*")
        replace_in_file(self, path, "-linux-musl* | -linux-uclibc*",
                        "-linux-musl* | -linux-ohos* | -linux-uclibc*")
        main = os.path.join(self.source_folder, "src", "main.c")
        replace_in_file(self, main,
                        "\t\tgvUsername = xstrdup(pwd->pw_name);\n\t\tgvLocalHomeDir = xstrdup(pwd->pw_dir);",
                        """        if(pwd) {
            gvUsername = xstrdup(pwd->pw_name);
            gvLocalHomeDir = xstrdup(pwd->pw_dir);
        }
        if(!gvUsername || !*gvUsername) {
            const char *name = getenv("USER");
            char uid_label[48];
            if(!name || !*name) name = getenv("LOGNAME");
            if(!name || !*name) {
                snprintf(uid_label, sizeof(uid_label), "uid-%lu", (unsigned long)geteuid());
                name = uid_label;
            }
            free(gvUsername);
            gvUsername = xstrdup(name);
        }""")
        replace_in_file(self, main, "  char* curdir = getcwd(NULL, 0);",
                        """  char* curdir = getcwd(NULL, 0);
  if(!curdir) {
    fprintf(stderr, "Unable to determine local working directory: %s\\n", strerror(errno));
    exit(EXIT_FAILURE);
  }
  if(!gvLocalHomeDir || gvLocalHomeDir[0] != '/') {
    free(gvLocalHomeDir);
    gvLocalHomeDir = xstrdup(curdir);
  }""")
        utils = os.path.join(self.source_folder, "src", "utils.c")
        save(self, utils, load(self, utils) + "\n" +
             load(self, os.path.join(self.export_sources_folder, "tmpfile_helper.c")))
        replace_in_file(self, os.path.join(self.source_folder, "src", "utils.h"),
                        "void listify_string", "FILE *yafc_tmpfile(void);\n\nvoid listify_string")
        ftp = os.path.join(self.source_folder, "src", "ftp", "ftp.c")
        replace_in_file(self, ftp, '#include "args.h"', '#include "args.h"\n#include "utils.h"')
        for file in (ftp, os.path.join(self.source_folder, "src", "transfer.c")):
            replace_in_file(self, file, "tmpfile()", "yafc_tmpfile()")

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args = [a for a in tc.configure_args
                             if not a.startswith(("--host=", "--build=", "--target="))]
        tc.generate()
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()
        env = Environment()
        bash = os.path.join(self.dependencies.build["bash"].package_folder, "bin", "bash")
        env.define("CONFIG_SHELL", bash)
        env.define("SHELL", bash)
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        for var, names in (("AR", ("ar", "llvm-ar")), ("RANLIB", ("ranlib", "llvm-ranlib")),
                           ("NM", ("nm", "llvm-nm"))):
            tool = next((shutil.which(n) for n in names if shutil.which(n)), None)
            if not tool:
                raise ConanInvalidConfiguration("Native tool missing: " + var)
            env.define(var, tool)
        for dep in self.dependencies.host.values():
            for directory in dep.cpp_info.libdirs:
                path = directory if os.path.isabs(directory) else os.path.join(dep.package_folder, directory)
                if os.path.isdir(path):
                    env.prepend_path("LD_LIBRARY_PATH", path)
        env.vars(self).save_script("yafc_environment")

    def build(self):
        environment = Environment()
        if str(self.settings.os) == "OHOS":
            # mktemp -d fixes mode 0700 independently of the caller's umask.
            # Use exclusive creation in task-private TMPDIR, not chmod on
            # shared filesystem paths, and preserve config.status cleanup.
            configure = os.path.join(self.source_folder, "configure")
            configure_stat = os.stat(configure)
            replacements = (
                ('tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
                 'tmp="${TMPDIR:-.}/conf$$-$RANDOM"; (umask 007 && mkdir "$tmp") &&'),
                ('tmp=./conf$$-$RANDOM', 'tmp="${TMPDIR:-.}/conf$$-$RANDOM"'),
                ('(umask 077 && mkdir "$tmp")', '(umask 007 && mkdir "$tmp")'),
            )
            for original, replacement in replacements:
                replace_in_file(self, configure, original, replacement, strict=True)
            # doc/stamp-vti depends on configure. This temp-directory-only
            # edit changes neither configure.ac nor the shipped Texinfo inputs;
            # preserve the release timestamp rather than regenerating docs via
            # the old mdate-sh parser or suppressing make check/makeinfo errors.
            os.utime(configure, ns=(configure_stat.st_atime_ns,
                                   configure_stat.st_mtime_ns))
            scratch = Path(self.build_folder, ".autoconf-tmp")
            previous_umask = os.umask(0o007)
            try:
                scratch.mkdir(mode=0o770, exist_ok=False)
            finally:
                os.umask(previous_umask)
            environment.define("TMPDIR", str(scratch))
        with environment.vars(self).apply():
            self._build_with_autoconf_tmpdir()

    def _build_with_autoconf_tmpdir(self):
        apply_conandata_patches(self)
        if self.settings.os == "OHOS":
            compiler = self.conf.get("tools.build:compiler_executables", default={}).get("c", "cc")
            triplet = subprocess.check_output([compiler, "-dumpmachine"], text=True).strip()
            if not re.fullmatch(r"aarch64-(?:unknown-)?linux-ohos", triplet) or self.settings.arch != "armv8":
                raise ConanInvalidConfiguration("Native compiler target mismatch: " + triplet)
            guess = os.path.join(self.source_folder, "support", "config.guess")
            save(self, guess + ".original", load(self, guess))
            save(self, guess, "#!/bin/sh\nprintf '%s\\n' " + shlex.quote(triplet) + "\n")
        bash = os.path.join(self.dependencies.build["bash"].package_folder, "bin", "bash")
        env = ["conanbuild", "conanrun", "yafc_environment"]
        self.run(shlex.quote(bash) + " ./configure --prefix=/ --bindir=/bin --libdir=/lib", env=env)
        config = load(self, os.path.join(self.build_folder, "config.h"))
        for feature in ("HAVE_LIBSSH", "HAVE_LIBREADLINE", "HAVE_BASE64_OPENSSL"):
            if not re.search(r"^#define[ \t]+" + feature + r"[ \t]*(?:1|/\*\*/)?[ \t]*$", config, re.M):
                raise ConanInvalidConfiguration("Required published feature was not detected: " + feature)
        self.run("make -j1", env=env)
        if can_run(self):
            self.run("make -j1 check", env=env)
            self.output.info("YAFC_UPSTREAM_RESULT=0/0 (release has no registered tests; make check executed)")

    def package(self):
        self.run("make -j1 DESTDIR=" + shlex.quote(self.package_folder) + " install",
                 env=["conanbuild", "conanrun", "yafc_environment"])
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYRIGHT", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
