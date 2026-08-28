# lziprecover 1.26 — OpenHarmony 编译记录

## 上游核实

- **项目**: lziprecover — lzip (.lz) 格式数据恢复与解压工具
- **作者**: Antonio Diaz Diaz (lzip 系列同一作者)
- **上游页面**: https://www.nongnu.org/lzip/lziprecover.html
- **源码 URL** (Savannah GNU 镜像):
  - https://download-mirror.savannah.gnu.org/releases/lzip/lziprecover/lziprecover-1.26.tar.gz
  - https://download.savannah.gnu.org/releases/lzip/lziprecover/lziprecover-1.26.tar.gz
- **SHA256**: `e234005a756d5649f41686116d3e548736d4a77e5a5ec37b943ca6650787801d`
- **License**: GPL-2.0+ (COPYING 文件确认)
- **构建系统**: 自定义 configure 脚本 (非 GNU autoconf), lzip 系列通用
- **语言**: C++ (CXX), 非 C

## 编译器接收方式 (E095)

lzip 系列的 configure 脚本 **不读取环境变量 CC/CXX**, 而要求命令行参数
`CXX=<compiler>`。本 recipe 在 `generate()` 中从 Conan conf
`tools.build:compiler_executables` 取编译器, 以 `CXX=` 参数传入 configure。
不使用 shell 环境变量, 不硬编码路径。

## OHOS 工具链

- 编译器: `clang++` (实际为 clang-15, target=aarch64-linux-ohos, -fuse-ld=lld, -D__MUSL__)
- 来源: Conan profile `ohos-aarch64-local` 的 `tools.build:compiler_executables`
- 产物: ELF64 AArch64, PIE (DYN), 动态链接 musl (ld-musl-aarch64.so.1)
  + OHOS C++ 运行时 (libc++_shared.so + libc.so)
  - readelf -h: Class=ELF64, Machine=AArch64, Type=DYN (PIE)
  - readelf -l: INTERP=/lib/ld-musl-aarch64.so.1 (musl libc)
  - .note.ohos.ident section 存在 (OHOS 标识)

## 零 Patch

无任何 patch。conandata.yml 中 `patches: {}`。所有构建逻辑通过原版
configure + make 完成, 未修改任何上游源文件。

## 上游正式测试 (make check)

lziprecover 上游 testsuite (`testsuite/check.sh`) 在 build() 阶段完整执行。
该 testsuite 需要 `lzip` 压缩器作为辅助工具 (LZIP_NAME, 默认 `lzip`)。
因 lzip 未发布到 OHOS registry, 在 build() 内从源码构建 lzip 并通过
LZIP_NAME 传入, 实现零外部依赖运行完整官方测试。

测试统计:
- **Total sections**: 10 (decompression, bad input, --byte-repair, --fec,
  --merge, --reproduce, --split, --dump/remove/strip, --dump/remove/strip=damaged,
  trailing data)
- **Assertions**: 864 (`test_failed $LINENO`) + 213 framework checks
- **Pass**: 10/10 sections — "tests completed successfully."
- **Fail**: 0
- **Skip**: 0

## package_type 与 commands.json

lziprecover 是纯 CLI 工具 (非库), `package_type = "application"`。
`archives/l/lziprecover/commands.json` 中 `type = "tool"`。

## install 策略

OHOS 无 `install` coreutil。Makefile 的 install 依赖 `install` 命令。
本 recipe 用 Conan `copy()` 直接将 `lziprecover` 二进制从 build 目录复制到
`bin/`, 实现零 patch 安装。不依赖 host install 命令。

## test_package (真实文件级功能测试)

test_package 提交了三个 fixture (不需要外部 lzip):
- `fixture.txt` — 明文参考 (440 bytes)
- `fixture.txt.lz` — lzip 压缩 (95 bytes)
- `damaged.lz` — fixture.txt.lz 的副本, offset 40 字节翻转为 0xFF

测试 (conanfile.py::test()):
1. `--version` 冒烟 (断言含 "lziprecover 1.26")
2. `-t` 完整性校验 (valid .lz)
3. `-cd` 解压 → sha256 比对 (byte-for-byte)
4. `-B` 字节修复损坏文件 → `-cd` 解压 → sha256 比对 (恢复后内容 == 原文)

全部通过。不允许只跑 --version。

## libxml2.so.16 / LD_LIBRARY_PATH

本次构建未触发 libxml2.so.16 缺失问题 (lziprecover 不依赖 libxml2)。
若 SDK clang→lld 报该错, 应动态定位 SDK LLVM lib 目录并仅对 OHOS 构建设置
LD_LIBRARY_PATH, 不硬编码本机路径。本 recipe 不涉及此问题。

## CI gate 结果

`zsh ci/conan/build_and_note.sh archives/l/lziprecover/1.26` 全部通过:
- L0_RESULT=pass (所有质量门)
- L1_RESULT=pass (upstream make check + test_package 执行)
  - L1a: test_package 被 conan create 执行
  - L1b: 测试证据在日志中
  - L1c: 上游官方测试 (make check) 在 build 阶段执行
  - L1e: 负面测试 (R34) — 删除 bin/ 后 test 真正失败
- L2_RESULT=pass (lziprecover --version OK)
- L4_RESULT=pass (无 patch)
- L5_RESULT=pass (bin/ 有内容)
- Total: 1, Success: 1, Failed: 0, Pass rate: 100%

## 清理

- Conan 生成的脚本 (conanrunenv-*.sh, conanbuild.sh 等) 已从 test_package/ 删除
- 本地下载缓存目录已删除
- CI 临时 scope diff 文件已删除
- CI 生成的元数据 JSON 已删除
- test_package/ 构建产物 (out.txt, repaired.txt, version.txt, repaired.lz) 已删除
- conandata.yml 被 CI 预下载缓存污染的本地协议 URL 已恢复为 https 上游 URL

## 禁止模式检查

最终对源码树扫描全部禁用词串 (本地文件协议、预下载缓存、本机用户名、
本机绝对路径前缀、临时 diff、CI 元数据文件名): **零匹配** (clean)。

## git status

```
?? archives/l/lziprecover/   (lziprecover 全部为未跟踪新增文件)
 M archives/l/libXext/README.md   (预存改动, 未触碰)
 M archives/l/libXext/manifest.yaml  (预存改动, 未触碰)
```

未 commit, 未 push。仅改 `archives/l/lziprecover/`。
