# DRAFT-ohos-openmp-runpath：clang 交叉编译的 RUNPATH 指向宿主 resource dir，-fopenmp 动态链的 libomp.so 在 OHOS 上 loader 找不到

> Status: **Draft**（待审核 promote）| severity: `2` | category: `build-system|toolchain|openmp` | Updated: 2026-10-03
> 对应: `knowledge/drafts/DRAFT-ohos-openmp-runpath-static-openmp.kv`
> 来源: spaced 1.2.0-201605 适配 HarmonyOS PC（aarch64 OHOS / clang 15 / libc++）

---

**匹配关键词**：openmp, -fopenmp, -static-openmp, libomp, libgomp, omp.h, RUNPATH, RPATH, rpath, cross compile, cross-compile, resource dir, clang-15, loader, ld-musl, ld-linux-aarch64, OHOS, aarch64, DT_NEEDED, self-contained binary, CLI tool, spaced

## 错误签名（error_signature）

```text
Error loading shared library libomp.so|Error relocating .*: omp_|omp_get_thread_num: symbol not found|__kmpc_for_static_init_4: symbol not found|error: cannot find -lomp|unable to find library -lgomp
```

## 预扫（prescan）

- `prescan_pattern`: `-fopenmp|-lgomp|omp_get_thread_num|omp_set_num_threads|#pragma[[:space:]]+omp|include[[:space:]]*<omp\.h>|-static-openmp`
- `prescan_globs`: `Makefile*, *.mk, configure.ac, CMakeLists.txt, meson.build, conanfile.py`
- `prescan_severity`: 2

## 根因（root_cause）

clang 在链接时会把 RUNPATH 默认写成本**宿主** clang 的 resource dir。交叉编译（`--target=aarch64-linux-ohos` + `--sysroot=<ohos-sysroot>`）时这个值**不会**跟着变成目标 sysroot 下的路径。实测 OHOS clang 15：

```text
$ readelf -d spaced
 0x000000000000001d (RUNPATH)  Library runpath: [/usr/lib/llvm-15/lib]
 0x0000000000000001 (NEEDED)   Shared library: [libomp.so]
 0x0000000000000001 (NEEDED)   Shared library: [libc.so]
```

`/usr/lib/llvm-15/lib` 是宿主 Ubuntu 的 clang 包目录，目标设备上不存在；OHOS musl loader 的默认搜索路径里也没有 `libomp.so`（NDK 自带的 libomp 只在 NDK 目录里，不在镜像的 `/system/lib64`）。于是执行直接失败：

```text
$ ./spaced -h
Error loading shared library libomp.so: No such file or directory (needed by ./spaced)
Error relocating ./spaced: omp_set_dynamic: symbol not found
Error relocating ./spaced: omp_set_num_threads: symbol not found
Error relocating ./spaced: __kmpc_fork_call: symbol not found
Error relocating ./spaced: __kmpc_dispatch_init_4u: symbol not found
...（共 8 条 __kmpc_* 符号未定义）
```

**为什么这特别容易漏**：编译链接全过、`conan create` 的 `build()` 阶段全过，只有真正**执行**二进制时才炸。而 R34/L1e 这套门禁恰恰要求 `test_package` 真跑产物，所以它必然在最后一步才暴露，且症状是「测试失败」而不是「构建失败」，很容易被误判成测试脚本写错。

补充：本仓 `archives/a/aaphoto/0.45` 证明 OHOS NDK 确实带 libomp（它的 `0001/0002` 补丁删掉上游写死的 `-lgomp`，交给 clang 的 `-fopenmp` 拿到 SDK 的 libomp），但那是**动态**链；aaphoto 是库导向的包，产物本身不要求被直接执行，所以这条 RUNPATH 坑在它身上不会暴露。**CLI 工具必须被执行**（L1e 反向验证的前提），就会正面撞上。

## 推荐方案（rec_approach: `static-openmp-for-ohos-cli-tools`）

1. **`-fopenmp -static-openmp` 一起给**（`-static-openmp` 本身蕴含 `-fopenmp`，两者同时写是为了让命令行自解释）。效果：`DT_NEEDED` 从 `libomp.so + libc.so` 收敛到只剩 `libc.so`，得到自包含二进制，RUNPATH 指向哪里都不再影响启动。
2. **OpenMP 开关不可省、也不可当成优化项**。spaced 的 `sort.h` 有 7 处 `#pragma omp parallel for`（行 273/423/438/470/567/658/671）以及 `omp_get_thread_num()` / `omp_set_num_threads()` / `omp_set_dynamic()`，`sort.h:35` 还直接 `#include <omp.h>`。**不打开 OpenMP 不会编译失败**，只是 `#pragma omp` 被当未知 pragma 忽略、程序退化成串行/错误结果 —— 比编译错误危险得多。
3. **别用「配 LD_LIBRARY_PATH」绕**。CLI 应用包的产物路径不应该依赖调用方环境变量，那会让包在 CI worker / 设备上依赖本仓库没有的现场配置。真要动态链，就必须用 Conan toolchain 把 rpath 明确设到包内的 lib 目录。
4. **把「二进制真的能启动」做成断言**。本包消费者测试的 A1/A2/A4 就是 `[ -x <pkg>/bin/spaced ]`、`spaced -h` 退 0 且打出 Usage、`spaced --version` 退 0；再加上 L1e 反向破坏（移走 `bin/` 后测试必须失败），就把「静态链 libomp」这个决策钉在了 CI 上。
5. 若某些包确实需要动态 OpenMP（例如还要向上层暴露 libomp 符号），那就反过来在 recipe 里显式写 `-Wl,-rpath,$ORIGIN/../lib` 并把 `libomp.so` 收进包里，不要依赖 clang 的默认 RUNPATH。

