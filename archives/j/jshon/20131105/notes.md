# jshon 20131105 适配笔记

## 概述

- 软件: jshon — 命令行 JSON 解析/编辑工具（栈式过滤器管道）
- 上游: https://github.com/keenerd/jshon（官方仓库，作者 Kyle Keen / keenerd）
- 版本: 20131105（上游最后一个正式 tag，2013-11-05；master 止于 2014-08，无后续 release）
- 许可: MIT（LICENSE，(c) 2011-2013 Kyle Keen）
- 构建系统: 纯 GNU Makefile（无 configure；编译/链接全靠 make 内建规则）
- 依赖: jansson（唯一第三方依赖）
- 产物: 单个可执行文件 `jshon`（bin/）+ man 手册 `jshon.1`（share/man/man1/）
- 目标平台: OpenHarmony / HarmonyOS PC（aarch64-linux-ohos，musl）

## 时间/状态

- 适配日期: 2026-10-12
- 状态: **pending**（本地验证完成，CI 待跑）— 本机即 OHOS aarch64 真机：
  conan create 构建通过 + test_package 31/31 断言通过；CI L1-L4 冒烟待推送后执行
- 分支: `feat/jshon-20131105`

## W0 依赖结论

```text
依赖数量：1（jansson）
已满足依赖：jansson — 制品仓已发布 2.14 / 2.15.0 / 2.15.1 / 2.15.1.1
缺失依赖：无
是否需要拆分依赖适配：否（复用 archives/j/jansson/2.15.1.1，不 vendoring）
阻塞点：无
下一步：本机前置验证 → 本地 conan create
```

选择 `jansson/2.15.1.1`：制品仓最新版（2.15.1 + 修正），SONAME 为无版本后缀的
`libjansson.so`（适配 OHOS 封闭系统目录布局）。本机 conan 缓存中的 2.15.1 完整包
（janssb633ffa0f5f63）已实测具备同样正确的 SONAME——探针二进制 NEEDED
`libjansson.so` + `libc.so`，原生运行正常。

## 源码归档选择

- URL: `https://github.com/keenerd/jshon/archive/refs/tags/20131105.tar.gz`
- SHA256: `28420f6f02c6b762732898692cc0b0795cfe1a59fbfb24e67b80f332cf6d4fa2`
- 上游 tag 归档，共 6 个文件（LICENSE / Makefile / PKGBUILD / jshon.1 / jshon.c /
  jshon.spec），单目录 `jshon-20131105/`（`strip_root=True`）。
- URL 以 `.tar.gz` 结尾 → Conan 选 gzip 解压器（规避无扩展名 codeload URL 的
  `BadZipFile` 误选，见知识条目 E392；rotix 先例同法）。
- SHA256 三方交叉核验：本机下载计算 + Homebrew formula（jshon.rb resource
  sha256）+ FreeBSD distinfo（jshon-20131105）一致。

## W1 源码与构建系统分析

### 语言与 API

- 纯 C，单文件 jshon.c（1070 行），`#define _GNU_SOURCE` 在第 1 行。
- 标准 C 库: ctype/stdio/string/stdlib/errno + sys/param/sys/stat/unistd。
  GNU 扩展: asprintf、strdup（musl 均可用）。`uint`（BSD 遗留类型）用于
  mapping 结构数组迭代器（207 行）——**未包含 sys/types.h**，是 OHOS 编译
  失败的根源（见下）。
- jansson API: json_loadf/json_loads（JSON_PRESERVE_ORDER｜JSON_DECODE_ANY，
  宏在 jansson 2.14/2.15 头文件仍有效；2.14 起对象默认按插入序）、
  json_dumps（JSON_INDENT(1)｜JSON_COMPACT｜JSON_ENCODE_ANY）、
  json_object_* / json_array_* / json_string_* / json_copy 等。
- getopt: `getopt_long` 注册了 `--version`（原生可用）；`--help` 未注册 →
  落入默认分支 usage() 且 rc=2（见“L2 冒烟说明”）。
- 版本机制: Makefile dist 目标用 sed 把 JSHONVER 宏写进 jshon.c；tag 归档
  已带 `#define JSHONVER "20131105"`，无需处理。

### 构建系统（Makefile）

- 变量: `LDLIBS = -ljansson`；`CFLAGS := -std=c99 -Wall -pedantic -Wextra
  -Werror ${CFLAGS}`（关键机制：命令行/环境 CFLAGS 会被**追加在 upstream
  flags 之后**，因此 -Wno 抑制可后置生效）。
