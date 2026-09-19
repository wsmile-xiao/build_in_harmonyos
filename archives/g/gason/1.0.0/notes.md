# gason 1.0.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-19
- 编译器: clang/clang++ 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: published

## 官方来源
- 上游: https://github.com/vivkin/gason（tag v1.0.0，仅 tag 无 release 资产）
- 源码 tarball: https://github.com/vivkin/gason/archive/refs/tags/v1.0.0.tar.gz
- SHA-256: 773bc850abc109529c4cd972c1b43a119de763c25011172bf7eb2a0668632d79
- 无第三方运行时依赖（C++11 单静态库 + 单头文件）

## 编译步骤

```bash
# 下载（github.com 直连超时，codeload 可达）
python3 scripts/ohc-run.py init-build gason 1.0.0 \
  --url=https://codeload.github.com/vivkin/gason/tar.gz/refs/tags/v1.0.0
# 语言预检
python3 scripts/ohc-run.py lang-preflight gason 1.0.0 --src $BUILD_SRC_DIR
# OS 工具链构建（CMake + ohos.toolchain.cmake）
cmake .. -DCMAKE_TOOLCHAIN_FILE=.../ohos.toolchain.cmake \
         -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5
make -j1   # HMDFS SELinux 禁止 mkfifo → 禁用 make jobserver（E525）
./test-suite  # 上游测试：ALL TESTS PASSED (43/43)
# 配方与验证
python3 scripts/ohc-run.py conan-init gason 1.0.0
python3 scripts/ohc-run.py conan-verify gason 1.0.0   # G0-G4+L2/L4/L5 PASS
python3 scripts/ohc-run.py finish gason 1.0.0 published  # W3 PASS
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载返回 HTML | github.com archive 直连超时，tag 无 release 资产 | 用 codeload.github.com 官方归档 URL |
| 2 | CMake 报 "Compatibility with CMake < 3.5 has been removed" | 上游 cmake_minimum_required(2.8.12)，CMake 4.x 移除 <3.5 兼容 | 补丁提升至 3.10 + 配方 generate() 注入 CMAKE_POLICY_VERSION_MINIMUM=3.5（E103/E187） |
| 3 | benchmark 目标编译失败 'rapidjson/document.h' not found | 发布 tarball 不含 rapidjson 子模块，benchmark 为可选非交付目标 | 补丁加 option(BUILD_GASON_BENCHMARK OFF) + 配方设 OFF（见知识草稿 gason-1.0.0-optional-benchmark-submodule） |
| 4 | make: jobserver mkfifo: Operation not permitted | HMDFS SELinux 禁止 FIFO | make -j1（E525 force-j1） |
| 5 | llvm-ar: Read-only file system（写 /tmp） | 设备 /tmp 只读，llvm-ar 默认临时目录在 /tmp | 构建环境 TMPDIR/TMP/TEMP 指向可写目录（E002/E528） |
| 6 | W3 JC 全量扫描命中其他库基线空文件 | 分支零提交时 junk_check 退化为 full 模式 (git ls-files) 整仓扫描，命中 origin/main 上 cloog 的 .build-closed/.staging-verified 空文件 | 基线隔离复验：记录 SHA-256 → 移出 + git rm --cached → 复跑 finish → 恢复 + 核对 SHA 一致（DRAFT-dr_mp3-0.7.2-baseline-noise-isolation 同型） |

## 源码修改

patches/0001-CMakeLists.txt.patch：
- cmake_minimum_required 2.8.12 → 3.10
- benchmark 目标以 option(BUILD_GASON_BENCHMARK OFF) 门控（rapidjson 子模块不入发布包）
- 补充 install() 规则（libgason.a → lib/，gason.h → include/）

## 依赖版本

无运行时依赖；构建工具：conan 2.29.1、cmake 4.1.2、make 4.4.1、clang 15.0.4、llvm-ar/llvm-ranlib 15.0.4。

## 验证结果

- 上游 test-suite：43 个独立解析断言 ALL TESTS PASSED（16 合规 + 27 非法输入拒绝）
- 消费者用例 test_gason：ALL CHECKS PASSED（name=gason version=1.0 tags=2，12 断言）
- 鸿蒙专项 test_ohos：ALL OHOS-SPECIFIC CHECKS PASSED（UTF-8 中文/数值边界/32 层嵌套/错误输入，10 断言）
- conan-verify：G0-G4 + L2/L4/L5 全过
- W3 本地 CI：setup.sh + build_and_test.sh 通过（基线隔离复验后）

## 知识候选台账（路径 B 判定）

| 候选 | 现象/根因/修复 | 四范围查重 | 七轴结论 |
|------|--------------|-----------|---------|
| C1 CMake 最低版本过旧 | CMake 4.x 拒 <3.5；提升 min + POLICY 参数 | E103/E187 命中 | exact_duplicate → 复用 |
| C2 benchmark 依赖子模块缺失 | tarball 无 rapidjson；option 门控可选目标 | E150/E342/DRAFT-release-tarball 部分覆盖 | combination_novelty + boundary_novelty → 新草稿（见下） |
| C3 make jobserver FIFO | HMDFS SELinux 禁 FIFO；-j1 | E525 命中 | exact_duplicate → 复用 |
| C4 /tmp 只读致 llvm-ar 失败 | TMPDIR 指向可写目录 | E002/E528 命中 | exact_duplicate → 复用 |
| C5 W3 JC 基线噪声 | full 模式扫描其他库空文件；隔离复验 | DRAFT-dr_mp3 命中同型 | exact_duplicate（同 stem 草稿已存在）→ 复用，不重复建草稿 |

路径决定：**new_draft**（路径 B）——C2 新增差异已验证（本任务 W3/G2 真实日志）且可跨库复用（任何 CMake 项目的可选 benchmark/demo 目标依赖未入包子模块时均可套用），其余四项复用既有知识。草稿对：
knowledge/drafts/DRAFT-gason-1.0.0-optional-benchmark-submodule.md/.kv（与归档同 PR 交付）。

**编译结束**: 2026-09-19 01:29
**最终状态**: published