# libXau 1.0.12 适配笔记

## 编译环境
- 构建系统: autotools（官方 tarball 自带预生成 configure/Makefile.in，无需 autoreconf）
- 编译日期: 2026-08-08
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos, 本机原生编译)
- 状态: built

## 编译步骤

```bash
# 依赖：xorgproto/2025.1（制品仓已发布，提供 X11/Xfuncproto.h 与 xproto.pc）
conan install --requires=xorgproto/2025.1 -r=ohpcd \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64

source .build-context-libXau-1.0.12 && cd $BUILD_SRC_DIR
export PKG_CONFIG_PATH=<xorgproto pkgconfig 路径>
export CONFIG_SHELL=/data/service/hnp/bin/bash
export SED=$(which sed)

# E205: config.guess/config.sub 打 OHOS 补丁（代替 --build/--host，R15 禁止）
perl $SKILL_ROOT/scripts/patch-autotools-ohos.pl config.guess config.sub
# 补丁脚本 step 2.3 因 config.sub 中已存在 'linux-ohos'（其他位置）被跳过，
# 内核-OS 校验列表缺少 linux-ohos*-，手动补充（见"源码修改"）

./configure --prefix=$DEFAULT_PREFIX
make -j1
make -j1 check        # 上游测试：PASS 1/1 (Autest)
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Invalid configuration 'aarch64-unknown-linux-ohos': Kernel 'linux' not known to work with OS 'ohos'` | config.guess/config.sub (2024-01-01) 不识别 HarmonyOS | E205: 打 patch-autotools-ohos.pl；并手动在 config.sub 内核-OS 校验列表补 `linux-ohos*-`（补丁脚本 2.3 步因 `linux-ohos` 已在 basic_os 分支出现而误判跳过） |
| 2 | `./confipAimG/subs1.awk: Permission denied`（configure 生成 config.status 时） | E002/HMDFS：configure 用 `umask 077` 创建临时子目录，subs1.awk 无法执行 | configure 中 `umask 077` → `umask 022`（与 libXau 1.0.11 同款修复） |
| 3 | `Package xorg-macros was not found` | 仅影响文档生成（XORG_MACROS_VERSION 检查），configure 继续 | 非致命；配方用 `--disable-docs` 排除文档生成 |
| 4 | 下载 tarball 时 release 域名 `releases/...` 连接被关闭 | 官方源该路径 502/断连 | 改用官方 archive 镜像 `https://xorg.freedesktop.org/archive/individual/lib/libXau-1.0.12.tar.xz` |
| 5 | conan create 报 `Conan packages names 'libXau/...' must be all lowercase` | Conan 要求包名全小写 | conanfile `name = "libxau"`（1.0.11 同款） |
| 6 | test_package 中 `tmpfile(): Permission denied` | OHOS `/tmp` 只读（E002），且 musl `tmpfile()` 忽略 `TMPDIR` 恒走 `/tmp` | test 改用 CWD 常规文件 `fopen(AUTH_FILE,"w+b")` 做往返，`remove()` 清理 |
| 7 | 上游 Autest 在 OHOS 上"必然通过" | 上游 `Autest.c` 末行 `return (state = 1) ? 0 : 1;` 是赋值表达式恒真，`tmpfile()` 失败（返回 NULL）时跳过写入块仍返回 0 | 不改上游测试；test_package 提供真实 API 往返验证（R34） |

## 源码修改

探索阶段直接修改（补丁由 finish refresh-patch --auto 固化）：
1. `config.guess` — patch-autotools-ohos.pl：`__OHOS__` LIBC 检测 + `*:HarmonyOS:*:*` 识别分支
2. `config.sub` — patch-autotools-ohos.pl：`ohos-linux)` triplet + `ohos*` OS 列表；手动补内核-OS 校验列表 `| linux-ohos*-`
3. `configure` — `umask 077` → `umask 022`（两处，E002/HMDFS）

## 依赖版本

- xorgproto/2025.1（制品仓 ohpcd 预编译包，唯一依赖，提供 xproto.pc + X11 头文件）
- autotools（本机：autoconf 2.72 / automake 1.16.5，tarball 自带 configure 故仅 libtool 参与）

## 验证结果

```bash
$ make -j1 check
PASS: Autest
Testsuite summary for libXau 1.0.12
# TOTAL: 1  # PASS: 1  # FAIL: 0  # SKIP: 0  # ERROR: 0

$ ls test-install.../usr/local
lib/libXau.so.6.0.0 lib/libXau.a lib/libXau.la include/X11/Xauth.h lib/pkgconfig/xau.pc share/man/man3/*.3
```

## 交付物

| 文件 | 说明 |
|------|------|
| libXau.so.6.0.0 / libXau.so.6 / libXau.so | 共享库（-version-number 6:0:0） |
| libXau.a | 静态库 |
| include/X11/Xauth.h | 唯一头文件 |
| lib/pkgconfig/xau.pc | pkg-config 元数据 |
| share/man/man3/Xau*.3 | 9 个 man page |

## 注意事项

- 上游测试仅 1 个：`Autest`（check_PROGRAM，XauWriteAuth 写 tmpfile 往返测试），100% 通过。
- libXau 是纯库包，无可执行文件 → R38 不需要 commands.json。
- 非系统同名库（系统无 libXau），保持动态 .so（R26 不适用）。
- config.guess/sub 补丁逻辑与 libXau 1.0.11 一致；新发现：patch-autotools-ohos.pl 对新版 config.sub（`linux-uclibc*- )` 带尾部 `-`）会误判 2.3 步，需手工补充 `linux-ohos*-` 到内核-OS 校验列表（已在 E205 相关笔记记录）。
---

## 复核记录（2026-08-08 打回修复）

- 上一轮 conan-verify G2 为**缓存命中**（`--build=missing` 命中 `~/.conan2/p/b/libxae2e2488506516`），无 build() 阶段日志，无法证明从源码可复现构建。
- **清缓存重建**：`conan remove "libxau/1.0.12*" -c` 移除 recipe+二进制（含第二个构建目录 `libxa760867d8b8301`，保留配方/源码节点 `p/libxad3fc7d036d3ec`、`p/libxac3904347575f0`）。
- 根因二：conan-verify 的 ref 用 `libXau`（大写）与 conan 包名 `libxau`（小写）不匹配，导致 G3/G4/L2/L4/L5 跳过。改用 `ohc-run.py conan-verify libxau 1.0.12`（小写）。
- 重跑后**从源码真实构建**，全部门禁 G0-G4/L2/L4/L5 均 PASS：
  - make check：`PASS: Autest` / `Testsuite summary for libXau 1.0.12` / `# TOTAL: 1  # PASS: 1`
  - test_package：`XauWriteAuth/XauReadAuth round-trip: OK` / `libXau consumer API test: OK`
  - 手动核实：包产物 lib/libXau.so{,.6,.6.0.0} + include/X11/Xauth.h 完整；R26 系统 `/lib`、`/lib64` 无 libXau 无冲突；L4 readelf GNU_RELRO/GNU_STACK/BIND_NOW 安全属性符合预期。

---

**编译结束**: 2026-08-08 10:04（首次）/ 2026-08-08 10:45（复核重建）
**最终状态**: built
