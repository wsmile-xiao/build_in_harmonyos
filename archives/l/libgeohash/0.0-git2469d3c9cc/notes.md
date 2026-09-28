# libgeohash 0.0-git2469d3c9cc 适配笔记

## 编译环境
- 构建系统: makefile（原始 Makefile，无 configure）
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4（OHOS aarch64 profile）
- 状态: built

## 编译步骤
1. init-build：从官方源 https://github.com/simplegeo/libgeohash @ commit 2469d3c9cc 下载 tarball，
   校验 SHA-256（2e507fadee14faf7662d8c5a9f2a212e11a25fe5efc9d28d21ff2437f95737fe），
   建立 .orig/.work 双轨。
2. lang-preflight：源码为纯 C（2 个源文件 100%），与任务 cpp 兼容族通过。
3. 手动编译：clang -c geohash.c && ar rcs libgeohash.a，上游测试 geohash_test.c 编译运行。
4. conan-init 生成配方 → 按 Makefile 项目重写 conanfile.py（无 configure，make 直接构建，
   basic_layout 下 make 需在 source_folder 执行，编译器从 conan conf tools.build:compiler_executables 获取）。
5. conan-verify：G1-G4 + L2/L4/L5 全部 PASS（含 test_package 消费者测试 ctest）。
6. finish：W2 结构检查 + W3 本地 CI 模拟（conan create + 上游测试 + junk_check 单包口径）通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 geohash.c get_neighbor() 对高精度(≥8) geohash 计算邻居时输出截断/错误 | get_neighbor 中 `char *base = malloc(1)` 后 `strncat(base, hash, len-1)` 再 `strcat(base, last_hash)`，堆缓冲区溢出、越界读写，属上游缺陷 | 补丁 0002：按 `malloc(hash_length + 1)` 分配前缀缓冲；修复后上游测试与高精度邻居断言全部通过 |
| 2 | 原始 Makefile 写死 `gcc`/`ar`，CI 环境无 gcc | 上游 Makefile 硬编码工具链 | 补丁 0001：Makefile 改用 `$(CC)/$(AR)/$(RANLIB)` 变量（`?=` 可注入），conanfile.py 从 conan conf 注入 clang/llvm-ar |
| 3 | conanfile 中 `tools.build:compiler_executables:c` 键不存在 | Conan 2.29 该 conf 是 dict，不是子键 | 改为 `self.conf.get("tools.build:compiler_executables", default={})` 后取 `["c"]` |
| 4 | basic_layout 下 make 报 "No makefile found" | 构建目录与源码目录分离，make 需在 source_folder 执行 | `self.run(..., cwd=self.source_folder)` |
| 5 | W3 junk_check full 模式误扫 main 上其他库历史垃圾（cloog/kics） | 本机共享工作区 main 存在其他库遗留 .build-closed/.staging-verified | 本地 W3 用 JUNK_PR_DIFF=单包 pr.diff 口径（CI 本身就是 PR diff 模式）；E017 镜像注入残留 conandata.yml.ghfast-bak 提交前清理 |

## 源码修改
- patches/0001-Makefile.patch：Makefile 工具链变量化（平台适配）
- patches/0002-geohash.c.patch：get_neighbor 堆溢出修复（上游 bugfix，跨平台）

## 依赖版本
无外部依赖（纯 C 单文件静态库）。

## 验证结果
- 上游测试 geohash_test.c（1 个 main 入口，含 encode/decode/neighbors 断言）：PASS（修复后无 Error 输出）
- test_package 消费者测试 test.c（17 断言：encode/decode/neighbors 高精度/dimensions）：ctest PASS
- conan create + test_package：PASS（W3 本地 CI 模拟 100%）

## 交付物
- archives/l/libgeohash/0.0-git2469d3c9cc/conanfile.py
- conandata.yml（官方源 + 真实 SHA-256）
- test_package/（CMake 消费者测试 + MANIFEST.yml）
- patches/（2 个补丁）

## 注意事项
- 库类型（静态库），非 CLI，无 commands.json（R38 不适用）。
- conandata.yml 提交前必须确认无 ghfast-bak/.orig 残留（E017 镜像注入备份）。
- 知识候选：get_neighbor 堆溢出（malloc(1)+strncat 拼接前缀）→ 待按七轴查重后决定路径 B 草稿。

**编译结束**: 2026-09-27 06:00
**最终状态**: built
---

**编译结束**: 2026-09-27 06:06
**最终状态**: published
