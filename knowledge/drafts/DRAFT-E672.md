# KMC 3.2.4 在 HarmonyOS 上的适配三连：libc++ 头收敛 / 捆绑 zlib 预构建 / 老 pybind11 的 NOT_RUN 判据（草稿，预留条目 E672）

- **软件**：kmc 3.2.4（https://github.com/refresh-bio/KMC）
- **构建系统**：上游顶层裸 `Makefile`（无 configure；`uname -m` 分派 X64/ARM64，aarch64 自动选 `raduls_neon.o`）
- **平台**：HarmonyOS PC / aarch64，`clang 15.0.4`（`/data/service/hnp/bin/clang`，target `aarch64-unknown-linux-ohos`），libc++
- **状态**：DRAFT（预留编号 E672）

## 现象

首次 `make CC=clang++ kmc kmc_tools kmc_dump -j1` 失败于：

```
kmc_core/defs.h:112:10: fatal error: 'ext/algorithm' file not found
#include <ext/algorithm>
```

修掉后，捆绑 zlib（`.gitmodules` → `refresh-bio/dependencies-zlib` @ `3cccc9613d79…318a`
的 `3rd_party/cloudflare` 子模块）单独构建时：

```
Checking for gcc...
Compiler error reporting is too harsh for ./configure (perhaps remove -Werror).
** ./configure aborting.
make: *** No rule to make target 'libz.a'.  Stop.
```

配方侧两次 conan create 报错：

```
ERROR: kmc/3.2.4: Package type is 'library', but no 'shared' option declared
ERROR: kmc/3.2.4: ... 'tools.build:compiler_executables:c' does not exist in configuration list
```

`make py_kmc_api`（上游 Python 绑定目标）报 9 连错：

```
py_kmc_api/libs/pybind11/include/pybind11/cast.h:442:36: error: member access into incomplete type 'PyFrameObject' (aka '_frame')
```

## 根因

1. **`<ext/algorithm>` 是 libstdc++ GNU 扩展头**：OHOS NDK 全线 libc++，无此头。代码用
   `using __gnu_cxx::copy_n;`，而 `copy_n` 自 C++98 起就在 `<algorithm>`/`std` 里；
   全仓 grep `copy_n` **0 个调用点**（纯死引用）。两文件三行 std 化即解，无行为级改动。
2. **上游 Makefile 的 zlib 规则探测裸 `gcc`**：`$(LIB_ZLIB):` 规则是**无依赖规则**
   （`cd 3rd_party/cloudflare; ./configure; make libz.a`）。zlib configure 默认 `CC=gcc`，
   设备/CI 无 gcc 即 abort；`make CC=clang++` 只影响顶层 make，configure 是独立 shell
   进程不吃 make 变量。**无依赖规则的妙处**：目标文件已存在时 make 直接跳过——
   配方层用 profile 的 clang 预构建 `libz.a`，上游 Makefile 一字不改。
3. **conan 模板与现场实现不符**：本机 conan 2.29 中
   `tools.build:compiler_executables` 是整个 JSON dict（profile `[conf]` 段写成
   `{"c": "...", "cpp": "..."}`），`self.conf.get("tools.build:compiler_executables:c")`
   深取直接抛异常；须先取 dict 再按键。另外上游只发行静态 `libkmc_core.a`，
   `package_type="library"` 会被 conan 要求声明 shared 选项——应声明
   `"static-library"`（加 shared=True 空开关才是坏味道）。
4. **捆绑 pybind11 2.3.dev 与 Python ≥3.11 结构性不兼容**：PyFrameObject 3.11 起
   不透明化，`cast.h`/`pybind11.h` 直接访问成员成员即 9 连错；设备 python 3.12.9 /
   harmonybrew 3.13.15 无旧版可退。

## 判 NOT_RUN 而非硬修的判据（可复用口径）

- 上游官方发行物 `KMC3.2.4.linux.arm64.tar.gz` 实核清单 =
  `bin/{kmc,kmc_tools,kmc_dump} + bin/libkmc_core.a + include/kmc_runner.h`，
  **不含** `py_kmc_api*.so`；
- 上游 `.github/workflows/main.yml` 的 make 目标 = `kmc kmc_tools kmc_dump`，
  **不含** `py_kmc_api`，workflow **也不引用** `tests/py_kmc_api/run.py`。

⇒ Python 绑定及其 11 个 pytest 用例不在上游交付面/CI 面 → 判 NOT_RUN 并写明双依据，
不要为它升级第三方 pybind11 或引入补丁。**替代验证**：`test_package` 用底层
`kmc_runner.h`（py_kmc_api 的底层 API）做等价消费断言（本任务 T5：Stage1/Stage2
结果 `nSeqences=1 / nTotalKmers=70 / nUniqueKmers=40`）。

## 附带经验：静态库的捆绑符号依赖必须入包

`nm -u libkmc_core.a | grep inflate` 有引用（`fastq_reader.o` 的 gzip 流解码），
下游不带 zlib 必然 `undefined symbol: inflateInit2_`（实测）。官方发行物不带
`libz.a`（假设消费者自备）；Conan 包必须自包含 ⇒ `package()` 把同一份捆绑
`libz.a` copy 进 `lib/`，`cpp_info.libs = ["kmc_core", "z"]`（引用者在前，
链接器单遍序敏感）。R26 合规：系统同名库 zlib 仅静态 `.a` 出包，无 `.so`。

## 复现命令

```sh
# 现象 1（未打补丁的源）：
grep -rn "ext/algorithm" --include='*.h' "$HOME/tmp/kmc-3.2.4/src/KMC-3.2.4" | head
# 现象 2（zlib configure 探 gcc）：
cd "$HOME/tmp/kmc-3.2.4/src/KMC-3.2.4/3rd_party/cloudflare" && /data/service/hnp/bin/bash ./configure 2>&1 | tail -3
# 修复后全链路（干净轮由采信轮执行）：
conan create "$HOME/ws/worktrees/kmc-3.2.4/archives/k/kmc/3.2.4" \
  -pr:h="$HOME/ws/worktrees/kmc-3.2.4/ci/conan/profiles/ohos-aarch64" \
  -pr:b="$HOME/ws/worktrees/kmc-3.2.4/ci/conan/profiles/ohos-aarch64" -c tools.build:jobs=2
```

## 关联

- 补丁：`archives/k/kmc/3.2.4/patches/0001-libcxx-portability-ext-algorithm-to-std-algorithm.patch`
- manifest `knowledge_gained`：三条均以 `# knowledge_ref: E672` 行尾注释引用
