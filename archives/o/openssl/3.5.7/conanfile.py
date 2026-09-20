#!/usr/bin/env python3
"""Conan recipe — OpenSSL 3.5.7 (custom-perl build system).

上游: https://github.com/openssl/openssl/releases/tag/openssl-3.5.7（tag 与版本一一对应，
sha256 已与 openssl.org 官方 .sha256 文件核对一致）。

继承本仓 openssl/3.5.8.1、3.5.6.1.1 已验证的 OHOS 适配结论，并按 SKILL §3 在 build()
里真实执行上游 `make test` 套件（3.0.16 的做法），不再「超时截断即算过」：

  - Configure 默认写 gcc，OHOS 只有 clang → 显式传 CC=<clang>（R33，来自 profile conf）
  - R26: openssl 是 system-name 库（libssl/libcrypto 与系统 /lib 冲突）→ no-shared 静态
  - OHOS(musl) 无 glibc 私有符号 __fd_chk → 0002 补丁提供有界 fd_set，配 -D__MUSL__
  - OHOS(musl) 无 /dev/*random 的旧探测路径 → --with-rand-seed=getrandom
  - no-asm：OHOS 上 perlasm 生成的 .S 与 SDK 汇编器组合不稳定，沿用既有范本
  - R9: make -j2 受限并行（CI worker 内存有限）
  - R49: 链接期需 LD_LIBRARY_PATH 指向 SDK llvm/lib，否则 lld 找不到 libxml2.so.16
  - R32: settings.os 判断用 `in ("Linux", "OHOS")`
  - R39: conandata 只声明官方 HTTPS 源

Build system: custom-perl (Configure + make)
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"

# OHOS SDK llvm 目录（CI worker 与真机 harmonybrew 同名布局）；缺失时 loader 忽略即可。
_SDK_LLVM = ("/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm")
LD_ENV = (
    "LD_LIBRARY_PATH={0}/lib:{0}/sysroot/usr/lib:${{LD_LIBRARY_PATH:-}}"
).format(_SDK_LLVM)

# test/recipes/<n>-<stem>.t 的用例名（去掉序号与 .t），交给 test/run_tests.pl 匹配。
# 取的是加密算法/ASN.1/X.509/PKCS/TLS/QUIC/provider 这条安全关键主线；不含 fuzz、
# fips-only、external（需第三方套件）与 dynamic-engine（依赖 shared 构建）那一类。
# 名单逐项存在于上游 3.5.7：ls test/recipes/*.t | sed 's/^[0-9]*-//;s/\.t$//'。
CI_UPSTREAM_TESTS = " ".join((
    "test_sanity test_symbol_presence test_bn test_internal_bn test_ec test_ecdsa test_ecparam test_genec",
    "test_evp test_evp_extra test_evp_byname test_evp_fetch_prov test_evp_kdf test_evp_pkey_provided",
    "test_asn1_decode test_asn1_encode test_asn1_parse test_asn1_stable_parse test_asn1_string_table",
    "test_asn1_time test_internal_asn1 test_internal_asn1_dsa test_algorithmid test_params_api test_params",
    "test_param_build test_property test_hmac test_mac test_cmac test_kdf test_dgst test_sha test_aesgcm",
    "test_internal_chacha test_internal_poly1305 test_internal_siphash test_internal_sm2 test_internal_sm3",
    "test_internal_sm4 test_des test_bf test_cast test_rc2 test_idea test_ige test_exp test_rsa test_rsaoaep",
    "test_rsapss test_rsax931 test_mp_rsa test_dh test_dsa test_dsaparam test_gendh test_genrsa test_genpkey",
    "test_gensm2 test_ml_kem_codecs test_ml_dsa_codecs test_slh_dsa test_hpke test_pkey test_pkeyutl",
    "test_x509 test_x509_req test_x509_time test_x509_store test_x509_load_cert_file test_verify test_req",
    "test_crl test_cms test_pkcs7 test_pkcs12 test_pkcs8 test_ocsp test_rpk test_dane test_ct test_tsa",
    "test_policy_tree test_ca test_ssl_ctx test_sslapi test_sslbuffers test_clienthello test_recordlen",
    "test_packet test_wpacket test_dtls test_dtls_mtu test_quicapi test_quic_record test_quic_stream",
    "test_quic_wire test_quic_txp test_quic_cfq test_quic_ackm test_provider test_provfetch",
    "test_provider_fallback test_encoder_decoder test_store test_ossl_store test_rand test_threads test_async",
    "test_memleak test_secmem test_constant_time test_upcalls test_conf test_pem_reading test_ui",
))



class OpensslConan(ConanFile):
    name = "openssl"
    version = "3.5.7"
    description = "Industry-standard TLS/SSL and cryptographic library"
    license = "Apache-2.0"
    homepage = "https://www.openssl.org/"
    url = "https://github.com/openssl/openssl"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Static-only build; the optional zlib compression path is not enabled,
        # so no Conan dependency is needed.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _configure_target(self):
        if self.settings.arch in ("armv8", "aarch64"):
            return "linux-aarch64"
        if self.settings.arch == "x86_64":
            return "linux-x86_64"
        raise Exception(f"Unsupported arch: {self.settings.arch}")

    def _cc(self):
        cc_conf = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = cc_conf.get("c") or os.environ.get("CC") or "clang"
        if self.settings.os == "OHOS":
            # Patch 0002's bounded fd_set is guarded by __MUSL__; without it the
            # build falls back to bare FD_SET and fails at link time on musl.
            cc = f"{cc} -D__MUSL__"
        return cc

    def build(self):
        apply_conandata_patches(self)

        if self.settings.os not in ("Linux", "OHOS"):
            raise Exception(f"Unsupported OS: {self.settings.os}")

        prefix = self.package_folder
        openssldir = os.path.join(prefix, "ssl")
        configure_cmd = (
            f"perl ./Configure "
            f"--prefix={prefix} "
            f"--openssldir={openssldir} "
            f"no-asm "
            f"no-shared "
            f"--with-rand-seed=getrandom "
            f'CC="{self._cc()}" '
            f"{self._configure_target()}"
        )
        self.run(configure_cmd, cwd=self.source_folder)

        # Library + apps only (make install would try to build docs, and the
        # 3.5.x tree is missing some pod.in files).
        self.run(f"{LD_ENV} make build_sw -j2", cwd=self.source_folder)

        # Upstream official suite (SKILL §3): `make test` → test/run_tests.pl.
        # `make test` also builds every test program (test: tests → build_programs),
        # so the only knob left for CI is which *.t recipes the harness runs.
        # CI gives one package 3600s (ci/config/build_timeouts.txt has no openssl
        # entry, and rule5 forbids contributors touching ci/), while the full 345-script
        # suite alone measured 930s/1144s on a 8-core device — no margin for a slower
        # worker. So CI runs this 116-script security-critical subset and it must pass
        # (no `|| true`: a failing harness fails the build). The full suite result is
        # recorded in reports/test-report.md. The `timeout 1500` guard turns a slow
        # worker into an explicit failure instead of eating CI's whole 3600s slot.
        self.run(
            f'{LD_ENV} HARNESS_JOBS=4 timeout 1500 make test TESTS="{CI_UPSTREAM_TESTS}"',
            cwd=self.source_folder)


    def package(self):
        self.run("make install_sw", cwd=self.source_folder)

    def package_info(self):
        # OpenSSL provides libcrypto and libssl (not libopenssl)
        self.cpp_info.libs = ["ssl", "crypto"]
        self.cpp_info.system_libs = ["dl", "pthread"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
