#!/usr/bin/env python3
"""Conan test_package for lua-resty-http 0.17.2 — pure Lua library test.

Verifies that the Lua module files are present in the package and contain
the expected module definitions. Since lua-resty-http is a pure Lua library
(no compiled binary), the test checks file existence and content via shell
commands.

R34: test_package verifies actual package content (Lua module files),
     not just printing strings.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class LuaRestyHttpTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            dep = self.dependencies["lua-resty-http"]
            resty_dir = os.path.join(dep.package_folder, "lib", "lua", "5.4", "resty")

            # Verify all 3 Lua module files exist (test -f exits 0 if file exists)
            for fname in ["http.lua", "http_connect.lua", "http_headers.lua"]:
                fpath = os.path.join(resty_dir, fname)
                self.run(f'test -f "{fpath}"', env="conanrun")
                self.output.info(f"Verified file exists: {fname}")

            # Verify content of http.lua contains module definition (grep -q exits 0 on match)
            self.run(
                f'grep -q "resty.http" "{os.path.join(resty_dir, "http.lua")}"',
                env="conanrun"
            )
            self.output.info("http.lua module definition verified")

            # Verify content of http_headers.lua
            self.run(
                f'grep -qi "headers" "{os.path.join(resty_dir, "http_headers.lua")}"',
                env="conanrun"
            )
            self.output.info("http_headers.lua module definition verified")

            # Verify content of http_connect.lua
            self.run(
                f'grep -qi "connect" "{os.path.join(resty_dir, "http_connect.lua")}"',
                env="conanrun"
            )
            self.output.info("http_connect.lua module definition verified")

            self.output.info("lua-resty-http test: PASS (3 module files verified)")
