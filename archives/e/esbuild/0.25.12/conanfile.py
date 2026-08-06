#!/usr/bin/env python3
"""Conan recipe for esbuild 0.25.12

esbuild is a JavaScript bundler and minifier written in Go.
It produces a standalone binary with no C/C++ dependencies.

Build: CGO_ENABLED=0 go build -ldflags="-s -w" -trimpath ./cmd/esbuild
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class EsbuildConan(ConanFile):
    name = "esbuild"
    version = "0.25.12"
    description = "An extremely fast JavaScript bundler and minifier"
    license = "MIT"
    homepage = "https://esbuild.github.io"
    package_type = "application"

    # R32: os check must include OHOS
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Ensure Go is available - install if needed
        go_bin = shutil.which("go")
        if not go_bin:
            go_bin = self._install_go()

        # On HarmonyOS, the Go linker uses fallocate syscall which returns EACCES
        # on tmpfs. We build a seccomp BPF wrapper that intercepts fallocate and
        # returns EOPNOTSUPP (which the Go linker treats as a non-fatal error,
        # falling back to Truncate + Mmap).
        seccomp_wrap = self._build_seccomp_wrapper()

        # Set Go environment variables
        go_cache = os.path.join(self.build_folder, ".go-cache")
        go_tmp = os.path.join(self.build_folder, ".go-tmp")
        os.makedirs(go_cache, exist_ok=True)
        os.makedirs(go_tmp, exist_ok=True)

        os.environ["CGO_ENABLED"] = "0"
        os.environ["GOPROXY"] = os.environ.get("GOPROXY", "https://goproxy.cn,direct")
        os.environ["GOSUMDB"] = os.environ.get("GOSUMDB", "sum.golang.google.cn")
        os.environ["GOCACHE"] = go_cache
        os.environ["GOTMPDIR"] = go_tmp

        # Build esbuild with seccomp wrapper for fallocate interception
        # Run go build from the source folder where cmd/esbuild/ exists
        if seccomp_wrap:
            self.run(
                f'go build -toolexec "{seccomp_wrap}" '
                f'-ldflags="-s -w" -trimpath '
                f'-o "{os.path.join(self.build_folder, "esbuild")}" ./cmd/esbuild',
                cwd=self.source_folder,
            )
        else:
            self.run(
                'go build -ldflags="-s -w" -trimpath '
                f'-o "{os.path.join(self.build_folder, "esbuild")}" ./cmd/esbuild',
                cwd=self.source_folder,
            )

    def _install_go(self):
        """Install Go toolchain if not available."""
        go_bin = shutil.which("go")
        if go_bin:
            return go_bin

        # Try Harmonybrew first (handles HarmonyOS security trust)
        brew_bin = shutil.which("brew")
        if not brew_bin:
            brew_bin = os.path.expanduser("~/.harmonybrew/bin/brew")

        if not brew_bin or not os.path.exists(brew_bin):
            # Install Harmonybrew
            self.run(
                'zsh -c "$(curl -fsSL https://harmonybrew.atomgit.com/install.sh)"'
            )
            brew_bin = os.path.expanduser("~/.harmonybrew/bin/brew")

        if os.path.exists(brew_bin):
            # Set up Harmonybrew environment
            brew_prefix = os.path.expanduser("~/.harmonybrew")
            os.environ["PATH"] = (
                f"{brew_prefix}/bin:" + os.environ.get("PATH", "")
            )
            # Install Go via Harmonybrew (handles security trust registration)
            self.run(f'"{brew_bin}" install go')
            go_bin = shutil.which("go")
            if go_bin:
                return go_bin

        raise Exception(
            "Go is required but could not be installed. "
            "Please install Go manually or ensure Harmonybrew is available."
        )

    def _build_seccomp_wrapper(self):
        """Build a seccomp BPF wrapper that intercepts fallocate syscall."""
        # Only needed on HarmonyOS (os=OHOS) where fallocate returns EACCES
        if self.settings.os != "OHOS":
            return None

        c_source = r'''
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/prctl.h>
#include <linux/filter.h>
#include <linux/seccomp.h>
#include <linux/audit.h>
#include <errno.h>
#include <stddef.h>
#include <string.h>

struct seccomp_data_arch {
    unsigned int nr;
    unsigned int arch;
    unsigned long long instruction_pointer;
    unsigned long long args[6];
};

int main(int argc, char **argv) {
    if (argc < 2) return 1;

    if (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)) {
        perror("prctl NO_NEW_PRIVS");
    }

    struct sock_filter filter[] = {
        BPF_STMT(BPF_LD | BPF_W | BPF_ABS,
                 offsetof(struct seccomp_data_arch, arch)),
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, AUDIT_ARCH_AARCH64, 1, 0),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_KILL),
        BPF_STMT(BPF_LD | BPF_W | BPF_ABS,
                 offsetof(struct seccomp_data_arch, nr)),
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, 47, 2, 0),
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, 285, 1, 0),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | (95 & SECCOMP_RET_DATA)),
    };

    struct sock_fprog prog = {
        .len = sizeof(filter) / sizeof(filter[0]),
        .filter = filter,
    };

    if (prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &prog)) {
        /* seccomp not available, run without filter */
    }

    fflush(stderr);
    execvp(argv[1], &argv[1]);
    perror("execvp");
    return 1;
}
'''
        src_path = os.path.join(self.build_folder, "seccomp_wrap.c")
        with open(src_path, "w") as f:
            f.write(c_source)

        out_path = os.path.join(self.build_folder, "seccomp_wrap")

        # Find a C compiler
        cc = shutil.which("clang") or shutil.which("gcc") or shutil.which("cc")
        if not cc:
            self.output.warning("No C compiler found for seccomp wrapper, skipping")
            return None

        try:
            self.run(f'{cc} -o "{out_path}" "{src_path}"')
            return out_path
        except Exception:
            self.output.warning("Failed to build seccomp wrapper, skipping")
            return None

    def package(self):
        copy(self, "esbuild", self.build_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
