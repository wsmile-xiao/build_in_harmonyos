#!/usr/bin/env python3
"""Conan recipe — partimage 0.6.9 (Autotools, CLI tool)

partimage is a Linux utility for making backups of disk partitions.
It saves partitions in a compressed image file to allow fast restoration.
Built in batch/headless mode (no newt GUI) for HarmonyOS platform.
"""
import os
import time
import glob

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, save
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


# Embedded gui_dummy.cpp for headless/batch mode (no newt GUI)
GUI_DUMMY_CPP = r'''// gui_dummy.cpp — dummy GUI implementations for headless/batch mode (no newt)
#ifndef HAVE_LIBNEWT
#ifdef HAVE_CONFIG_H
  #include <config.h>
#endif
#include "gui_text.h"
#include "partimage.h"
int COptionsWindow::runForm() { return 0; }
void COptionsWindow::destroyForm() {}
void COptionsWindow::addHotKeys() {}
void COptionsWindow::addButtons() {}
int CRestoreMbrWindow::create() { return 0; }
void CRestoreMbrWindow::addHardDisk(char *, DWORD) {}
void CRestoreMbrWindow::addMbr(char *, DWORD) {}
void CRestoreMbrWindow::getValues(uintptr_t *a, uintptr_t *b, int *c) { if(a)*a=0; if(b)*b=0; if(c)*c=MBR_RESTORE_WHOLE; }
int CSaveOptWindow::create(char *, COptions) { return 0; }
int CSaveOptWindow::getValues(COptions *) { return 0; }
int CRestoreOptWindow::create(char *, char *, COptions) { return 0; }
int CRestoreOptWindow::getValues(COptions *) { return 0; }
int CSavingWindow::create(const char *, const char *, const char *, QWORD, COptions) { return 0; }
int CSavingWindow::runForm() { return 0; }
void CSavingWindow::destroyForm() {}
void CSavingWindow::showImageFileInfo(char *, QWORD, QWORD, char *) {}
void CSavingWindow::showStats(const time_t, QWORD, QWORD, QWORD, char *) {}
int CRestoringWindow::create(char *, char *, QWORD, DWORD, char *, char *, portable_tm, QWORD, COptions *) { return 0; }
int CRestoringWindow::runForm() { return 0; }
void CRestoringWindow::destroyForm() {}
void CRestoringWindow::showImageFileInfo(char *, int, char *) {}
void CRestoringWindow::showStats(const time_t, QWORD, QWORD, QWORD, QWORD, bool, char *) {}
unsigned int CExceptionsGUI::windowError(char *, char *, char *, char *) { return 0; }
unsigned int CExceptionsGUI::windowAlreadyExist(char *, char *) { return 0; }
unsigned int CExceptionsGUI::windowLocked(char *, char *) { return 0; }
unsigned int CExceptionsGUI::windowWrongPath(char *) { return 0; }
#endif
'''


class PartimageConan(ConanFile):
    name = "partimage"
    version = "0.6.9"
    description = "Linux utility for making backups of disk partitions"
    license = "GPL-2.0-or-later"
    homepage = "https://www.partimage.org/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    generators = "AutotoolsDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")
        self.requires("bzip2/1.0.8")
        self.requires("gettext/0.22.5")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-newt")
        tc.configure_args.append("--disable-ssl")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Create gui_dummy.cpp (new file not in original tarball)
        save(self, os.path.join(self.source_folder, "src", "client", "gui_dummy.cpp"), GUI_DUMMY_CPP)
        # Create compile wrapper (automake auxiliary, missing from tarball)
        compile_path = os.path.join(self.source_folder, "compile")
        if not os.path.exists(compile_path):
            save(self, compile_path, '#!/bin/sh\nexec "$@"\n')
            os.chmod(compile_path, 0o755)
        # HMDFS workaround: patch 0006 may not fully remove umask 077 from
        # the large configure script (context mismatch on some hunks).
        # Ensure umask 077 is removed and chmod is added for HMDFS compatibility.
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure_path):
            with open(configure_path, "r") as f:
                content = f.read()
            if "umask 077" in content:
                content = content.replace('(umask 077 && mktemp -d', '(mktemp -d')
                content = content.replace('(umask 077 && mkdir', '(mkdir')
                content = content.replace(
                    'test -d "$tmp"\n}',
                    'test -d "$tmp" && chmod 0777 "$tmp" 2>/dev/null\n}'
                )
                with open(configure_path, "w") as f:
                    f.write(content)
        # Set permissive umask for HMFS compatibility
        os.umask(0o022)
        # Prevent automake/aclocal/autoconf regeneration (automake not on OHOS)
        now = time.time()
        for root, dirs, files in os.walk(self.source_folder):
            for d in list(dirs):
                if d in ('.deps', '.git'):
                    dirs.remove(d)
            for fn in files:
                os.utime(os.path.join(root, fn), (now, now))
        # Touch configure to be newest (prevents "older than distributed files")
        for f in ["configure", "config.status"]:
            p = os.path.join(self.source_folder, f)
            if os.path.exists(p):
                os.utime(p, (now + 1, now + 1))
        autotools = Autotools(self)
        autotools.configure()
        # Fix generated config.status (inherits umask 077 from configure template)
        for cs_path in glob.glob(os.path.join(self.build_folder, "**/config.status"), recursive=True):
            with open(cs_path, "r") as f:
                cs = f.read()
            cs = cs.replace('(umask 077 && mktemp -d', '(mktemp -d')
            cs = cs.replace('(umask 077 && mkdir', '(mkdir')
            cs = cs.replace('(umask 022 && mktemp -d', '(mktemp -d')
            cs = cs.replace('(umask 022 && mkdir', '(mkdir')
            cs = cs.replace(
                'test -d "$tmp"\n}',
                'test -d "$tmp" && chmod 0777 "$tmp" 2>/dev/null\n}'
            )
            with open(cs_path, "w") as f:
                f.write(cs)
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
