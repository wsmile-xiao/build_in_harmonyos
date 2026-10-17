# lakai 0.1 — 适配笔记

> 档案创建时间: 2026-09-14
> 状态: built（本地 conan create 通过；未 upload）
> 设备/工具链: HarmonyOS PC (aarch64, os.version 6.0) + clang 15 + GNU Make 4.4.1

## 一、上游测试清点（R51 三步法 · 第一步）

清点命令（在解压后的上游源码树内执行，实测输出见下）：

```sh
grep -nE '^(check|test|regress)[^:]*:' Makefile   # 无任何输出
make -n check                                     # make: *** No rule to make target 'check'.  Stop.
ls -d tests test 2>/dev/null                      # 两个目录都不存在
find . -type f \( -name '*.c' -o -name '*.h' \) | sort
```

实测结论：

| 项 | 结果 |
|----|------|
| Makefile 目标 | 仅 `all / progs / lakclear / lakbak / lakres / $(LIB) / lakai.o / install / uninstall / clean` —— **无 check / test / regress** |
| `make -n check` | `make: *** No rule to make target 'check'.  Stop.` |
| tests/ 目录 | **不存在** |
| 源文件 | 仅 5 个：`lakai.c`、`lakai.h`、`lakbak.c`、`lakres.c`、`lakclear.c` |
| **上游测试用例数** | **0** |

因此 `upstream_official_tests: []`，`upstream_tests: []`。用户要求：上游无测试的，
适配后自行补全 → 见第三节。

## 二、构建系统与产物

- 构建系统：**纯 GNU Makefile**（无 configure/autotools/cmake）。
- 编译命令（配方 build() 内，实测）：

  ```
  make -j1 CC=/data/service/hnp/bin/clang AR=ar RANLIB=ranlib
  ```

  产出：`liblakai.a`（静态库）、`lakai.o`，以及三个 CLI `lakbak`、`lakres`、`lakclear`。
- 编译器按 R33 从 Conan conf（`tools.build:compiler_executables`）读取绝对路径后
  显式传给 make，不依赖 shell 中的 `CC`（CI worker 上该变量为空）。
- 上游 Makefile 用裸 `ar rcu` / `ranlib`（未引用 `$(AR)`/`$(RANLIB)`），依赖构建机
  PATH 上有这两个命令（本机与 CI 均在）。
- 上游 `install` 目标调用 `install(1)` —— OHOS 无该命令，**不调用**；配方改用
  conan `copy()` 在 `package()` 阶段收集 `bin/`、`lib/`、`include/`、`licenses/`。
- 源码编译告警：8 处 `-Wpointer-sign` / `-Wstrict-prototypes`（2004 年代码风格），
  0 error，不影响功能；未改动上游源码。

## 三、自研补全测试（层 1）

上游无测试，故本归档自研测试套件 `0.1/tests/test_lakai.c`，并用
`patches/0001-add-make-check-target.patch` **仅新增**一个 `check` 目标
（不修改任何上游构建规则、不涉平台宏），由 `build()` 内 `make check` 真实执行，
同时满足 TEST_QUALITY_SPEC 层 1 与 CI 门禁 L1c 的 `make check` 痕迹要求。

执行方式（实测日志原文）：

```
lakai/0.1: RUN: make check CC=/data/service/hnp/bin/clang AR=ar RANLIB=ranlib
/data/service/hnp/bin/clang -g -Wall -Wstrict-prototypes  -I. tests/test_lakai.c -L. -llakai -o test_lakai
./test_lakai .
```

覆盖点与断言数（实测统计）：

| 覆盖点 | 断言数 |
|--------|-------:|
| `lakai_asciitoakai` 映射边界（0-9/A-Z/a-z/#/+/-/. + 5 个不可转换字符） | 18 |
| `lakai_akaitoascii` 反向映射边界（含 10/41/255 空洞码） | 13 |
| ASCII->Akai->ASCII 往返一致性（40 个可往返字符逐字符） | 40 |
| 小写 a-z 折叠为大写 A-Z（记录上游行为） | 1 |
| `len` 语义（len=0 不改写、部分长度只转前 len 字节） | 4 |
| `lakai_init/open/close` 契约（可离线部分） | 5 |
| 已发布头文件常量契约（S2000_*、LAKAI_MODE_*） | 7 |
| 三个 CLI 可执行性（usage + 不存在设备错误码 5，各 4 条） | 12 |
| **合计** | **100** |

