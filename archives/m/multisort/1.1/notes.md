# multisort 1.1 适配笔记

## 编译环境
- 构建系统: makefile（上游三行裸 Makefile：`CC = gcc`、`CFLAGS = -Wall -g -O2`，单条规则一步编译链接，无 configure、无 install 目标）
- 编译日期: 2026-09-23
- 编译器: OHOS SDK clang 15.0.4（`aarch64-unknown-linux-ohos`，经 `/data/service/hnp/bin/clang`），sysroot 为 OHOS musl
- 构建机: x86_64 runner 交叉编译；目标 aarch64-linux-ohos（profile `ci/conan/profiles/ohos-aarch64`，build_type=Release）
- 状态: built（conan-verify G0-G4 通过，W3 本地 conan create 通过）

## 编译步骤

1. 源码：作者官方下载页 `https://www.xach.com/multisort/multisort-1.1.tar.gz`，sha256
   `50cc0e84738f1c9b4b587e4d13564c233be20c693fd2154f2e8a293f3d5bc17d`（tarball 共 4 个文件：
   multisort.c / months.gperf / Makefile / README，日期均为 1999-10-28）。
2. 手工打通（临时目录）：`make CC=/data/service/hnp/bin/clang CFLAGS="-O3 -Wall"` 直接成功；
   `CFLAGS="-O0 -g"` 链接失败（见问题 3）。
3. 配方 `build()`：`apply_conandata_patches` 后，由 `AutotoolsToolchain(self).vars()` 取 `CC`、
   `CPPFLAGS`、`CFLAGS`、`LDFLAGS`，以 make 命令行变量覆盖上游写死的 `CC = gcc`（R33，不读裸 shell 变量）：
   `make -j1 CC=/data/service/hnp/bin/clang CFLAGS='-DNDEBUG -O3 -Wall'`
   （上游规则 `$(CC) $(CFLAGS) -o multisort multisort.c` 没有单独的链接步骤，LDFLAGS 随 CFLAGS 传入；
   `-Wall` 沿用上游 Makefile，`-g -O2` 由 build_type 标志取代）。
4. `package()`：上游无 install 目标，把 `multisort` 复制到 `bin/`；tarball 无 COPYING，
   把 multisort.c 头部的 GPL 许可声明写入 `licenses/LICENSE`。
5. `months.gperf` 的 gperf 输出已内嵌在 multisort.c 中，构建不需要 gperf。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 Makefile 写死 `CC = gcc` | 交叉构建必须用 OHOS clang | make 命令行变量覆盖（命令行赋值优先于 Makefile 赋值），值取自 AutotoolsToolchain（R33），不改 Makefile |
| 2 | 1024 字节以上的日志行在 OHOS 上输出被截断/与下一行粘连（编译零告警，仅运行时出现） | 程序用 `char buf[BUFSIZ + 1]` + `fgets(buf, BUFSIZ, fp)` 读"整行"；OHOS musl 的 `BUFSIZ` 为 1024（sysroot `stdio.h:50`），glibc 为 8192。长行被切段，续段若含 `[`（如 UA 中的 `[FBAN/...]`），`conv_time()` 先写入若干 `\0` 再因月份查不到提前返回、不还原，`fputs` 截断输出 | 补丁引入 `LINEBUF_SIZE 8192`，缓冲与两处 `fgets` 统一改用它，行为与 glibc 版一致、不依赖 libc 常量，无平台宏。实测 1312 字节行：x86 glibc 原样输出，OHOS 静态重链版（未打补丁）只剩 1 行 1359 字节（输入 2 行共 1380 字节）；打补丁后逐字节一致。已沉淀知识草稿 E6401 |
| 3 | `-O0`/Debug 构建链接失败：`ld.lld: error: undefined symbol: in_word_set`，同时 `-Wstatic-local-in-inline` 告警 | gperf 2.7 生成的 `in_word_set()` 是非 static 的 `__inline`（sysroot `features.h` 把 `__inline` 定义为 `inline`）；clang 默认 gnu17 采用 C99 inline 语义，这种"inline definition"不产生外部符号。Release（-O3）因被内联而侥幸通过 | 补丁给 `in_word_set()` 加 `static`（内部链接，告警同时消失）；`-O0` 与 `-O3` 均复验通过。根因已被草稿 E321-draft-9758（C99 inline 缺外部定义）覆盖，不另立条目 |
| 4 | 2019 年以后的日志合并完全失序，并对已关闭的 FILE 再次 `fgets`（x86 glibc 版 2026 年日期样例直接 SIGSEGV，退出码 139；OHOS 版输出 `/a /c /e /e`） | **上游缺陷，非平台相关**：`conv_time()` 返回 `(年-1990)*31104000 + 月*2592000 + ...`，而每轮最小值哨兵写死 `900000000`，自 2018-12-06 16:00:00 起所有时间戳都不小于哨兵，`min_index` 恒为 0，文件 0 读完后仍被选中 | 按维护者决策随补丁修复：哨兵改为 `LONG_MAX`（+`#include <limits.h>`），两行改动；1999 年日期行为不变 |
| 5 | 上游无 install 目标 | Makefile 只有 `multisort` 一个目标 | `package()` 直接 copy 到 `bin/` |
| 6 | x86 runner 无法运行交付的动态产物 | 构建机没有 OHOS 的 `/lib/ld-musl-aarch64.so.1`，binfmt qemu 启动即报 `Could not open '/lib/ld-musl-aarch64.so.1'`（知识库暂无对应条目） | 功能验证改用同源、同标志的 `.o` 静态重链副本经 qemu 实跑；test_package 在异架构主机上把功能层如实记为 SKIPPED |
| 7 | `init-build` 把构建系统判成 `autotools`、`conan-init` 生成了 autotools 配方与 CMake 空壳 test_package | 工具侧判定问题（已写入 SKILL_FEEDBACK） | 按实际的裸 Makefile 手写配方，test_package 改为 Python 功能测试 |
| 8 | 首轮 W3：`FileNotFoundError: ... .build-cache/predl_cache/9b840294_source_9b840294multisort-1.1.tar.gz`（conan-verify 的 G2 却通过） | `conandata.yml` 注释里写了下载页 URL `https://www.xach.com/multisort/`；W3/CI 的预下载正则抓取文件中所有 http(s) URL，把该下载页当源码包下载，再用 `str.replace` 改写，连带把真实 URL 的同名前缀改成了 `file://` 路径（已有草稿 DRAFT-8543 覆盖；engine 误匹配 E333） | 注释中不写 http(s) URL；W3 复跑通过 |