- 无任何显式编译/链接规则，全部依赖 make 内建规则（`%.o: %.c` 与 `%: %.o`）：
  - CC 必须在 make 命令行钉住（conf 的 tools.build:compiler_executables）；
  - CPPFLAGS/LDFLAGS Makefile 未定义，经环境注入即进内建规则；
  - CFLAGS **必须走环境变量**——走 make 命令行会整体覆盖 upstream flags
    （`CFLAGS :=` 对命令行赋值同样生效），破坏“flags 全保留”要求。
- 其它目标: install（宿主 `install -D`，不采用，package() 用 conan copy）、
  strip、dist、clean；`VERSION := $(shell git show ...)` 仅供 dist 使用，
  构建目录非 git 仓库时仅 stderr 噪音（"fatal: not a git repository"），
  不影响构建。

### upstream tests 精确清点（R51）

**上游可运行测试数 = 0**。证据：

1. 归档 6 文件中无 tests/t/test* 目录或文件；
2. Makefile 目标全集 = all/strip/clean/install/dist，无 test/check；
3. PKGBUILD 无 check() 函数（Arch 官方打包也从不跑测试）；
4. jshon.spec 无 %check 段；
5. 上游 git master（2014-08 最后提交）同样没有测试目录；
6. 旁证: Alpine aports 的 jshon 20131105-r2 APKBUILD 亦无 test/check 钩子。

### OHOS 编译问题定论（全部实证）

| # | 问题 | 根因 | 修复 |
|---|------|------|------|
| 1 | `unknown type name 'uint'`（207 行）+ `sign-compare`（260 行） | OHOS musl 的 sys/stat.h 改用 bits/alltypes.h，不再传递包含 sys/types.h；uint 的 typedef 守卫在 sys/types.h 的 `_GNU_SOURCE/_BSD_SOURCE` 分支内，包含链到达不了。uint 回退 int 后与 size_t 比较符号不一致 → 连带 sign-compare | 补丁 0001：在 `_GNU_SOURCE`（第 1 行）之后补 `#include <sys/types.h>` |
| 2 | `unused-command-line-argument`（-Wl,--code-sign） | OHOS clang 包装器经 .cfg 对每次调用注入 `-Wl,--code-sign`（链接器自签），编译阶段该参数未使用，被 upstream -Werror 升级为致命 | env CFLAGS 追加 `-Wno-unused-command-line-argument`（先例 aesfix/asterisk） |
| 3 | `strict-prototypes` ×6（182/215/222/244/269/833 行） | 上游 6 处 K&R 空参数列表 `()`，clang 15 严格告警 + -Werror | env CFLAGS 追加 `-Wno-strict-prototypes`（先例 asmotor） |

错误收敛矩阵（upstream flags `-std=c99 -Wall -pedantic -Wextra -Werror` +
conan jansson 头文件，本机实测）：

```text
不加补丁、不加任何 -Wno 抑制：9 errors（6×strict-prototypes + uint
  + sign-compare + wrapper --code-sign 的 unused-command-line-argument）
仅加 2 个 -Wno 抑制：          2 errors（uint + sign-compare → 补丁职责）
加补丁 + 2 个 -Wno 抑制：      0 errors，RC=0
补丁但放文件首行（Alpine 位置）：2 errors（uint + sign-compare 依旧）——
  -std=c99 的 __STRICT_ANSI__ 下 _BSD_SOURCE 不生效，证明插入位置必须在
  _GNU_SOURCE 之后
```

修复策略遵循 #8 要求：**upstream flags 全保留**（-std=c99 -Wall -pedantic
-Wextra -Werror 一个不少），仅经 Makefile 自带的 `${CFLAGS}` 尾部追加两个
`-Wno` 抑制（比 Alpine 的 disable-werror.patch 更干净——不削弱任何告警类别，
只定点豁免两处 OHOS 环境性问题）；源码补丁仅 1 行 include（portability）。

### Alpine aports 先例

jshon 20131105-r2 打两个补丁：disable-werror.patch（我们用 -Wno 后置抑制
替代，保留 -Werror 语义）+ missing-typesh.patch（加 sys/types.h 包含，与我们
的 0001 同根因同修法；其插入位置在文件首行，OHOS 上实证无效）。

## W2 配方设计

- `package_type = "application"`，settings 四项，无 options（单二进制工具，
  无可选特性）。
