# guilite 2.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-19
- 编译器: clang/clang++ 15 (aarch64-linux-ohos, OHOS 6.0)
- 状态: built（本地 conan-verify G1-G4 + L2/L4/L5 全过；远端 CI/release 待 PR）

## 编译步骤

1. init-build guilite 2.1 --url=https://codeload.github.com/idea4good/GuiLite/tar.gz/refs/tags/v2.1
   - 官方 tag v2.1 源码；SHA-256=54226aaaf5ab4ba617ba71f693963e473aa4ca43f53319e590ec806d5cd3906e
   - 源码整体嵌套在 workspace/ 子目录，init-build 自动提升到源码根
2. lang-preflight：任务标记 cpp，检测器因 Gradle 样例目录误报 mixed（源统计 cpp:19/主体 100%）。
   按 R47 边界规则「辅助样例不算主体」判定为 cpp，继续适配。
3. 手动编译验证：clang++ -std=c++17 -DGUILITE_ON 全部 core/adapter/api_linux/widgets 17 个源文件编译通过。
4. conan-init 生成配方 → 改写为 CMake 配方（实际构建系统为 CMake，非模板默认 autotools）。
5. conan-verify：修复 4 项后 G1-G4/L2/L4/L5 全 PASS：
   - codeload URL 末尾无扩展名 → conandata sources 增加 filename: GuiLite-v2.1.tar.gz
   - 源码嵌套 workspace/ → source() 提升到根目录
   - conandata patches 格式应为 list（conan 2 apply_conandata_patches 按版本取列表）
   - 补丁 hunk 行数头精确化；新增 register 关键字移除（C++17）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | get() BadZipFile | codeload URL 以 /v2.1 结尾无 .tar.gz 扩展名，conan 无法识别压缩格式 | conandata sources 增加 filename 字段 |
| 2 | cmake: 源码目录无 CMakeLists.txt | 官方 tag tarball 源码全部嵌套在 workspace/ | source() 中将 workspace/* 提升到源码根 |
| 3 | apply_conandata_patches 不应用 | conandata patches 写成 {序号: {...}} 字典，conan 2 期望 list | 改为 list 格式 |
| 4 | 补丁解析失败 patch stream incomplete | 手写 hunk 行数与上下文不符 | 用 difflib.unified_diff 重新生成精确补丁 |
| 5 | cmake_minimum_required(2.8) 报错 | CMake 4.x 已移除 <3.5 兼容 | 补丁提升为 3.5 |
| 6 | register 关键字报错 | C++17 移除 register 存储类说明符 | 补丁移除 wave_ctrl.h 4 处无实际作用的 register |
| 7 | 上游 configure 期运行 .sync.sh 遥测脚本 | 上传构建信息到 PowerBI，且依赖 /tmp | 补丁删除 execute_process 调用 |
| 8 | test_package 消费者测试失败 | 我误认为 build_bmp 输出 32 位 BMP（>1000B） | 实际为 16 位 RGB565（≈578B）；断言改为校验存在性+BM魔数 |

## 源码修改

patches/：
- 0001-cmake-fixes.patch：cmake_minimum_required 2.8→3.5；删除 configure 期遥测 .sync.sh 调用
- 0002-remove-register-keyword.patch：widgets_include/wave_ctrl.h 移除 4 处 register（C++17）

## 依赖版本

无第三方依赖（0 requires）。构建工具：conan 2.29.1 / cmake 4.1.2 / clang 15.0.4 / make 4.4.1。

## 上游测试清点（R51 申报表）

GuiLite v2.1 官方 tag 源码（53 文件，剔除 Gradle 样例目录）：
- tests/ 目录：无
- CTest/`make check` 目标：无（CMakeLists.txt 仅构建静态库，无 enable_testing）
- 测试脚本/基准/夹具：无（.sync.sh 为遥测脚本，非测试）
- 结论：上游官方测试声明总数 = 0；无独立上游用例可运行。

## 鸿蒙专项/消费者测试

test_package/test.cpp（真实消费者用例，仅用安装后公开头 core_include/api.h 与 libGuiLite）：
调用 c_rect/c_fifo/get_time_in_second/second_to_day/build_bmp 共 5 个公开 API，
含 10 项断言（矩形几何、fifo 读写往返、时间有效性、BMP 产物存在性与 BM 魔数）。
conan create 内 ctest 实测通过（1/1，exit 0）。

## 验证结果

```bash
conan-verify guilite 2.1 → G0-G4 PASS, L2/L4/L5 PASS
conan create（ohos-aarch64 profile）→ 构建+test_package 通过
```

## 交付物

archives/g/guilite/2.1/：conanfile.py + conandata.yml + patches/ + test_package/ + manifest.yaml + notes.md + reports/

## 注意事项

- GuiLite 2.1 上游无任何测试资产，PASS 口径为「消费者用例 1/1 + 上游声明 0 项」。
- 本库为纯库包（无 bin/），按 R38 不需 commands.json。
- 语言判定：核心库 100% C++；Gradle/ 目录仅为样例（其 build.gradle 指向同一批 C++ 源），不构成 mixed。

## 基线隔离复验审计（W3/finish 命中其他库既有基线文件）

W3 本地 CI 的 JC 检查在 full 模式下命中提交前已存在于 main 的其他库基线文件（空标记文件），
按 SKILL 基线隔离复验流程处理（未修改、未提交、未写入 PR）：

| 路径 | pre_sha256 | 隔离命令 | 复跑命令 | rerun_exit_code | 恢复命令 | post_sha256 |
|------|-----------|---------|---------|----------------|---------|------------|
| archives/c/cloog/0.21.1/.build-closed | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 | git rm --cached + mv 至 /storage/Users/currentUser/tmp/guilite-jc-isolation3/ | run_local_ci("guilite","2.1")（finish W3） | 0 | mv 原路径 + git add -f | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| archives/c/cloog/0.21.1/.staging-verified | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 | 同上 | 同上 | 0 | 同上 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| archives/k/kics/2.1.20/.staging-verified | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 | 同上 | 同上 | 0 | 同上 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |

- pre_sha256 == post_sha256（e3b0c442… 空文件）✓
- 当前库 diff/staged/PR 未包含上述路径 ✓（`git status -s` 对这些路径为空）
- 隔离复验通过后继续当前库审计与交付；这些基线文件未修改、未提交、未写入知识库或 PR。
---

**编译结束**: 2026-09-19 03:50
**最终状态**: built
