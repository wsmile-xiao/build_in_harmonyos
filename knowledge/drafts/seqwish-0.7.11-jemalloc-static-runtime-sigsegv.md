# DRAFT: 制品仓 jemalloc 静态库让链接它的 C++ 可执行文件在 OHOS aarch64 上启动即 SIGSEGV

- **草稿 id**: `DRAFT-SEQWISH-0711-JEMALLOC-STATIC-RUNTIME-SIGSEGV`
- **来源**: seqwish 0.7.11 适配（HarmonyOS PC / OHOS 26.0.0.18 / aarch64 / musl / clang 15）
- **严重度**: 1（阻断级：进程无法启动，且编译链接期零征兆）

## 现象

上游 `CMakeLists.txt` 无条件 `find_library(JEMALLOC jemalloc)` + `target_link_libraries(seqwish ... jemalloc)`。
用制品仓 `jemalloc/5.3.0`（只有静态库 `libjemalloc.a` / `libjemalloc_pic.a`，无共享版）链接后：

- `conan create` **全绿**（无 warning、无 undefined symbol、无签名异常）；
- 包内 `bin/seqwish` 一执行即 **SIGSEGV（exit 139）**，连 `--version` / `-h` 都不行。

## 隔离复现（根因定位）

| 用例 | 退出码 |
|------|--------|
| 空 `main()`（无 jemalloc） | 0 |
| 空 `main()` + `-ljemalloc` | **139** |
| 空 `main()` + `-ljemalloc -lpthread` | **139** |
| 空 `main()` + `libjemalloc_pic.a` | **139** |
| 带 `std::string` / `std::unordered_map` 静态初始化的空 main + `-ljemalloc` | **139** |

即：**只要链接该静态库，任何 C++ 可执行文件在进入 `main` 之前就崩**，与是否使用 jemalloc API、是否多线程无关。

排除项：`llvm-nm` 扫描该库的 `__libc_*` / `_IO_*` 等 glibc 专有符号命中 **0**（`GLIBC_MARKERS=0`），
故**不是** libc 归属错配，属依赖实现与平台运行时的兼容缺陷。

## 处置（seqwish 采用）

1. 补丁 `0005-jemalloc-optional.patch`：把上游硬编码的 jemalloc 链接改成 option（默认 ON 保持上游行为）；
2. 配方侧传 `-DSEQWISH_USE_JEMALLOC=OFF`（附证据注释），改用平台自带分配器；
3. 验收不止于 `conan create`：取包内 `bin/seqwish` 实跑 `--version` / `-h` 与真实数据往返。

## 一般化判据

- 凡配方/上游把 allocator（jemalloc/tcmalloc/mimalloc 等）**静态库无条件链进可执行文件**，交叉适配前先做空 main 隔离复现；
- 判决口径：**"编译通过"不是可用性证据**——必须实际执行包内产物；
- 同类陷阱：静态 x86 JIT/解释器、glibc 专有 API 实现等，都是"链接期静默、运行期才崩"。

## 关联

- 配方: `archives/s/seqwish/0.7.11/conanfile.py`（`requirements()` 不引 jemalloc，注释含证据）
- 补丁: `archives/s/seqwish/0.7.11/patches/0005-jemalloc-optional.patch`
- 笔记: `archives/s/seqwish/0.7.11/notes.md`
