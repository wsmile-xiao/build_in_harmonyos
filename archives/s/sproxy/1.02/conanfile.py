#!/usr/bin/env python3
"""Conan recipe for sproxy 1.02 — HTTP proxy that records requested URLs.

Upstream (JoeDog) ships sproxy as an autotools wrapper around one pure-Perl
script (`src/sproxy.in`) plus a bundled pure-Perl module (JoeDog::Config).
There is no C/C++ code: the upstream configure/Makefile only substitutes
`%_VAR%` placeholders (`sed`), copies files and, when a Perl module is not
found by `$PERL utils/modtest`, builds the bundled tarballs.

configure's module probing executes the target perl, which is impossible when
cross-building (aarch64 perl on an x86 builder), so this recipe performs the
same substitutions directly in build() — autoconf/automake/libtool are not
needed on the build machine (OHOS devices have none either).

Runtime: perl (this repo's perl/5.42.2.3). Its perl has no libwww-perl stack,
so the package is self-contained: it installs upstream's own bundled
libwww-perl 5.76 (LWP, HTTP::*, Net::HTTP, pure Perl) and JoeDog::Config from
lib/*.tar.gz, plus URI 5.35 (pure Perl, CPAN; upstream assumes it is installed)
into lib/sproxy, which sproxy puts first in @INC.
License: GPL-2.0-or-later.
"""
import os
import re
import shutil
import tarfile
import time

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class SproxyConan(ConanFile):
    name = "sproxy"
    version = "1.02"
    description = "HTTP proxy that records every URL requested through it"
    license = "GPL-2.0-or-later"
    homepage = "https://www.joedog.org/"
    url = ""  # CI fills this
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"sproxy supports Linux and OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("perl/5.42.2.3")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        get(self, **self.conan_data["sources"]["uri-5.35"],
            destination=os.path.join(self.source_folder, "uri"), strip_root=True)

    def _read_version_txt(self):
        with open(os.path.join(self.source_folder, "src", "version.txt"),
                  encoding="utf-8") as fh:
            text = fh.read()
        values = {}
        for key in ("PROGRAM", "VERSION", "AUTHOR"):
            m = re.search(rf'^{key}\s+"([^"]*)"', text, re.M)
            if not m:
                raise ConanInvalidConfiguration(f"src/version.txt lacks {key}")
            values[key] = m.group(1)
        if values["VERSION"] != self.version:
            raise ConanInvalidConfiguration(
                f"upstream VERSION {values['VERSION']} != recipe {self.version}"
            )
        return values

    def build(self):
        """Equivalent of upstream `configure && make` (sed substitutions)."""
        info = self._read_version_txt()
        perl_bin = os.path.join(self.dependencies["perl"].package_folder,
                                "bin", "perl")
        # upstream: DATE=`utils/mkstamp` == `date +"%B-%d-%Y"` (C locale)
        month = ("January", "February", "March", "April", "May", "June",
                 "July", "August", "September", "October", "November",
                 "December")[time.gmtime().tm_mon - 1]
        date = f"{month}-{time.strftime('%d-%Y', time.gmtime())}"
        subst = {
            "%_DATE%": date,
            "%_VERSION%": info["VERSION"],
            "%_PROGRAM%": info["PROGRAM"],
            "%_AUTHOR%": info["AUTHOR"],
        }
        out = os.path.join(self.build_folder, "out")
        os.makedirs(out, exist_ok=True)

        def render(src_rel, dst_name, with_perl=False):
            with open(os.path.join(self.source_folder, src_rel),
                      encoding="utf-8") as fh:
                content = fh.read()
            for key, value in subst.items():
                content = content.replace(key, value)
            if with_perl:
                # OHOS has no /usr/bin/perl and rejects `#!/usr/bin/env perl`;
                # point the shebang at the conan perl dependency.
                if not content.startswith("#!%_PERL%"):
                    raise ConanInvalidConfiguration(
                        "sproxy.in shebang anchor drifted")
                content = f"#!{perl_bin}" + content[len("#!%_PERL%"):]
                # sproxy only forwards content; LWP's default parse_head would
                # require HTML::HeadParser (XS, HTML-Parser) for text/html
                # responses, which the perl dependency does not ship.
                anchor = "$ua->env_proxy;"
                if content.count(anchor) != 1:
                    raise ConanInvalidConfiguration(
                        "sproxy.in env_proxy anchor drifted")
                content = content.replace(
                    anchor, anchor + "\n  $ua->parse_head(0);")
            with open(os.path.join(out, dst_name), "w", encoding="utf-8",
                      newline="\n") as fh:
                fh.write(content)

        render("src/sproxy.in", "sproxy", with_perl=True)
        render("doc/sproxy.conf.in", "sproxy.conf")
        render("doc/sproxy.1.in", "sproxy.1")

        # Bundled pure-Perl JoeDog::Config (upstream installs it to
        # $prefix/lib/sproxy/JoeDog/Config.pm via Makefile.PL LIB=...).
        cfg_tar = os.path.join(self.source_folder, "lib",
                               "JoeDog-Config-1.2.tar.gz")
        with tarfile.open(cfg_tar) as tf:
            member = tf.getmember("JoeDog-Config-1.2/Config.pm")
            data = tf.extractfile(member).read()
        cfg_dir = os.path.join(out, "lib", "sproxy", "JoeDog")
        os.makedirs(cfg_dir, exist_ok=True)
        with open(os.path.join(cfg_dir, "Config.pm"), "wb") as fh:
            fh.write(data)

        # LWP / HTTP::* / Net::HTTP: upstream bundles libwww-perl 5.76 (pure
        # Perl) in lib/libwww-perl-5.76.tar.gz and installs it to
        # $prefix/lib/sproxy when LWP is missing. Do the same, from the tarball.
        perl_lib = os.path.join(out, "lib", "sproxy")
        lwp_prefix = "libwww-perl-5.76/lib/"
        lwp_tar = os.path.join(self.source_folder, "lib",
                               "libwww-perl-5.76.tar.gz")
        count = 0
        with tarfile.open(lwp_tar) as tf:
            for member in tf.getmembers():
                if not member.isfile() or not member.name.startswith(lwp_prefix):
                    continue
                rel = member.name[len(lwp_prefix):]
                if rel.startswith("Bundle/") or ".." in rel.split("/"):
                    continue
                dst = os.path.join(perl_lib, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                with open(dst, "wb") as fh:
                    fh.write(tf.extractfile(member).read())
                count += 1
        if count < 40 or not os.path.isfile(
                os.path.join(perl_lib, "HTTP", "Daemon.pm")):
            raise ConanInvalidConfiguration(
                f"libwww-perl-5.76 bundle inventory drift ({count} files)")

        # URI (required by libwww-perl; not bundled upstream): pure Perl.
        uri_lib = os.path.join(self.source_folder, "uri", "lib")
        if not os.path.isfile(os.path.join(uri_lib, "URI.pm")):
            raise ConanInvalidConfiguration("URI source layout drifted")
        shutil.copytree(uri_lib, perl_lib, dirs_exist_ok=True)

    def package(self):
        out = os.path.join(self.build_folder, "out")
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        copy(self, "sproxy", src=out, dst=bindir)
        os.chmod(os.path.join(bindir, "sproxy"), 0o755)
        copy(self, "sproxy.conf", src=out,
             dst=os.path.join(self.package_folder, "etc"))
        copy(self, "sproxy.1", src=out,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "*", src=os.path.join(out, "lib", "sproxy"),
             dst=os.path.join(self.package_folder, "lib", "sproxy"))
        for doc in ("README", "AUTHORS", "ChangeLog"):
            copy(self, doc, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "share", "doc", "sproxy"))

    def package_id(self):
        # Pure script package: independent of os/arch/compiler.
        self.info.clear()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
