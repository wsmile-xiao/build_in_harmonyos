#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Ltrace, ltrace, 0.7.3, ltrace 0.7.3, MIT, 
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for system-name libraries.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy, download
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os


class LtraceConan(ConanFile):
    name = "ltrace"
    version = "0.7.3"
    description = "A library call tracer"
    license = "GPL-2.0-or-later"
    homepage = "https://www.ltrace.org/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("elfutils/0.195")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # Add elfutils include and lib paths explicitly
        elfutils_dep = self.dependencies["elfutils"]
        
        tc = AutotoolsToolchain(self)
        # Set TMPDIR to avoid HMDFS permission issues (E046, R7)
        env = tc.environment()
        env.define("TMPDIR", os.path.join(self.build_folder, "tmp"))
        
        # Add elfutils paths via environment variables for configure stage
        cppflags = []
        ldflags = []
        for include_dir in elfutils_dep.cpp_info.includedirs:
            cppflags.append(f"-I{include_dir}")
        for lib_dir in elfutils_dep.cpp_info.libdirs:
            ldflags.append(f"-L{lib_dir}")
        
        if cppflags:
            env.define("CPPFLAGS", " ".join(cppflags))
        if ldflags:
            env.define("LDFLAGS", " ".join(ldflags))
        
        # Explicitly specify --build for OHOS (E037)
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.generate()
        
        # Also use VirtualBuildEnv to ensure environment is activated
        from conan.tools.env import VirtualBuildEnv
        venv = VirtualBuildEnv(self)
        venv.generate()

    def build(self):
        # Create aarch64 -> arm symlink BEFORE applying patches
        # (patches 4-8 modify arm/ directory files)
        sysdeps_dir = os.path.join(self.source_folder, "sysdeps", "linux-gnu")
        aarch64_dir = os.path.join(sysdeps_dir, "aarch64")
        arm_dir = os.path.join(sysdeps_dir, "arm")
        if not os.path.exists(aarch64_dir) and os.path.exists(arm_dir):
            os.symlink("arm", aarch64_dir)
        
        apply_conandata_patches(self)
        
        # Create tmp directory for config.guess (E046)
        tmp_dir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp_dir, exist_ok=True)

        autotools = Autotools(self)
        
        # Add elfutils paths to environment for configure
        elfutils_dep = self.dependencies["elfutils"]
        cppflags_extra = []
        ldflags_extra = []
        for include_dir in elfutils_dep.cpp_info.includedirs:
            cppflags_extra.append(f"-I{include_dir}")
        for lib_dir in elfutils_dep.cpp_info.libdirs:
            ldflags_extra.append(f"-L{lib_dir}")
        
        # Set environment variables before configure
        import os as os_env
        if cppflags_extra:
            existing = os_env.environ.get("CPPFLAGS", "")
            os_env.environ["CPPFLAGS"] = " ".join(cppflags_extra) + (" " + existing if existing else "")
        if ldflags_extra:
            existing = os_env.environ.get("LDFLAGS", "")
            os_env.environ["LDFLAGS"] = " ".join(ldflags_extra) + (" " + existing if existing else "")
        
        try:
            autotools.configure()
        except:
            # Fix config.status for HMDFS permission issue (E167)
            # config.status is in the build folder
            config_status = os.path.join(self.build_folder, "config.status")
            if os.path.exists(config_status):
                # ltrace 0.7.3's config.status uses 'print' command which doesn't exist
                # Create a print wrapper script that mimics ksh print behavior
                print_wrapper = os.path.join(self.build_folder, "print")
                with open(print_wrapper, "w") as f:
                    f.write("#!/bin/sh\n")
                    f.write("# Mimic ksh print command for ltrace 0.7.3's old autotools\n")
                    f.write("# print -r -- args: output args without interpretation\n")
                    f.write("if [ \"$1\" = \"-r\" ]; then\n")
                    f.write("  shift\n")
                    f.write("  if [ \"$1\" = \"--\" ]; then\n")
                    f.write("    shift\n")
                    f.write("  fi\n")
                    f.write("fi\n")
                    f.write("printf '%s\\n' \"$*\"\n")
                os.chmod(print_wrapper, 0o755)
                # Add build folder to PATH so print wrapper is found
                import os as os_env
                build_folder_abs = os.path.abspath(self.build_folder)
                os_env.environ["PATH"] = f"{build_folder_abs}:{os_env.environ.get('PATH', '')}"
                
                # Then fix the temp directory path
                self.run(f"sed -i 's|ac_tmp=$tmp|ac_tmp=./fixed_tmp_for_config_status|g' {config_status}")
                fixed_tmp = os.path.join(self.build_folder, "fixed_tmp_for_config_status")
                os.makedirs(fixed_tmp, exist_ok=True)
                # Re-run config.status
                self.run(f"cd {self.build_folder} && ./config.status")
            else:
                raise
        
        # Create print wrapper for libtool (ltrace 0.7.3's libtool also uses 'print' command)
        print_wrapper = os.path.join(self.build_folder, "print")
        if not os.path.exists(print_wrapper):
            with open(print_wrapper, "w") as f:
                f.write("#!/bin/sh\n")
                f.write("# Mimic ksh print command for ltrace 0.7.3's old autotools\n")
                f.write("# print -r -- args: output args without interpretation\n")
                f.write("if [ \"$1\" = \"-r\" ]; then\n")
                f.write("  shift\n")
                f.write("  if [ \"$1\" = \"--\" ]; then\n")
                f.write("    shift\n")
                f.write("  fi\n")
                f.write("fi\n")
                f.write("printf '%s\\n' \"$*\"\n")
            os.chmod(print_wrapper, 0o755)
            # Add build folder to PATH
            import os as os_env
            build_folder_abs = os.path.abspath(self.build_folder)
            os_env.environ["PATH"] = f"{build_folder_abs}:{os_env.environ.get('PATH', '')}"
        
        # Create aarch64 -> arm symlink in build folder for make
        build_sysdeps_dir = os.path.join(self.build_folder, "sysdeps", "linux-gnu")
        build_aarch64_dir = os.path.join(build_sysdeps_dir, "aarch64")
        if not os.path.exists(build_aarch64_dir):
            os.symlink("arm", build_aarch64_dir)
        
        autotools.make(args=["-j2"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
