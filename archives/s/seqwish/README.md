# seqwish

[seqwish](https://github.com/ekg/seqwish) 从序列集合及其比对结果归纳出变异图（variation graph），
是 pangenome / graph genome 工具链的基础构件。

- 本仓库归档路径：`archives/s/seqwish/0.7.11/`
- 交付形态：命令行工具 `bin/seqwish`（Conan `package_type=application`）
- 运行期依赖：`zlib/1.3.2` + 平台 `libomp.so`

## 版本索引

| 版本 | 状态 | 适配日期 | 说明 |
|------|------|---------|------|
| 0.7.11 | built | 2026-10-01 | 首次适配 HarmonyOS PC（arm64）；5 枚可移植性补丁；上游测试 30/30、适配补全用例 25/25 通过 |

## 鸿蒙适配要点

1. **submodule 源码获取**：上游 release tarball 中 `deps/` 下 11 个 submodule 目录为空，
   需按 `.gitmodules` 声明的固定 commit 逐个取源（另含 `deps/mmmulti/deps/mio` 与
   `deps/sdsl-lite/external/libdivsufsort`）。这些来源统一声明在 `0.7.11/conandata.yml`
   的 `sources.submodules` 中，由配方的 `source()` 解包到对应相对路径。
2. **jemalloc 关闭**：`jemalloc/5.3.0` 静态库在 OHOS 上会让任何链接它的 C++ 可执行文件
   启动即 SIGSEGV（该平台无共享版可用）。补丁 0005 把上游 jemalloc 链接改为可选开关
   （默认 ON，保持上游行为），本包配方显式关闭并改用平台自带分配器；隔离复现表见
   `0.7.11/notes.md`。
3. **OpenMP**：上游 CMake 只在 Darwin/Linux 分支链接 OpenMP，OHOS 下
   `CMAKE_SYSTEM_NAME=HarmonyOS` 两个分支都不命中，由配方 `generate()` 显式提供 `-fopenmp`
   （链接 sysroot 中的 `libomp.so`）。
4. **POSIX 化**：`get_current_dir_name()` 为 glibc 扩展，在 musl 下不存在，补丁 0003 改为
   POSIX `getcwd` 实现（不引入平台条件编译宏）。
5. **CMake 4 兼容**：上游 `cmake_minimum_required(VERSION 3.1)` 与 sdsl-lite 2.8 的内嵌
   旧版本声明会被 CMake 4 拒绝，补丁 0001 抬高父工程最低版本，子工程由父级透传
   `CMAKE_POLICY_VERSION_MINIMUM`。

## 使用方法

```bash
conan install --requires=seqwish/0.7.11 -r=ohpcd
seqwish -s sequences.fa -p alignments.paf -g output.gfa   # 见 bin/seqwish -h
```

## 验证

- 上游测试 `test/t/01_seqwish.t`（bash-tap，30 断言）：**30/30 PASS**
- 适配补全消费者用例 `0.7.11/test_package/test_seqwish.sh`：**25/25 PASS**（含完整工作流）
- 门禁：G2/G3/G4 + L2/L4/L5 PASS；W3 本地 CI 模拟（与 CI 同源脚本）exit_code=0

详见 `0.7.11/reports/test-report.md`、`0.7.11/notes.md`。