实测结果（conan create 日志逐字摘录）：

```
assertions=100 failures=0
```

程序退出码 **0**（任一条失败即非零退出，供 CI 从日志取证）；日志中 `FAIL:` 计数为 **0**。

补充说明：`lakai.h` 中 `LAKAI_DEVTYPE_*` 宏与 `lakai_identifydevice` 等函数声明位于
`#if 0 ... #endif` 块内（**未启用**），自研测试不引用这些符号。

## 四、test_package（层 2，消费者视角）

- `test_package/test_lakai_package.c`：`#include <lakai.h>` + 链接 packaged
  `liblakai.a`，调用字符映射与句柄契约 API —— 实测 **10 断言全过**
  （`assertions=10 failures=0`，退出码 0）。
- `test_package/conanfile.py` 的 `test()`：先用 Conan conf 中的 clang 编译该 C 文件
  （`-I<pkg>/include -L<pkg>/lib -llakai`）并运行，再 smoke 运行 packaged
  `bin/lakclear`（无参数断言输出 `Usage:`；不存在设备断言输出 `Open failed`）。
- 三段验证都真实依赖包产物（include / lib / bin），移动产物后必失败
  （CI 门禁 L1e 破坏性反向验证可确认非空壳测试）。

## 五、踩坑记录

1. **`package_type` 与选项约束**：初版写 `package_type = "library"`，conan 报
   `Package type is 'library', but no 'shared' option declared`。上游只产出静态库，
   故改为 `package_type = "static-library"`（无需声明 `shared` 选项）。
2. **不调用上游 make install**：OHOS 无 `install(1)`，`make install` 必失败；
   配方改为 `package()` 内 conan `copy()` 收集，无需改上游 Makefile。
3. **上游 ar/ranlib 为裸命令**：Makefile 里是 `ar rcu`/`ranlib`，不接受 `$(AR)` 覆盖；
   依赖 PATH 上有 ar/ranlib（本机与 CI 均有）。
4. **字符映射有损**：小写 a-z 与 A-Z 共用同一 Akai 码，往返后折叠为大写；
   不可转换字符在 `asciitoakai` 方向回退为 `'+'`（38），而 `akaitoascii` 的
   空洞码（10/41/255…）映射为空格。自研测试据此设定期望值。
5. **LAKAI_DEVTYPE_* 不可用**：位于 `#if 0` 块，初版测试误用导致编译失败，已移除。
6. **无采样器环境**：`lakai_open()` 对不存在设备按契约返回负值（不崩溃），
   三个 CLI 对不存在设备打印 `Open failed.` 并返回退出码 5 —— 均可离线验证，
   因此层 1/层 2 测试不依赖真实 SCSI 硬件。
7. **test_package 构建产物隔离**：test_package 默认 `build_folder == source_folder`，
   会把编译出的 `test_lakai_package` 二进制留在归档目录里。已按仓库既有惯例
   （如 `archives/j/julius/1.8.0/test_package`）在 test_package 中加
   `basic_layout(self)`，构建输出落到 `test_package/build-release/`
   （该路径已被仓库 `.gitignore` 覆盖），归档树内不再残留二进制。
8. **许可证口径**：Debian 版权文件（`lakai_0.1-2/copyright`）标注 `License: GPL-2`，
   即仅第 2 版、无 “or later” 条款，故统一采用 SPDX `GPL-2.0-only`
   （conanfile.py / 软件级 manifest.yaml / README.md 三处一致）。

## 六、验证命令与结果

```sh
cd "<repo>"
conan create "archives/l/lakai/0.1" \
  -pr:h="ci/conan/profiles/ohos-aarch64" -pr:b="ci/conan/profiles/ohos-aarch64" \
  --build=lakai/*
```

- 退出码：**0**
- 日志关键行：`Launching test_package` / `Running test()` / `assertions=100 failures=0` /
  `assertions=10 failures=0` / `lakai test_package: C API + CLI checks passed`

## 七、结束记录

- 最终状态: built（本地 conan create 通过；未 upload 到制品仓）
- 包路径（本机实测）: `/storage/Users/currentUser/.conan2/p/b/lakai3411765dce534/p`
  （bin/ 三个 CLI、lib/liblakai.a、include/lakai.h、licenses/COPYING）
- 结束时间: 2026-09-14
