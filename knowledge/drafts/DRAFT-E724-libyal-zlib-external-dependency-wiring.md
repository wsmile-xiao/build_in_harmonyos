# DRAFT-E724：libyal 用 zlib 成员的依赖判定与接线（单通道 + m4 DIR 分支永败 + 产物面采信）

> Status: **Draft**（待审核 promote）| severity: `2` | category: `conan|autotools|dependency|upstream-m4-bug|false-positive` | Updated: 2026-09-25
> 对应: `knowledge/drafts/DRAFT-E724-libyal-zlib-external-dependency-wiring.kv`
> 来源: libvmdk 20240510 适配（libyal/libvmdk @ tag 20240510, 34890e3d）——W0 依赖判定、采信轮 round-1 G2 失败复现与修复
> 取号: `knowledge_id.py --claim --task libvmdk-20240510` → E724（三面并集回查未占用）

---

**匹配关键词**：zlib, uncompress, AX_ZLIB_CHECK_ENABLE, zlib.h, unable to find supported zlib, libvmdk_compression, libvmdk_deflate, grain 解压, AutotoolsDeps, --with-zlib, NEEDED, libz, sysroot 自带, libyal 零外部依赖

## 错误签名（error_signature）

```text
unable to find supported zlib in directory|undefined reference to [`'"]?uncompress|checking for zlib\.h\.\.\. no|zlib\.h.*No such file|fatal error: ['"]zlib\.h['"] file not found
```

## 预扫（prescan）

- `prescan_pattern`: `AX_ZLIB_CHECK_ENABLE|uncompress\(|#include [<\"]zlib\.h|with-zlib=`
- `prescan_globs`: `configure.ac, m4/*.m4, **/*.c, conanfile.py`
- `prescan_severity`: 2

## 根因（root_cause）

三条实测事实：

1. **源码级硬依赖**：libvmdk 的 `libvmdk_compression.c`/`libvmdk_deflate.c`/`libvmdk_grain_data.c` 直接 include `zlib.h` 并调用 `uncompress()`（压缩 grain 解压），configure.ac 用 `AX_ZLIB_CHECK_ENABLE`/`AX_ZLIB_CHECK_UNCOMPRESS` 探测（`AC_CHECK_HEADERS(zlib.h)` + `AC_CHECK_LIB(z, zlibVersion/uncompress)`，尊重 CPPFLAGS/LDFLAGS）。这与 libyal 家族「13–14 个支持组件内嵌、零外部 Conan 依赖」的常见口径不同——W0 不能按家族惯例直接写 `none`，必须逐源码核。
2. **共享 m4 的 `--with-zlib=<DIR>` 分支永败（上游缺陷，本条核心）**：`m4/zlib.m4`（Version 20240314，libyal 家族共享）DIR 分支只把 `-I<DIR>/include`/`-L<DIR>/lib` 追加进 CFLAGS/LDFLAGS，随后走检查链把 `ac_cv_zlib` 置为 `zlib`；收尾终闸却是 `test "x$ac_cv_zlib" != xyes && <给了 DIR>` → `AC_MSG_FAILURE`。生成的 configure 全部 `ac_cv_zlib=` 赋值点只有 no/check/zlib——**`yes` 从未被赋值** ⇒ 只要显式给 DIR 就必然 `configure: error: unable to find supported zlib in directory: <DIR>`（libvmdk round-1 G2 实测）。不带该参数的自动探测路径（或裸 `--with-zlib`）不经过该闸，一切正常。
3. **OHOS SDK sysroot 自带 zlib 使裸探测也 yes（假象面）**：不接任何 zlib 接线的裸 configure（A/B 对照）同样打出 `checking for zlib.h... yes` / `checking for uncompress in -lz... yes`——SDK sysroot 的 `zlib.h`/`libz.so` 在 clang 默认搜索路径。于是「探测通过」既不能证明接了 conan zlib，也不能证明产物自包含：A/B 构建实测裸路径 NEEDED 含 `[libz.so]`（动态依赖 worker/SDK 环境），接线路径 NEEDED 仅 `[libc.so]`（conan libz.a 静态内嵌）⇒ **采信判据必须落在链接产物面**。

## 推荐方案（rec_approach: `conan-zlib-pin + autotoolsdeps-auto-detect-only + link-artifact-audit`）

配方口径（libvmdk 20240510 实测：round-1 因 DIR 参数 G2 红 → 移除后 round-2 的 configure/构建阶段越过该错误但 **round-2 仍 G2 FAIL**（另一独立问题：消费者断言缓冲 512 不足，另修 a5b30e5c8）→ **G2 整体转绿在 round-3 干净轮**）：

1. `requirements()`: `self.requires("zlib/1.3.2")`（W0-2 用 `conan install --requires=zlib/1.3.2 --profile:host=<ohos-aarch64> --build=never` 实证二进制可得 rc=0；清单落 `$TASK_DIR/w0-deps.txt`）；
2. `generators = "AutotoolsDeps"`（afflib 等 500+ 主线先例；zlib 的 include/lib 经 conanbuild 聚合环境注入 CPPFLAGS/LDFLAGS——`ConanFile.run` 默认 `env=conanbuild` 即取到）；
3. **不要**在 configure_args 里加 `--with-zlib=<DIR>`（见 root_cause 2，共享 m4 20240314 必然失败）；自动探测路径即为唯一通道；
4. **产物面三关采信**：configure 两探测 `... yes`（必要非充分）→ 链接行含 `-L<conan zlib>/lib … -lz` → `readelf -d libvmdk.so` 的 NEEDED **只有 `libc.so`（无 libz）** 且 `llvm-nm -D` 里 `uncompress`/`inflate*` 为 **T（内嵌导出）**——三关全过才算「静态自包含、不依赖 worker 运行期 libz」。

## 证据（evidence，逐字）

- 源码面：`grep -rln 'zlib\.h|uncompress' libvmdk/*.c` → `libvmdk_compression.c`、`libvmdk_deflate.c`、`libvmdk_grain_data.c`；configure.ac 为 `AX_ZLIB_CHECK_ENABLE` + `AX_ZLIB_CHECK_UNCOMPRESS`；同 spec 段 13 个内嵌组件列单不含 zlib ⇒ zlib 是唯一外部依赖（`w0-deps.txt` 单行 `zlib/1.3.2`）。
- W0 实证：`conan install --requires=zlib/1.3.2 --profile:host=ohos-aarch64 --build=never` rc=0，直接取 ohpcd 二进制（package id `6b129b06…`，目录仅 `libz.a`）。
- **m4 DIR 闸反面证据（round-1 G2，conan-create.log 逐字）**：

```text
checking for zlib.h... yes
checking for zlibVersion in -lz... yes
configure: error: unable to find supported zlib in directory: /storage/Users/currentUser/.conan2/p/zlibadde02423c9a0/p
```

  同一构建 configure 命令行含 `--with-zlib=/…/zlibadde02423c9a0/p`；生成 configure 的 `ac_cv_zlib=` 赋值点 grep 仅 54466 no / 54468 check / 54545 check / 54549 check / 54555 zlib / 54579 no / 54581 zlib / 54625 no（**无 yes**），终闸在 54644。移除该参数后 round-2 的 configure/构建阶段即越过该错误（该轮随后因另一独立的消费者测试断言缓冲问题未过 G2，与本条无关）；G2 整体转绿在 round-3 干净轮。
- 正证（有接线，`native-build.log` 逐字）：`checking for zlib.h... yes`、`checking for uncompress in -lz... yes`；编译行 `-I/storage/Users/currentUser/.conan2/p/zlibadde02423c9a0/p/include`；测试链接行 `-L/storage/Users/currentUser/.conan2/p/zlibadde02423c9a0/p/lib … -lz`。
- 负证（无接线裸 configure，`neg-zlib-configure.log` 逐字）：同样 `checking for zlib.h... yes` / `checking for uncompress in -lz... yes`——根因：OHOS SDK sysroot `.../ohos/native/sysroot/usr/include/zlib.h` 与 `libz.so` 在 clang 默认搜索路径。**探测读数不可单独采信的直接证据**。
- 产物面 A/B 对照（决定性）：**接线构建** `readelf -d libvmdk.so.1.0.0` NEEDED 仅 `Shared library: [libc.so]`（无 libz），`llvm-nm -D` 中 `uncompress`、`inflateEnd`、`inflate` 等全部 ` T `（zlib 静态内嵌并导出）；**裸路径构建**（`neg-zlib`，同参无接线）：

```text
0x0000000000000001 (NEEDED) Shared library: [libz.so]
0x0000000000000001 (NEEDED) Shared library: [libc.so]
0x000000000000000e (SONAME) Library soname: [libvmdk.so.1]
```

  同一源码两套链接面，接线与否的产物差异被逐字钉死——接线构建运行期不依赖 worker/SDK 的 libz。
- 交付验证：conan create 干净轮（采信轮 round-3 干净轮）G0–G4+L2/L4/L5 与 test_package 72 断言全绿（见 reports/ 与 evidence 副本）。

## 复现命令（verification_cmd，设备可直接执行）

```sh
# 1) 探测面（两路都 yes，仅作必要条件）
grep -E 'checking for zlib\.h\.\.\.|checking for uncompress in -lz\.\.\.' \
  $HOME/tmp/libvmdk-20240510/native-build.log $HOME/tmp/libvmdk-20240510/neg-zlib-configure.log
# 2) 产物面（决定性三关）
L=$HOME/tmp/libvmdk-20240510/native-src/libvmdk/.libs/libvmdk.so.1.0.0
grep -E '\-L.*zlib.*/lib .*-lz' $HOME/tmp/libvmdk-20240510/native-build.log | tail -1
readelf -d "$L" | grep NEEDED                 # 期望: 仅 Shared library: [libc.so]
llvm-nm -D "$L" | grep -E ' T uncompress$'    # 期望: zlib 已静态内嵌
# 3) m4 缺陷定位（决定性证据：yes 无赋值点）
grep -n 'ac_cv_zlib=' <conan 构建树>/configure          # 期望: 仅 no/check/zlib
grep -n -A2 'unable to find supported zlib' <conan 构建树>/configure
# 4) 干净轮：conan create 后同一库形态由 conan-verify G3/G4 复核（采信轮证据副本）
```

## 适用范围与边界

- **适用**：源码级使用 zlib 的 libyal 成员（libvmdk 实测；共享同一 `m4/zlib.m4 20240314` 的同版成员的 `--with-zlib=DIR` 同样必炸，需逐包核对 m4 版本行）与任何「家族惯例零外部依赖」但实际有压缩类硬依赖的包。
- **边界**：真正零外部依赖的 libyal 成员（configure.ac 无 AX_ZLIB、源码无 `zlib.h`）仍应 W0 写 `none`，不要照抄本条硬加依赖；sysroot 有无 zlib 不改变「产物应自包含」的目标，只改变不接线时的隐性后果。

## 关系

- **similar_to**：E011（HMDFS 平台差异族）、DRAFT-E586（libyal 家族假信号族）、DRAFT-E726（同任务的 libvmdk API 三坑）
- **caused_by**：家族捆绑惯例与个别成员压缩硬依赖的差异 + 共享 m4 DIR 分支终闸写错比较值 + SDK sysroot 恰好补齐了探测面（掩盖了接线缺失）
- **prerequisite_of**：libewf 等 libyal zlib 成员的依赖复核
- **conflicts_with**：无

---

*本文件由 `knowledge/drafts/DRAFT-E724-libyal-zlib-external-dependency-wiring.kv` 字段派生生成（补齐 kv↔md 配套）；内容与 kv 一致，待主编审核 promote 后转入 `knowledge/doc/`。*