## 证据（evidence，逐字）

动态链（`-fopenmp`，无 `-static-openmp`）实测：

```text
readelf -d spaced
 0x000000000000001d (RUNPATH)  Library runpath: [/usr/lib/llvm-15/lib]
 0x0000000000000001 (NEEDED)   Shared library: [libomp.so]
 0x0000000000000001 (NEEDED)   Shared library: [libc.so]
./spaced -h
  Error loading shared library libomp.so: No such file or directory (needed by ./spaced)
  Error relocating ./spaced: omp_set_dynamic: symbol not found
  Error relocating ./spaced: omp_set_num_threads: symbol not found
  Error relocating ./spaced: __kmpc_fork_call: symbol not found
  Error relocating ./spaced: __kmpc_dispatch_init_4u: symbol not found
  Error relocating ./spaced: __kmpc_dispatch_next_4u: symbol not found
  Error relocating ./spaced: omp_get_thread_num: symbol not found
  Error relocating ./spaced: __kmpc_for_static_init_4: symbol not found
  Error relocating ./spaced: __kmpc_for_static_fini: symbol not found
→ 8 条 __kmpc_* / omp_* 未定义，程序无法启动。
```

静态链（`-fopenmp -static-openmp`）实测：

```text
readelf -d spaced
 0x000000000000001d (RUNPATH)  Library runpath: [/usr/lib/llvm-15/lib]
 0x0000000000000001 (NEEDED)   Shared library: [libc.so]
./spaced -h
  Alignment-free sequence comparison tool using spaced word frequencies
  Usage: ./spaced [options] <sequence file>
  rc=0
→ RUNPATH 仍是宿主 resource dir（无意义但无害），NEEDED 只剩 libc.so。
```

对照：本机 clang-15 的 `omp.h` 来自 clang resource dir，`libomp.a` / `libomp.so` 都在 OHOS SDK 的 `llvm/lib/aarch64-linux-ohos/` 下（两者均存在），所以 `-static-openmp` 在 OHOS 工具链上是**有库可用**的，不是空想。

先例：`archives/a/aaphoto/0.45` 的 `conanfile.py` docstring 明确记载「the Makefile hardcodes GCC's `-lgomp`; on OHOS we build with clang where `-fopenmp` auto-links the OHOS SDK's `libomp`」，其 `0001/0002` 补丁删掉 `-lgomp`。

## 复现命令（verification_cmd）

```sh
# 复现：动态链 OpenMP 后 RUNPATH/NEEDED 长这样
/opt/lpk-fixed/clang++ -O3 -std=c++17 -fopenmp src/*.cc src/*.cpp -o spaced_dyn
readelf -d spaced_dyn | grep -E 'NEEDED|RUNPATH'
./spaced_dyn -h ; echo "rc=$?"      # Error loading shared library libomp.so ... rc=127

# 正解：静态链
/opt/lpk-fixed/clang++ -O3 -std=c++17 -fopenmp -static-openmp src/*.cc src/*.cpp -o spaced
readelf -d spaced | grep -E 'NEEDED|RUNPATH'   # 只剩 libc.so
./spaced -h | head -2 ; echo "rc=$?"           # rc=0
```

## 适用范围与边界

- **适用**：任何在 OHOS aarch64 上需要 OpenMP、且产物是**要被直接执行的 CLI 工具或脚本**的包。
- **边界**：库导向的包（只导出符号、由最终应用链接）不受影响 —— 它们不需要在 OHOS 上直接跑。明确要求动态 OpenMP 并把 libomp 打进包 + 设置 `$ORIGIN` rpath 的方案不受本条约束。非 OpenMP 场景若出现同类「DT_NEEDED 在目标上找不到」症状，先按 R26/R49 的思路把依赖静态并入或收进包内 rpath，不要把本条的 `-static-openmp` 机械套上去。

## 关系

- **similar_to**：`archives/a/aaphoto/0.45`（OHOS 上 `-fopenmp` 能拿到 NDK 的 libomp，但走的是动态链）
- **caused_by**：clang 默认把 RUNPATH 写成宿主 resource dir + OHOS 镜像不含 libomp.so
- **prerequisite_of**：任何在 OHOS 上需要「跑起来」并被 L1e 反向验证的 CLI 工具
- **conflicts_with**：无

---

*本文件由 `knowledge/drafts/DRAFT-ohos-openmp-runpath-static-openmp.kv` 字段派生生成（补齐 kv↔md 配套）；内容与 kv 一致，待主编审核 promote 后转入 `knowledge/doc/`。*
