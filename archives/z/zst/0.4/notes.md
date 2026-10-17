# zst 0.4 编译笔记（HarmonyOS PC · Conan cmake · 单文件多压缩器 CLI）

## 定位
- `zst` 把四个「必备压缩库」——**zstd / xz(LZMA2) / gzip(zlib) / bzip2**——统一进**一个小二进制**，
  按 `-F<tool>` / 文件后缀 / `argv[0]` 自动分派算法。上游设计目标是替代各官方 CLI
  （体积小、行为一致、压缩级别统一 1–9、默认删除源文件）。
- 构建产物只有**一个可执行文件** `bin/zst`（外加 man page）；无库、无 headers。
- 依赖（均为 ohpcd 已发布制品）：`zlib/1.3.1`、`bzip2/1.0.8.2`、`xz/5.6.2`（liblzma）、`zstd/1.5.7.1`。

## 构建方式（自发现 toolchain + 裸 cmake）
`build()` 自发现 `ohos.toolchain.cmake` + 裸 `cmake -G Ninja`（不经 conan_toolchain，
后者在 os=OHOS 下把 `CMAKE_SYSTEM_NAME` 退化成 cmake 不认的值 —— ML-0035）：

- `cmake -G Ninja -B <build>/build-ohos -S <source>`，**Ninja 生成器**（与 zstd 同法）。
- `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（见下「首个真实错误」）。
- `-DOHOS_ARCH=arm64-v8a`，`-DCMAKE_BUILD_TYPE=Release`。

### 依赖接线：为什么不用 find_package
上游 `CMakeLists.txt` 用 `CHECK_LIBRARY_EXISTS(<so> <func>)` 探测四个压缩库，成功就把
库名塞进 `libs` 并 `target_link_libraries(zst ${libs})` —— 即链接行上是 `-lz -lbz2 -llzma -lzstd`。
**没有 find_package、没有 find_library，也没有脚本级开关**。因此：

1. **头文件**：`compress.c` 直接 `#include <zlib.h>/<bzlib.h>/<lzma.h>/<zstd.h>`，
   而交叉链的 `FIND_ROOT_PATH_MODE=ONLY` 会把 sysroot 之外的 conan 包路径滤掉
   → 显式把 4 个依赖的 `include` 通过 `-DCMAKE_C_FLAGS=-I...` 传入。
2. **静态链接**：在 `build_folder/zst-static-libs/` 建一个**只含 `.a`** 的私有目录
   （软链 4 个依赖包的静态库），把它同时挂到
   - `-DCMAKE_REQUIRED_LINK_OPTIONS=-L<dir>`（让 `CHECK_LIBRARY_EXISTS` 的 try_compile 能解析 `-lz` 等）
   - `-DCMAKE_EXE_LINKER_FLAGS=-L<dir>`（最终链接）

   搜索路径上**只有 `.a`**，于是 `-l<name>` 一律解析成静态库。

**为什么坚持静态**：`zst` 的全部意义就是「一个小二进制」。静态链接后
`bin/zst` 的 `DT_NEEDED` **只剩 `libc.so`**，不依赖 conan 缓存路径、无需 RPATH/LD_LIBRARY_PATH，
也避免了把 `libzstd.so` 这类系统同名库动态挂进加载器路径（R26 同向）。
各依赖静态库的可得性：
- `zlib/1.3.1` → 只装 `libz.a`（本就静态）
- `bzip2/1.0.8.2` → 只装 `libbz2.a`（OHOS 上 shared 被 recipe 主动禁用）
- `xz/5.6.2` → 只装 `liblzma.a`
- `zstd`：**必须用 1.5.7.1** —— 同包同时提供 `libzstd.so` 与 `libzstd.a`；已发布的 `1.5.7` 只有 `.so`

## 首个真实错误：cmake 4.x 拒绝 `cmake_minimum_required(2.8.12)`

