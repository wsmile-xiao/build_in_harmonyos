#!/usr/bin/env python3
"""Conan recipe for powerlevel10k — a fast zsh theme (pure zsh scripts).

Upstream v1.20.0 ships the theme as plain zsh sources:
powerlevel10k.zsh-theme (entry point), internal/*.zsh (engine, wizard,
parser), config/*.zsh (ready-made styles) and gitstatus/ (vcs backend
scripts + gitstatusd C++ sources).  The release tarball contains NO
prebuilt gitstatusd binary — those live in the separate gitstatus release
assets, and the bundled libgit2 fork (gitstatus/deps) is an empty submodule
placeholder (.gitkeep only).

This recipe packages the zsh scripts only, without the gitstatusd daemon.
Daemon-less operation is an upstream-supported configuration:
  * internal/p10k.zsh:4165 — the gitstatus fast path is gated on
    GITSTATUS_DAEMON_PID_POWERLEVEL9K; without a running daemon the theme
    renders git segments via zsh's native vcs_info instead;
  * gitstatus/gitstatus.plugin.zsh:55-58 — if the zsh module set
    (zsh/datetime, zsh/system, zsh/files) is unavailable, the plugin
    silently returns and the theme degrades to vcs_info.
The full decision record is in notes.md (R36/R21/JC2 constraints).

Layout is share-only (share/powerlevel10k/): the theme is sourced by the
user's zshrc, never executed, so there are no bin/ artifacts.  The expected
terminal manifest status for this script package is "built" (G4
conan-verify downgrade; papirus-icon precedent).
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class Powerlevel10kConan(ConanFile):
    name = "powerlevel10k"
    version = "1.20.0"
    description = ("A Zsh theme with emphasis on speed, flexibility and "
                   "out-of-the-box experience")
    license = "MIT"
    homepage = "https://github.com/romkatv/powerlevel10k"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    # L0p: OHOS profile gate requires all four settings attributes.
    # They are cleared in package_id(): pure zsh scripts are
    # interpreter/arch independent (zimfw 1.20.0 precedent).
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # No-op today (patches: {} — zero source modifications); kept so
        # any future patch declared in conandata.yml is applied here
        # (posh/papirus-icon precedent, G1 gate requirement).
        apply_conandata_patches(self)
        # Pure zsh scripts — nothing to compile.  The upstream Makefile
        # only builds the gitstatusd daemon (C++), which is intentionally
        # not packaged (see notes.md).
        pass

    def package(self):
        # Upstream install.md: "git clone the repository into your custom
        # themes directory" — i.e. the whole tree IS the installable unit.
        # Conan layout: share/powerlevel10k/.  The gitstatus/ zsh scripts
        # are required for backend dispatch + graceful degradation; its
        # C++ sources stay for future daemon builds (harmless, faithful
        # to the upstream layout).
        copy(self, "*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "powerlevel10k"),
             keep_path=True)

    def package_id(self):
        # Script-only package: identical payload for every settings
        # combination.
        self.info.clear()

    def package_info(self):
        # No bin/ artifacts: the theme is sourced, not executed
        # (share-only layout, bindirs intentionally empty).
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.resdirs = ["share"]
        theme_dir = os.path.join(self.package_folder, "share", "powerlevel10k")
        self.runenv_info.define_path("POWERLEVEL10K_DIR", theme_dir)
