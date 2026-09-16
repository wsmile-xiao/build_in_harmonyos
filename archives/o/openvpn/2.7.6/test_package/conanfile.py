#!/usr/bin/env python3
"""test_package for openvpn 2.7.6 - functional verification.

R34: the test must substantially depend on the tested package.  The packaged
`openvpn` CLI binary is executed end-to-end via test_openvpn.sh (shipped in
this test_package):

  1. `openvpn --version` prints "OpenVPN 2.7.6 aarch64-unknown-linux-ohos"
     with [SSL (OpenSSL)] [LZO] [LZ4] [EPOLL] [AEAD] feature marks.
  2. `openvpn --show-ciphers` / `--show-digests` / `--show-tls` list the
     crypto capabilities of the linked OpenSSL (statically embedded).
  3. `openvpn --genkey secret` generates a valid static key.
  4. Static-key dev-null tunnel: `openvpn --config` on a generated config
     with `dev null` runs the TLS-less static-key data path (explicitly
     allowed via --allow-deprecated-insecure-static-crypto) and exits
     cleanly after 4s of inactivity (--ping-exit 4).  Exercises cipher
     init, buffers and the null tun device without root / /dev/net/tun.

The binary is statically linked against the conan dependencies
(NEEDED: libc.so only), so no LD_LIBRARY_PATH handling is needed.
"""
import os

from conan import ConanFile


class OpenvpnTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["openvpn"]
        binary = os.path.join(dep.package_folder, "bin", "openvpn")
        if not os.path.isfile(binary):
            raise RuntimeError(f"openvpn binary not found at {binary}")

        # R34: execute the functional test script against the installed
        # binary via self.run() (L0d).  The script is packaged alongside
        # this conanfile (test_package/test_openvpn.sh).
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "test_openvpn.sh")
        self.run(f'bash "{script}" "{binary}"')
