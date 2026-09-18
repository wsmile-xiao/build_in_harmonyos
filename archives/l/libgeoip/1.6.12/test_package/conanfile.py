#!/usr/bin/env python3
"""Conan test_package — libgeoip 1.6.12 (libGeoIP) L1 functional test.

Consumer-side verification (R34: real API usage):
  1. test_geoip — mirrors the upstream test/test-geoip.c flow against the
     conan-packaged libGeoIP: opens the sample GeoIP.dat (the one shipped
     inside the upstream tarball) with GEOIP_MEMORY_CACHE, checks the
     database-info banner, runs all 61 IP entries of the upstream
     country_test.txt vector set through code/code3 by_addr and by_name,
     plus NULL-input graceful handling and a filesystem-mode pass.
  2. test_geoip_ohos — HarmonyOS-specific test (rule12): OHOS musl page
     size via sysconf, stdio/pread data path, custom-directory database
     discovery (GeoIP_db_avail).
  3. geoiplookup / geoiplookup6 — packaged CLI tools run end-to-end with
     the sample database (geoiplookup -d <dir> <ip> → country line).

Binary sample data note: GeoIP.dat is a real binary database; the GitCode
PR-diff channel cannot carry binary files (missing binary patch data), so
it is stored base64-encoded as GeoIP.dat.b64 and decoded at test time
into the build folder (sha256-verified, bit-identical to upstream's
data/GeoIP.dat).
"""
import base64
import hashlib
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibgeoipTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _decode_sample_db(self):
        """Decode the base64 sample GeoIP.dat into the build folder."""
        b64_src = os.path.join(self.source_folder, "GeoIP.dat.b64")
        dat_dst = os.path.join(self.build_folder, "GeoIP.dat")
        with open(b64_src, "rb") as fh:
            raw = base64.b64decode(fh.read())
        with open(dat_dst, "wb") as fh:
            fh.write(raw)
        # integrity: must match the upstream tarball's data/GeoIP.dat
        digest = hashlib.sha256(raw).hexdigest()
        expected = "9fe2005059f6c835e7bbee0803d89ddf67e22730d4420e34d44f33b054e51d81"
        if digest != expected:
            raise RuntimeError(
                f"decoded GeoIP.dat sha256 mismatch: {digest}")
        return dat_dst

    def test(self):
        # Run the two compiled tests directly (R34: real API usage via
        # self.run; can_run guard keeps cross scenarios safe)
        exe_dir = os.path.join(self.build_folder)
        dat = self._decode_sample_db()
        vec = os.path.join(self.source_folder, "country_test.txt")

        if can_run(self):
            self.run(f'"{os.path.join(exe_dir, "test_geoip")}" "{dat}" '
                     f'"{vec}"', env="conanrun")
            self.run(f'"{os.path.join(exe_dir, "test_geoip_ohos")}" "{dat}"',
                     env="conanrun")
        else:
            self.output.warning(
                "cross-building: skipping runtime test execution")
            return

        # CLI tools: run the packaged geoiplookup against the sample data.
        # geoiplookup needs the db in its own directory: -d takes the
        # directory that CONTAINS GeoIP.dat.
        pkg = self.dependencies["libgeoip"].package_folder
        lookup = os.path.join(pkg, "bin", "geoiplookup")
        lookup6 = os.path.join(pkg, "bin", "geoiplookup6")
        if not os.path.isfile(lookup):
            raise RuntimeError(f"geoiplookup not found at {lookup}")
        if not os.path.isfile(lookup6):
            raise RuntimeError(f"geoiplookup6 not found at {lookup6}")

        dat_dir = exe_dir

        def _run_tool(cmd):
            """Run a packaged CLI tool and return its combined output."""
            out_path = os.path.join(self.build_folder, "tool-out.txt")
            with open(out_path, "w", encoding="utf-8") as fh:
                self.run(cmd, env="conanrun", stdout=fh, stderr=fh)
            with open(out_path, "r", encoding="utf-8",
                      errors="replace") as fh:
                return fh.read()

        out = _run_tool(f'"{lookup}" -d "{dat_dir}" 12.87.118.0')
        if "US, United States" not in out:
            raise RuntimeError(
                f"geoiplookup country lookup failed: {out!r}")
        self.output.info(f"geoiplookup: {out.strip()}")

        out = _run_tool(f'"{lookup}" -d "{dat_dir}" 63.147.126.103')
        if "FR, France" not in out:
            raise RuntimeError(
                f"geoiplookup country lookup failed: {out!r}")
        self.output.info(f"geoiplookup: {out.strip()}")

        # geoiplookup6 with an IPv6 literal: the sample db is IPv4-only,
        # so the v6 tool finds no GeoIPv6.dat and exits 0 silently
        # (upstream behavior — the outer loop only prints when a v6
        # database is present). Verifies the v6 binary runs and exits
        # cleanly on OHOS.
        out = _run_tool(f'"{lookup6}" -d "{dat_dir}" ::1')
        self.output.info(f"geoiplookup6: {out.strip()!r} (no v6 db → "
                         "silent success, exit 0)")
