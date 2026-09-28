# libxutils 2.8.42 适配笔记

## 编译环境
- 构建系统: cmake（上游以 CMake 为主构建，registry 初判 autotools 已更正）
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4（aarch64-linux-ohos profile）
- 状态: built（conan-verify 全门禁通过，制品未上传）

## 编译步骤
1. init-build libxutils 2.8.42 --url=https://github.com/kala13x/libxutils（官方 tag v2.8.42）
2. lang-preflight：检测 c（task=cpp，兼容族），通过
3. 上游测试：cmake -DXUTILS_BUILD_TESTS=ON 构建后 ctest 全量运行（见 reports/test-report.md）
4. conan-init 生成 conanfile.py/conandata.yml/test_package
5. conan-verify：G0-G4 + L2/L4/L5 全部通过
6. finish built：W2 结构、R36 依赖、W3 本地 CI（conan create + test_package）通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 log_regression 两用例失败（file_output/rotation） | OHOS 平台 /tmp 只读（E002），测试硬编码 mkdtemp("/tmp/...") 失败 | patches/0001-tests-log_regression.c.patch：改用 $TMPDIR（缺省回退 /tmp），CI 环境 /tmp 可写不受影响 |
| 2 | G2 conan create 失败：'xstd.h' file not found | 安装后内部头以相对方式互引（base64.h → "xstd.h"），消费者 include 路径缺 include/xutils | conanfile.py package_info() 增加 cpp_info.includedirs = ["include", "include/xutils"] |

## 源码修改
- patches/0001-tests-log_regression.c.patch（+13/-2）：log_regression.c 增加可写临时目录解析，替换两处硬编码 /tmp

## 依赖版本
- 无外部 Conan 依赖（libxutils 自包含；上游可选 OpenSSL 未启用）

## 验证结果
```bash
# 上游回归测试（本机 aarch64-ohos 环境）
ctest -j4  →  234 passed / 2 skipped（jwt_regression.rs256、buf_regression.read_stdin 平台性跳过，SKIP_RETURN_CODE 77）
# Conan 配方验证
ohc-run.py conan-verify libxutils 2.8.42  →  G0-G4 + L2/L4/L5 全部 PASS
# W3 本地 CI
ohc-run.py finish libxutils 2.8.42 built   →  W3: conan create 通过（test_package 1/1），.ci-result.json exit_code=0
```

## 注意事项
- /tmp 在本平台只读，涉及临时目录的上游测试/脚本需经 $TMPDIR 适配（知识：E002 类）
- 内部头相对互引的静态库，package_info 必须补 include/<lib> 子路径
---

**编译结束**: 2026-09-27 20:44
**最终状态**: built