## 源码修改

`patches/0001-multisort.c.patch`（`refresh-patch --auto` 生成，+10/-5，`patch --dry-run -p1` 干净；
无任何平台宏）：

1. `#include <limits.h>`；新增 `#define LINEBUF_SIZE 8192`，`struct _input_file` 的 `buf` 与两处
   `fgets()` 改用它（问题 2，平台相关）。
2. `in_word_set()` 前加 `static`（问题 3，编译器 inline 语义相关）。
3. `min_time = 900000000L;` → `min_time = LONG_MAX;`（问题 4，上游缺陷修复，非平台相关）。

## 依赖版本

- 无 Conan 依赖（仅 libc）；W0 核验：配方 `requirements()` 为空，无需探测制品仓。
- 工具链：OHOS SDK clang 15.0.4、ld.lld、musl sysroot（`BUFSIZ 1024`）。

## 上游测试清点（R51）

- 清点：tarball 共 4 个文件；无 `tests/` 目录（0 个）、无测试脚本、无 ctest/pytest 注册（0 个）；
  Makefile 只有 `multisort` 一个目标，`make -n check` / `make -n test` 均报
  `No rule to make target`。**上游测试用例数 N = 0**，可运行数 N′ = 0，通过率不适用。
- 补全：test_package 的 `test_multisort.py` 共 10 项检查——A1-A3 产物检查（ELF64 AArch64 /
  PIE / `PT_INTERP=/lib/ld-musl-aarch64.so.1`，所有主机）+ F1-F7 功能检查（单参数 usage；
  1999 与 2026 年两文件合并；三文件覆盖 12 个月份 + 跨年；3015 字节长行（1999 年日期）；缺失文件；
  空文件；退出码 + stdout 逐字节比对 + stderr 关键文本，30 s 超时）。aarch64 CI worker 上功能层必跑。

## 验证结果

```bash
# conan-verify（G0-G4 PASS）/ W3 conan create，test_package 输出（x86_64 runner）：
[ok] A1 ELF64 little-endian EM_AARCH64 image
[ok] A2 position-independent executable (ET_DYN)
[ok] A3 PT_INTERP is /lib/ld-musl-aarch64.so.1
[skip] F1-F7 not run: this x86_64 host cannot execute the aarch64 OHOS image
RESULT: artifact checks 3/3 passed, functional checks 0/7 run (SKIPPED)

# 功能验证：Conan 构建目录中已打补丁的 multisort.c，按 conan create 相同标志
# clang -DNDEBUG -O3 -Wall -c 后 -static 重链，qemu-aarch64 实跑 test_multisort.py：
F1-F7 7/7 passed（A2/A3 对静态副本不适用，记 fail 属预期，不代表交付产物）

# 补丁消融对照（同法静态重链，qemu-aarch64 实跑 F1-F7）：
#   未打补丁        F3 F4 F5 失败（4/7）
#   仅行缓冲修复    F3 F4    失败（5/7）
#   仅哨兵修复            F5 失败（6/7）
#   完整补丁        全部通过（7/7）
# 即 F3/F4 只依赖哨兵修复，F5 只依赖行缓冲修复（F5 用 1999 年日期，不受哨兵缺陷干扰）
```

**说明**：x86 runner 上交付的动态产物本身未实跑（缺 OHOS loader），上面的结果来自同源同标志的
静态重链副本，不等于交付产物已实跑；交付产物的功能层由 aarch64 CI worker 上的 test_package 强制执行。
`in_word_set()` 的 `static` 修复由 `-O0` 编译链接通过来验证（未打补丁时 `-O0` 链接失败）。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/multisort` | ELF64 aarch64 PIE，动态链接 OHOS musl（本地 W3 构建约 19 KB） |
| `licenses/LICENSE` | multisort.c 头部的 GPL-2.0-or-later 许可声明 |

## 注意事项

- 上游时间模型是近似值：月份按 30 天计、忽略时区，因此 1 月 31 日与 2 月 1 日比较相等，
  跨时区日志按本地时间字面值排序——属上游设计，未改动；测试数据的日期避开 31 日。
- 行缓冲固定 8192 字节后，超过 8191 字节的行仍会被切段（与 glibc 版上游行为一致）。
- 首个 `[` 之后不是 `dd/Mon/` 形式的行（非 CLF 行），`conv_time()` 会写入 `\0` 后提前返回、
  输出被截断——上游既有行为，与平台无关，未改动。
---

**编译结束**: 2026-09-23 19:10
**最终状态**: built
