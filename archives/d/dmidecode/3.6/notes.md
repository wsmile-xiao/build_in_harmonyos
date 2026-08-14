# dmidecode 3.6 适配笔记

## 编译环境
- 构建系统: makefile (纯 Makefile，无 configure)
- 编译日期: 2026-07-01
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: **published** (Conan 配方验证全部通过)

## 编译步骤
1. 下载源码: `https://download.savannah.gnu.org/releases/dmidecode/dmidecode-3.6.tar.xz`
2. 解压: `tar xf dmidecode-3.6.tar.xz`
3. 编译: `make CC=clang -j1` (Makefile 使用 `CC ?= gcc`，需显式设置 clang)
4. Staging 安装: 手动 cp 到 DESTDIR (系统无 `install` 命令)

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | make install 失败 | 系统无 `install` 命令 | 手动 `cp` 到 staging 目录 |
| 2 | Conan 下载 SSL 失败 | Python ssl 默认 cafile=None | 设置 `SSL_CERT_FILE=/etc/ssl/certs/cacert.pem` |
| 3 | test_package VirtualRunEnv 失败 | conanrun.sh 依赖 `/bin/sh`，OHOS 无此路径 | 改用 `dep.package_folder` 直接构建二进制路径 |
| 4 | env_info 弃用警告 | Conan 2.x 弃用 env_info | 改用 `cpp_info.bindirs = ["bin"]` |

## 编译警告
- 96 个 cast-align 警告 (dmioem.c) — aarch64 上预期行为，不影响功能
- 240 个 cast-align 警告 (dmidecode.c) — 同上
- 警告源于 WORD/DWORD/QWORD 宏的类型转换，config.h 已定义 USE_SLOW_MEMCPY 缓解

## 依赖版本
- 无外部编译依赖
- 运行时仅依赖 musl libc (libc.so)

## 平台兼容性
- config.h 已有 `__aarch64__` 支持 (`USE_SLOW_MEMCPY`)
- Makefile 的 `MACHINE` 变量在 aarch64 上仅编译 dmidecode（不编译 x86 专用的 biosdecode/ownership/vpddecode）

## 功能测试摘要
- 全部 20 项功能测试通过
- --version / --help / --list-strings / --list-types: ✅
- 默认运行 (无 /dev/mem): 优雅处理 ✅
- --from-dump 离线解析: SMBIOS 解析引擎正确 ✅
- 类型过滤 (-t) / 字符串查询 (-s) / Handle 过滤 (-H): ✅
- 安静模式 (-q) / 原始 dump (-u) / 无 quirks (--no-quirks): ✅

## 平台限制
- HarmonyOS 无 `/dev/mem` — 无法直接读取物理内存中的 SMBIOS 数据
- 无 sysfs DMI 表 (`/sys/firmware/dmi/tables/`, `/sys/class/dmi/id/`)
- 影响: 直接读取硬件 DMI 信息不可用，但 `--from-dump` 离线分析完全可用

## Conan 配方
- conanfile.py: `make CC=clang -j1`，打包 bin/dmidecode
- conandata.yml: sha256 已填写
- test_package: L2 smoke test (`dmidecode --version`)
- 验证结果: G0-G4 + L2/L4/L5 全部 PASS

---

**编译结束**: 2026-07-01
**最终状态**: published
