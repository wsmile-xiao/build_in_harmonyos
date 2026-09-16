#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --source-url https://github.com/scipr-lab/libff/archive/refs/tags/v0.2.1.tar.gz --sha256 630010841f6992ad6e4758bb079d248eab46cfe66a4c0391c11075f3e5387b60 --name libff --version 0.2.1 --build-system cmake --libs ff --pkgconfig-name libff --homepage https://github.com/scipr-lab/libff --test-header libff/algebra/curves/alt_bn128/alt_bn128_pp.hpp --test-lang cpp --test-symbol alt_bn128_pp::reduced_pairing --out <输出根目录>
# 手动适配部分（生成器不覆盖，见 notes.md）：
#   - conanfile.py: requirements gmp/6.3.0.1 (transitive_headers) + openssl/3.5.6
#   - conanfile.py: generate() 固化 CURVE=ALT_BN128 / WITH_PROCPS=OFF /
#     CMAKE_POLICY_VERSION_MINIMUM=3.5 / IS_LIBFF_PARENT=ON
#   - conanfile.py: build() Debug 测试树（无 NDEBUG）构建+ctest 运行上游 3 测试
#   - test_package/: 真实核心 API（reduced_pairing 双线性断言）