- `requirements`: `jansson/2.15.1.1`（复用制品仓，不 vendoring）。
- `layout`: basic_layout；`source()`: conandata get + strip_root。
- `build()`: apply_conandata_patches → CC 取 conf（R33，不碰宿主环境变量）→
  jansson include/lib 目录取自 `self.dependencies["jansson"]
  .cpp_info.aggregated_components()`（仓库惯用写法，cf. cmatrix/ncurses）→
  Environment 注入 CFLAGS（两个 -Wno）/CPPFLAGS(-I)/LDFLAGS(-L) →
  `make CC=... -j1 jshon`。
- `package()`: copy LICENSE→licenses/、jshon→bin/、jshon.1→share/man/man1/，
  chmod 0755（上游 install 同权限）；不用上游 install 目标（宿主专用路径）。
- `package_info()`: `cpp_info.bindirs = ["bin"]`（消费者经 PATH 取得 jshon）。
- `_index.yaml` 为脚本自动生成（勿手改），与 rotix 一致不在本次提交中手改。

## W3 test_package

- `test_package/conanfile.py`: `VirtualRunEnv` 生成器（PATH + LD_LIBRARY_PATH
  覆盖 bin/ 与 jansson lib/）+ `test_type = "explicit"` + `CONFIG_SHELL`
  bash 执行 `test.sh`（OHOS 上 /system/bin/mksh 无法执行 ELF，须 bash 包裹；
  rotix 同法）。
- `test_package/test.sh`: **31 项断言**（24 功能 + 7 ELF），每个期望值都经
  真实二进制经验核验（见 W4），不只看 exit code，逐项比对输出内容：
  - object key 读取：类型（-t）、嵌套提取去引号（-e b -e c -u）、长度（-l）、
    插入序 keys（-k，验证 jansson 2.14+ 有序对象）；
  - array 读取：下标（-e 1 -u）、长度（-l）、迭代（-a -u）；
  - string/number/bool/null：类型与值全配对（string 型/值/转义还原 a"b、
    number 42、bool true、null）；
  - 创建/修改（CLI 完整支持）：-s/-i 创建、-n/-i 非字符串字面量、-s/-i
    覆盖、-d 删除、空数组下标 0 插入；断言含 1 空格缩进的多行精确输出；
  - invalid JSON（`{bad`）→ 非零；顶层标量（`"hi"`，jshon 只接受顶层
    object/array）→ 非零；空输入 → 非零；
  - `--version` → 精确输出 `20131105`；
  - ELF 专项（要求 #6）：ELF64 / AArch64 / ET_DYN(PIE) / PT_INTERP
    `/lib/ld-musl-aarch64.so.1`（musl）/ 动态段无 RPATH/RUNPATH（无宿主
    路径泄漏）/ NEEDED libjansson.so（确认动态链接制品仓 jansson）。
- `test_package/MANIFEST.yml`: upstream_tests = []（上游无测试的声明与证据）。

## W4 本机前置验证（探针矩阵）

本机即 OHOS 设备（aarch64-linux-ohos；clang 15.0.4 包装器 + musl sysroot；
GNU Make 4.4.1；toybox patch 0.8.12 支持 -p1）。验证记录：

| 检查 | 结果 |
|------|------|
| tarball SHA256 复核 | 通过（28420f6f…，与两方记录一致） |
| 补丁 dry-run / 应用（toybox patch -p1） | 通过 |
| OHOS 编译（补丁 + 2 抑制 + upstream flags 全保留） | 通过（RC=0） |
| 未修复复现（错误收敛矩阵） | 通过（9 → 2 → 0，三类根因实证） |
| 链接（-L conan jansson lib -ljansson） | 通过 |
| ELF 检查（readelf） | ELF64 / AArch64 / DYN(PIE) / INTERP /lib/ld-musl-aarch64.so.1 / NEEDED libjansson.so + libc.so / 无 RPATH、RUNPATH |
| 原生运行 24 项行为 | 全部符合预期（探针矩阵矩阵值即 test.sh 期望值来源） |
| make 真实路径冒烟（env CFLAGS/CPPFLAGS/LDFLAGS + make CC=clang -j1 jshon，与 recipe build() 同款） | 通过（makerc=0，产物 43520 字节，运行/版本正常） |
| 本地 conan create（.tmp-audit/profile-ohos-local，--build=missing） | 通过（jansson/2.15.1.1 命中本地缓存；源码下载/补丁/build/package 全绿；包 93c3958…built，打包 LICENSE/jshon/jshon.1） |
| conan test test_package（CONFIG_SHELL=本机 bash） | 通过（**31/31 断言 PASS**：24 功能 + 7 ELF 专项，RC=0） |

探针运行要点（对应 test.sh 断言值）：

