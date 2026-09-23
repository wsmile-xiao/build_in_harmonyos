# wolfssl 5.7.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-06
- 编译器: clang 15.0.4
- 平台: aarch64-unknown-linux-ohos (HarmonyOS)
- 状态: built

## 编译步骤
1. **init-build**: GitHub tag archive v5.7.0-stable 下载，SHA-256=2de93e8a... 核验
2. **autoreconf**: GitHub archive 不含生成的 configure，需 `autoreconf -fi`
   - 手工环境需 PERL5LIB=automake/share/automake-1.18、ACLOCAL_PATH=libtool/share/aclocal、
     `_lt_pkgdatadir`=libtool/share/libtool(仅手工构建；conan tool_requires 自动注入)
3. **E007**: `--build/--host=aarch64-unknown-linux-ohos` 显式 triplet(config.guess 不识别 HarmonyOS)
4. **E011**: configure 中 umask 077→022(HMDFS 临时目录权限)
5. **configure**: `./configure --prefix=$DEFAULT_PREFIX --enable-static --disable-shared`
6. **make**: `make -j1`(E074: HMDFS jobserver fifo EPERM→禁并行)
7. **make check**: 8 TOTAL;testsuite/resume/tls13/pem/google PASS,
   external/openssl SKIP(exit 77,网络),unit 1 FAIL(过期根证书,见下)

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 | 知识图谱 |
|---|------|------|----------|----------|
| 1 | configure: cannot guess build type | E007: config.guess 无 HarmonyOS 分支 | --build/--host=aarch64-unknown-linux-ohos | E007 |
| 2 | configure: umask 077 临时目录拒绝 | E011: HMDFS umask | configure 内 umask 077→022 | E011 |
| 3 | libtoolize: pkgauxdir //share/libtool/... 不存在 | conan libtool 包 prefix=/ | 手工构建设 `_lt_pkgdatadir`；conan 环境无需 | — |
| 4 | scripts/*.test exit 126 bad interpreter /bin/bash | OHOS 无 /bin/bash(只读 /bin) | 显式 bash scripts/x.test 运行 | — |
| 5 | unit.test: test_wolfSSL_CTX_load_verify_locations FAIL | certs/external/baltimore-cybertrust-root.pem 2025-05 过期,ASN_AFTER_DATE_E=-151 | 测试数据随日期老化，非库缺陷；探针确认仅该文件失败 | — |

## 源码修改
无补丁文件(patches/ 为空)。E007/E011 修复在 conanfile.py generate()/build() 中实现。

## 依赖版本
- 无外部运行依赖(仅 libc.so)
- tool_requires: automake/1.18, libtool/2.5.4(CI worker 缺 aclocal/libtoolize m4)

## 验证结果
### conan-verify(全 PASS)
```
G1 配方完整性: PASS
G0 预构建风险评估: PASS
G2 conan create: PASS
G3 系统同名库隔离 (R26): PASS
G4 产物完整性: PASS
L2 平台功能矩阵: PASS
L4 静态安全扫描: PASS
L5 产物基线对比: PASS
```
test_package 实际运行: `wolfSSL version: 5.7.0`

### 测试统计(双口径)
- source_declared_total = 948(tests/api.c testCases[] 940 + make check TESTS 8)
- 执行: testsuite PASS / unit 178 passed 1 failed(过期证书)+676 skipped /
  resume/tls13/pem/google PASS / external/openssl SKIP(exit 77)
- 鸿蒙专项 ohos_verify: SHA256 RFC6234 + ECC P-256 sign/verify + RNG 全 PASS
- 详见 tests/台账: 12-test-ledger.md

## 注意事项
1. wolfssl 是纯库软件
2. 测试脚本 shebang #!/bin/bash 在 OHOS 不可解析(无 /bin/bash)，需显式 bash 运行
3. unit.test 中 baltimore 根证书过期属于测试数据老化，非库缺陷，不阻塞功能验证
4. 静态库 libwolfssl.a 782KB

---
**编译结束**: 2026-09-06
**最终状态**: built