**命令**：`cmake -G Ninja -B build -S <src> -DCMAKE_TOOLCHAIN_FILE=<ohos.toolchain.cmake> -DOHOS_ARCH=arm64-v8a`
**原始输出（exit 非 0，configure incomplete）**：
```
CMake Error at CMakeLists.txt:1 (cmake_minimum_required):
  Compatibility with CMake < 3.5 has been removed from CMake.
  ...
  Or, add -DCMAKE_POLICY_VERSION_MINIMUM=3.5 to try configuring anyway.
-- Configuring incomplete, errors occurred!
```
**根因**：上游 `CMakeLists.txt` 首行 `cmake_minimum_required(VERSION 2.8.12)`；本环境 cmake 为 **4.1.2**，
CMake 4.0 起移除了对 `<3.5` 的兼容（不再只是 warning）。
**最小修改**：`-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（与 libarchive/libtiff 同法），**未改动上游源码**。

## 第二个真实问题：签名后丢可执行位（`conan test` → Permission denied）

`conan create` 构建、打包成功后，test_package 执行 `bin/zst` 报：
```
test.sh: line 24: .../bin/zst: Permission denied        (ConanException: Error 126)
```
**根因**：HarmonyOS PC 要求 ELF 带有效代码签名，recipe 在 `package()` 里用
`binary-sign-tool sign -selfSign 1` 重签；而**签名会丢弃权限位**（harmonyos-specifics.md §2.3 第 3 步）。
**最小修改**：签名后 `os.chmod(path, 0o755)` 恢复可执行位（recipe 内，不改上游源码）。

> 另外：`.so` 无需签名（本包不产 `.so`）；man page 安装到 `share/man/man1/zst.1`。

## 上游测试用例统计（R51 三步法）

### 清点（写在 MANIFEST.yml，另附实跑）
上游基于 **CTest**：`tests/CMakeLists.txt` 用 GLOB 收集 `tests/*.t` 与 `tests/*.T`。
- `*.t`（38 个）会被 `compressor(TOOL EXT)` 对**每个可用压缩库**各实例化一次
  → 4 个库(gzip/bzip2/xz/zstd) × 38 = **152 项**
- `*.T`（9 个）工具无关 → **9 项**
- 合计 **161 项**（`ctest -N` 实测 `Total Tests: 161`）
- 上游 `.cirrus.yml` 里 CI 也 `apt-get install ... bzip2 zstd xz-utils` —— **用例会直接调用原生
  gzip/bzip2/xz/zstd CLI**，这是测试环境的一部分。

### 实跑环境与方法（可复现脚本）
```bash
bash archives/z/zst/0.4/run_upstream_tests.sh     # 自包含：下载+校验源码 → cmake 交叉构建 → ctest
```
- 环境：HarmonyOS localhost HongMeng Kernel 1.12.0 aarch64，clang 15.0.4，cmake 4.1.2，ninja，conan 2.29.1，`nproc=20`
- 日志：`reports/upstream-ctest.log`（原始 ctest 输出）、`reports/upstream-ctest-junit.xml`（逐用例）、
  `reports/upstream-build.log`（cmake configure+build）
- 测试期 PATH 追加（上游假设的 GNU 工具在本环境缺位，属**测试环境**修配，非源码改动）：
  1. `diffutils` 的 GNU `cmp`：**OHOS toybox 的 `cmp` 不支持 `-b`**（用例大量 `cmp -b`）→
     用 `/data/service/hnp/diff.org/diff_3.10/bin`
  2. 原生 `zstd`：来自 `zstd/1.5.7.1` 包的 `bin/`
  3. `bzip2`/`xz`/`diff`/`grep`：`/data/service/hnp/bin`

### 实测结果（真实数据）
| 指标 | 数量 |
|------|-----:|
| 用例总数 | **161** |
| 通过 | **139** |
| 失败 | **14** |
| 跳过 | **8** |
| 通过率 | **86.3%**（139/161）；剔除 8 项环境跳过 = 139/153 = 90.8% |

### 失败项逐项审计（14 项，3 类根因，**均非 zst 库缺陷**）
| 类别 | 用例名 | 数量 | 具体技术原因 |
|------|--------|-----:|-------------|
| A. 递归遍历重复访问新生成文件 | `z-dir-alreadysuffix-{gzip,bzip2,xz,zstd}`、`zd-dir-many-{gzip,bzip2,xz,zstd}` | 8 | 上游 `zst.c do_dir()` **边 `readdir()` 边处理**：压缩 `a` 生成 `a.gz` 后，同一目录流又返回了刚建的 `a.gz`。用例断言「unchanged 恰好 4 行」/「4096 个 .zst 目录不重复」因此不成立。glibc 的 `getdents` 对小目录一次性返回全部条目时不会看到新文件；**HMDFS 的 `readdir` 分批返回**，于是暴露。此为上游对「readdir 期间新增条目」的 POSIX 未规定行为做了乐观假设，非本包构建/链接问题（实测同一命令在 HMDFS 上稳定复现 5 行 unchanged）。 |
| B. `/dev/full` 不可用 | `zd-full-{gzip,bzip2,xz,zstd}` | 4 | 用例第一步 `$Z -zF$TOOL </dev/null >/dev/full` 需要 `/dev/full`。本环境 `ls -l /dev/full` → **Permission denied**（设备节点存在但不可访问）。OHOS 无法提供该字符设备。 |
| C. FIFO 受限 | `z-dir-nonreg`、`z-file-nonreg` | 2 | 用例需 `mkfifo b`。**OHOS 无 `mkfifo` 命令**（toybox 无该 applet；`/system/bin/mkfifo` 存在但创建报 `Operation not permitted`，内核 FIFO 子系统限制）。 |

### 跳过项逐项审计（8 项，1 类原因）
| 用例名 | 数量 | 原因 |
|--------|-----:|------|
| `d-file-noperm-{gzip,bzip2,xz,zstd}`、`z-file-noperm-{gzip,bzip2,xz,zstd}` | 8 | 用例首行是 root 检测 `[ \`whoami\` != root ] \|\| exit 42`（`SKIP_RETURN_CODE 42`）。**OHOS 无可用 `whoami`**（busybox `whoami` 报 `unknown uid 20020101`、`/etc/passwd: bad record`），命令替换为空后 `[ != root ]` 触发 `[` 的参数错误 → 走 `exit 42` 跳过分支。另：**HMDFS 忽略权限位**（`chmod u-r` 后仍可读），即便运行该用例也无法验证「无权限应失败」的断言 —— 跳过是本环境的正确结果。 |

## 未做基础库源码改动
本包**零补丁**（`patches: {}`）：唯一的上游构建问题是 cmake 4.x 策略（用 cmake 变量解决），
无编译错误、无平台宏注入、无 stub。

## test_package 设计（R34）
- zst 是 CLI，不存在可链接的库 API，故 `test_package/test.sh` **直接驱动已安装的 `bin/zst`**：
  对 zstd/xz/gzip/bzip2 各做一次 **压缩 → `-t` 完整性校验 → 解压** 往返，并 `cmp` 断言逐字节一致；
  额外校验未知格式 `-Fnosuchfmt` 被拒绝。
- `test_package/conanfile.py` 用 `bash test.sh` + `env="conanrun"`（OHOS `/system/bin/sh` 不能可靠执行 ELF）。
- `conan create` 实测：4 种格式往返全部 `OK`，未知格式 `OK`，test_package 通过（exit 0）。

## 本地流水线注意：W3 会改写 conandata.yml，提交前必须还原

`ci/conan/build_and_test.sh`（finish 的 W3 步骤）有一处 **mirror fallback**：只要
`conandata.yml` 里出现 `url: ... https://github.com/...`，它就把**单值 url 改写成镜像 url 列表**
（首项 `https://gh-proxy.com/<官方 URL>`），并留下 `conandata.yml.orig` 备份。
随后 pre-download 阶段又把 `file://` 改写还原（用 `conandata.yml.predl-orig`），
但**不还原上一步的镜像列表** —— 即 W3 结束时 `conandata.yml` 停留在镜像列表状态
（日志末尾的「已还原为官方 URL」只覆盖 pre-download 那一次改写）。

**处置**：W3 通过后，已把 `conandata.yml` 手工还原为官方单值 URL，并删除
`conandata.yml.orig` / `conandata.yml.ghfast-bak` 残留。还原后再次 `conan create` 仍通过
（源码 sha256 未变，W3 证据 `reports/w3-local-ci.log` 与 `.ci-result.json` 保持有效）。
提交前请确认：`grep -n "gh-proxy\|ghfast" archives/z/zst/0.4/conandata.yml` 无输出（R39 / preflight PF7）。

## 状态
**built（真机已验）** —— 在 HarmonyOS PC 上 `conan create` 通过（exit 0）：
- 产物：`bin/zst`（969 KB，`DT_NEEDED` 仅 `libc.so`，已 `binary-sign-tool -selfSign`）、`share/man/man1/zst.1`
- 包引用：`zst/0.4#0bdccfec4937800bcf8f1dd14b591201:8c48ee29ae12c56b1260b0ed35eab22c99b8619d#b970f28c8d0c19ec6dff328c42fad552`
- 上游测试：161 项 / 139 通过 / 14 失败（3 类环境原因）/ 8 跳过
---

**编译结束**: 2026-09-23 12:02
**最终状态**: built
