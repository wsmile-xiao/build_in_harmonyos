# turbo 2.1.2 适配笔记

## 编译环境
- 构建系统: makefile (plain Makefile, no configure)
- 编译日期: 2026-07-16
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码: https://github.com/kernelsauce/turbo/archive/refs/tags/v2.1.2.tar.gz
2. 应用补丁:
   - 0001-Makefile.patch: 修复 HarmonyOS 平台检测 (uname -s 返回 "HarmonyOS")
   - 0002-deps-http-parser-Makefile.patch: 使用 clang 替代 gcc
3. 编译: `make -j1 SSL=none`
4. 安装: `make SSL=none PREFIX=$TEST_PREFIX install`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 编译时找不到 openssl/ssl.h | 系统有 libssl.so.3 但无开发头 | 使用 SSL=none 禁用 SSL 支持 |
| 2 | libtffi_wrap.dll 被创建而非 .so | uname -s 返回 "HarmonyOS"，Makefile 只检查 Linux 和 Darwin | 在 Makefile 中添加 HarmonyOS 到 uname_S 检查 |
| 3 | install 时 cp -a 失败 | SYMLINK=cp -a 使用相对路径而非安装路径 | 修改为使用 $(INSTALL_TFFI_WRAP_DYN) 完整路径 |
| 4 | Python SSL 模块不可用 | libssl.so.3 不在 LD_LIBRARY_PATH 中 | export LD_LIBRARY_PATH="/usr/lib:$LD_LIBRARY_PATH" |
| 5 | test_package 中 http_parser 结构体不匹配 | 自定义结构体与实际布局不同 | 使用正确的 bitfield 定义匹配源码 |

## 源码修改

- Makefile: 添加 HarmonyOS 到 uname_S 检查 (ifneq filter Linux HarmonyOS)
- Makefile: 修复 SYMLINK 路径为完整安装路径
- Makefile: CC=gcc → CC=clang
- Makefile: SYMLINK=ln -sf → SYMLINK=cp -a (HMDFS 兼容)
- deps/http-parser/Makefile: CC=gcc → CC=clang

## 依赖版本

- 无外部 conan 依赖 (SSL=none 禁用了 OpenSSL)
- 系统库: libssl.so.3 (用于 Python SSL 模块，非编译依赖)

## 验证结果

```bash
$ conan-verify: PASS (G1-G4 + L2/L4/L5)
$ build_and_test.sh: PASS (L0-L5 全部通过)
```

## 二次校准 (2026-07-17)

1. 移除 PR 中的状态文件 (.audit-result.json, .build-closed) 和 reports/ 目录
2. 修复 patch 0002: http-parser Makefile 添加 HarmonyOS 平台检测 (-fPIC)
3. 修复 manifest.yaml: 填充 sha256, 修正 build.system 为 makefile
4. 修复 conanfile.py: package_info() 添加 libhttp_parser 到 cpp_info.libs

## 注意事项

- SSL 支持已禁用 (TURBO_NO_SSL=1)，因为 OpenSSL 尚未作为 conan 包发布到 ohpcd 制品仓
- 当 OpenSSL 发布后，可在 conanfile.py 中添加 `self.requires("openssl/版本")` 并移除 SSL=none
- turbovisor 是 LuaJIT 脚本而非编译二进制，commands.json 中 binary=false
---

**编译结束**: 2026-07-16 01:34
**最终状态**: built
