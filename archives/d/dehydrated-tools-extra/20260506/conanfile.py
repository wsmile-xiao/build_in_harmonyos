#!/usr/bin/env python3
"""Conan recipe for dehydrated-tools-extra — extra tools for the dehydrated
ACME client (pure POSIX shell scripts, no compilation, no configure).

Installs the dehydrated-cron/dehydrated-hook/dehydrated-nsupdate scripts,
hook example scripts, cron.d/logrotate.d configs and documentation.
The upstream man pages stay in .rst form: rst2man (python3-docutils) is not
available on OHOS, so `make build` (man pages) is intentionally not run.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class DehydratedToolsExtraConan(ConanFile):
    name = "dehydrated-tools-extra"
    version = "20260506"
    description = "Extra tools for the dehydrated ACME client (cron wrapper, hook dispatcher, nsupdate hook)"
    license = "GPL-3.0-or-later"
    homepage = "https://git.open-infrastructure.net/tools/dehydrated-tools-extra"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Upstream official test entry point (`make test`): sh -n syntax check
        # on all scripts; checkbashisms/shellcheck parts self-skip when the
        # tools are not installed. Run it for real so it gates the build.
        self.run("make test", cwd=self.source_folder)

    def package(self):
        src = self.source_folder
        # CLI shell scripts (upstream: /usr/bin)
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        for f in ["dehydrated-cron", "dehydrated-hook", "dehydrated-nsupdate"]:
            copy(self, f, src=os.path.join(src, "bin"), dst=bin_dir)
        # Hook example scripts (upstream: /usr/share/dehydrated/hooks)
        hooks_dir = os.path.join(self.package_folder, "share", "dehydrated", "hooks")
        os.makedirs(hooks_dir, exist_ok=True)
        copy(self, "*", src=os.path.join(src, "share", "hooks"), dst=hooks_dir)
        # cron.d / logrotate.d configs (upstream: /etc/cron.d, /etc/logrotate.d)
        cron_dir = os.path.join(self.package_folder, "etc", "cron.d")
        os.makedirs(cron_dir, exist_ok=True)
        copy(self, "dehydrated", src=os.path.join(src, "share", "cron"), dst=cron_dir)
        logrotate_dir = os.path.join(self.package_folder, "etc", "logrotate.d")
        os.makedirs(logrotate_dir, exist_ok=True)
        copy(self, "dehydrated", src=os.path.join(src, "share", "logrotate"), dst=logrotate_dir)
        # Docs: license, changelog, TODO and rst man pages (man pages are not
        # rendered: rst2man/python3-docutils is unavailable on OHOS)
        doc_dir = os.path.join(self.package_folder, "share", "doc", "dehydrated-tools-extra")
        os.makedirs(doc_dir, exist_ok=True)
        for f in ["LICENSE.txt", "CHANGELOG.txt", "TODO.txt", "VERSION.txt"]:
            copy(self, f, src=src, dst=doc_dir)
        copy(self, "*.rst", src=os.path.join(src, "share", "man"), dst=doc_dir)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