```console
$ echo '{"b":{"c":"str"}}' | ./jshon -e b -e c -u      # str
$ echo '{"b":2,"a":1}' | ./jshon -k                    # b↵a（插入序）
$ echo '{}' | ./jshon -s hello -i greeting             # {↵ "greeting": "hello"↵}
$ echo '{bad' | ./jshon -t; echo $?                    # json read error… rc=1
$ ./jshon --version                                    # 20131105
```

jshon 20131105 行为备注（影响断言设计，均已实测）：无 `-c` 紧凑输出选项
（上游后期提交才加入），默认输出 1 空格缩进多行 JSON；顶层输入只接受
object/array，顶层标量是解析错误。

## L2 冒烟说明（--version / --help 与 E503）

- `--version`: **原生支持**（getopt_long 已注册），输出 `20131105`，rc=0 ——
  E503 判例（CLI 无长选项致 L2 失败）对 jshon 不适用于 --version。
- `--help`: 未注册，落入默认分支打印 usage 到 stderr，rc=2。若 CI L2 冒烟
  固定执行 --help 会 miss；参照 rotix r1 判例（L2=skip，non-blocking，
  总 exit=0），不为此打长选项拦截补丁（E503 的推荐方案）——jshon --version
  已原生可用，不为 --help 单独扩大补丁面、增加上游行为分叉。test.sh 只断言
  --version。

## 遗留与阻塞点

- **CI L1-L4 冒烟待推送后执行**：--version 原生通过；--help 未注册，预期
  L2=skip（non-blocking，rotix r1 判例，见上文"L2 冒烟说明"）。
- 本地复跑注意事项：仓库 profile（ci/conan/profiles）硬编码
  `/data/service/hnp/bin/clang` 与 `CONFIG_SHELL=/data/service/hnp/bin/bash`
  （本机均不存在）。本地用 `.tmp-audit/profile-ohos-local`（指向本机 clang，
  settings 与仓库 profile 完全一致，保证与 CI 构建的 jansson 二进制
  package_id 匹配），test 阶段导出
  `CONFIG_SHELL=/storage/Users/currentUser/usr/local/bin/bash`（recipe 回退
  默认路径按 CI 设备写死，与 rotix 先例一致，不改动）。
- 共享构建机磁盘间歇性满（"No space left on device"，时好时坏），若 conan
  create 失败先查磁盘。
- `_index.yaml` 为自动生成文件，本次不手动编辑（rotix 亦未入册，随工具链
  再生成）。

## 下一步

- [x] 本地 conan create（修正 profile 副本，--build=missing）— 构建通过
- [x] conan test test_package — 31/31 断言通过
- [ ] 推送后 CI L1-L4 冒烟（预期 L2=skip non-blocking，其余 pass）
- [ ] CI 全绿后把版本级/软件级 manifest status: pending → built

本地验证实际执行的命令（可复现）：

```bash
conan create archives/j/jshon/20131105 \
  -pr:h=.tmp-audit/profile-ohos-local -pr:b=.tmp-audit/profile-ohos-local \
  --build=missing
# 本机无 /data/service/hnp/bin/bash，test 阶段需导出 CONFIG_SHELL 后单跑：
CONFIG_SHELL=/storage/Users/currentUser/usr/local/bin/bash conan test \
  archives/j/jshon/20131105/test_package jshon/20131105 \
  -pr:h=.tmp-audit/profile-ohos-local -pr:b=.tmp-audit/profile-ohos-local
```

## 交付物

```text
archives/j/jshon/
├── README.md                       # 软件说明 + 用法 + 适配状态
├── manifest.yaml                   # 软件级 manifest
├── commands.json                   # CLI 工具声明（type: tool, binary: false）
└── 20131105/
    ├── conanfile.py                # Conan 2 配方（make + jansson/2.15.1.1）
    ├── conandata.yml               # 源 URL/SHA256 + 补丁登记
    ├── manifest.yaml               # 版本级 manifest（pending）
    ├── notes.md                    # 本文件
    ├── patches/
    │   └── 0001-include-sys-types.patch
    └── test_package/
        ├── conanfile.py            # VirtualRunEnv + bash test.sh
        ├── test.sh                 # 31 项断言（24 功能 + 7 ELF）
        └── MANIFEST.yml            # upstream_tests: []（上游无测试）
```

## issue 说明

任务下发未附带 issue 编号；本仓 git 历史与知识库（7484 文件）中均无 jshon
既有条目或相关提交（`git log --all -i --grep=jshon` 无 jshon 专项记录）。
issue 编号待补。
