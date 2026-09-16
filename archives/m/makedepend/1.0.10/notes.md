# makedepend 1.0.10 适配笔记

## 基线

- 上游源码: `https://www.x.org/releases/individual/util/makedepend-1.0.10.tar.gz`
- SHA-256: `baf742fb6c76c15febf5181e5cd814066205d8be9aef4abfdc2c54b235e14917`
- 上游发布: 2026-08-17（当前上游最新版；仓库此前的 1.0.9 归档对应 2024-02-04 的旧版）
- 构建系统: autotools（tarball 自带 `configure` / `Makefile.in`，**不跑 autoreconf**）
- 许可证: `MIT-open-group AND HPND-sell-variant`（与上游 meson.build 声明一致）
- 交付物: `bin/makedepend` + `share/man/man1/makedepend.1`

## 依赖核验（W0）

makedepend **无第三方库依赖**：源码只 include libc/POSIX 头
（`ctype.h fcntl.h limits.h signal.h stdarg.h stdio.h stdlib.h string.h sys/stat.h sys/types.h sys/utsname.h unistd.h`），
零 X11 头文件引用，运行期仅需 libc。

| 依赖 | 类型 | 状态 |
|---|---|---|
| util-macros/1.20.1 | configure 期经 pkg-config 查询 `xorg-macros`（软依赖） | ✅ 已发布（ohpcd） |
| clang / make / sed / sh | 构建与测试工具 | ✅ CI 与设备齐备 |

`configure` 中的 `macros_datadir=\`$PKG_CONFIG --print-errors --variable=pkgdatadir xorg-macros\``
仅在缺失时打印警告、**不中断**（实测：无 xorg-macros.pc 时 configure 仍走完全程）。
配方仍按 X.Org autotools 包惯例 `tool_requires util-macros/1.20.1`，让该查询命中并把 `INSTALL` 复制流程走通。

## 与 1.0.9 历史归档的关系

1.0.9 是旧式归档（只有 `manifest.yaml` / `notes.md` / `README.md`，无
`conanfile.py`、`conandata.yml`、`test_package/`、`patches/`），且从未发布到制品仓。
其 manifest 里声明的两个 config 补丁**文件本体不在仓库**，来源目录
`/storage/Users/currentUser/builds/makedepend-1.0.9.orig` 已不存在 —— 因此本版本
的补丁是**基于 1.0.10 源码重新生成**的，不是复用。1.0.9 的 notes 作为踩坑清单已逐项比对。

## 平台适配（2 个补丁）

| 补丁 | 解决的问题 | 验证证据 |
|---|---|---|
| `0001-config.guess.patch` | **E007**：config.guess 不识别 HarmonyOS，configure 报 `cannot guess build type; you must specify one` | 补丁后 `sh config.guess` → `aarch64-unknown-linux-ohos`（rc=0） |
| `0002-configure-umask-fix.patch` | **E011**：configure 以 `umask 077` 创建临时目录，HMDFS 上 `config.status` 写 `subs*.awk` 报 `Permission denied` | 补丁后 configure rc=0，正常生成 `Makefile` / `makedepend-config.h` |

### 本版本**不需要**的两个补丁（与 1.0.9 / xinit 时代不同）

- **config.sub**：1.0.10 自带的 config.sub（timestamp `2024-05-27`）已内置 ohos
  （`ohos*` OS 白名单 + `linux-ohos*-` 内核组合校验），实测
  `sh config.sub aarch64-linux-ohos` → `aarch64-unknown-linux-ohos`。
- **RAWCPP**：makedepend 的 configure 中不存在 RAWCPP 探测（`grep -c RAWCPP configure` = 0），
  man page 由 `$(SED)` 生成，因此 xinit 式的 `${RAWCPP} < file` 重定向补丁不适用。

## 本地验证（设备 aarch64）

```bash
./configure --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos --prefix=$HOME/tmp/md-prefix2
# rc=0

make -j1
# rc=0 → makedepend: ELF 64-bit LSB shared object, ARM aarch64, dynamic (/lib/ld-musl-aarch64.so.1)

make check
# rc=0 → TOTAL: 2 / PASS: 2 / FAIL: 0  (tests/1、tests/28045)

makedepend demo.c            # 含 #include "dep.h" 的 C 源
# Makefile 追加:  "# DO NOT DELETE" + "demo.o: dep.h"

makedepend standalone.c      # 无 Makefile 的目录
# rc=1, "makedepend: error:  [mM]akefile is not present"
```

## Conan 配方端验证（conan create，与 CI 同源 profile）

```bash
conan create archives/m/makedepend/1.0.10 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# rc=0
```

- `Apply patch (portability)` ×2 —— 两个补丁均由 `apply_conandata_patches` 实际应用
- `checking for aarch64-unknown-linux-ohos-gcc... /data/service/hnp/bin/clang`
- `config.status: creating Makefile / makedepend-config.h` —— E011 已闭环（无 Permission denied）
- `CC/CCLD` 7 个对象 → `CCLD makedepend` → `package(): Packaged makedepend.1 + makedepend`
- `make check`（已嵌入 `build()`）：`# PASS: 2` / `# FAIL: 0`
- 打包二进制含 `.codesign` 节 —— `binary-sign-tool` 自签名生效
- test_package 4 项断言全部通过（PATH 可见 / `# DO NOT DELETE` / `demo.o: dep.h` / 无 Makefile 时失败）
- `util-macros/1.20.1` 由 ohpcd 正常解析并下载

非阻塞告警（已核实不影响构建与功能，留档备查）：

- `configure: WARNING: using cross tools not prefixed with host triplet`（clang 二进制未按 triplet 前缀命名）
- `configure: WARNING: ancient id detected; assuming current UID is ok` 与 `test: unknown: integer expected`（本机 `id` 输出格式所致，仅告警）
- `parse.c:274: warning: variable 'recurse_lvl' set but not used`（上游代码告警）

## 边界与遗留

- 上游测试用例均为 C++ 场景，test_package 额外覆盖 C 源解析与"无 Makefile 目录"负向场景。
- `make check` 已嵌入 `build()`（`autotools.make(target="check")`），CI 侧与本地同源。
- 发布二进制已在 `package()` 中用 `binary-sign-tool` 自签名（`.codesign` 节已确认存在），与 xinit 先例一致。
- 上游 1.0.10 新增 `meson.build`（meson ≥ 1.1.0）作为替代构建路径；本配方沿用 autotools 以与仓库主流一致，meson 路径留待需要时启用。
---

**编译结束**: 2026-09-12 18:39
**最终状态**: built
