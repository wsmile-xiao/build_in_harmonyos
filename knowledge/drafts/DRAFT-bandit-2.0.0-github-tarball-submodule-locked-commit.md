# DRAFT-bandit-2.0.0-github-tarball-submodule-locked-commit：官方 tarball 缺 submodule 且为硬依赖时，按锁定 commit 从官方源补齐并 Conan 多源打包

> Contributor: pc4-8 | Status: Draft | Updated: 2026-09-19
> Source: bandit 2.0.0 HarmonyOS PC adaptation（archives/b/bandit/2.0.0，r01）
> 对应：knowledge/drafts/DRAFT-bandit-2.0.0-github-tarball-submodule-locked-commit.kv

## 现象

GitHub 官方 archive tarball（`https://github.com/<owner>/<repo>/archive/<tag>.tar.gz`）
从不包含 git submodule 内容：submodule 目录在解压后为空。当 submodule 是编译或
头文件的**硬依赖**时，直接构建失败：

```text
# bandit 2.0.0 实测首错（bandit/bandit.h:23）
fatal error: 'bandit/assertion_frameworks/snowhouse/snowhouse/snowhouse.h' file not found
# cotire（构建期 cmake 模块 submodule）
CMake Error at CMakeLists.txt:1 (cmake_minimum_required): ...（cotire.cmake 缺失）
```

## 根因分析

GitHub archive 生成器只打包 git 跟踪树，submodule 以空目录/占位形式出现（.gitmodules
声明了 path 与 url，但内容不随 archive 分发）。`get()` 单源下载 + `strip_root` 得到的
源码树不完整。依赖是"头文件 include 硬依赖"时无法绕过（与可选依赖不同，可选依赖可
参考 E425 用占位目录裁剪功能范围）。

## 解决方案

1. **锁定 commit 解析**：用 GitHub Trees API 获取 tag 的完整树，读取 mode=160000
   （submodule）条目 sha：
   ```bash
   curl -s "https://api.github.com/repos/<owner>/<repo>/git/trees/<tag>?recursive=1"
   # 输出形如: {"path":"bandit/assertion_frameworks/snowhouse","mode":"160000","type":"commit","sha":"34d4b6df..."}
   ```
2. **官方源补齐**：从官方 codeload/github 下载该 commit 归档并解压到 submodule 路径：
   ```bash
   curl -sL "https://codeload.github.com/<subowner>/<subrepo>/tar.gz/<sha>" -o sub.tar.gz
   tar -xzf sub.tar.gz --strip-components=1 -C <path>/<submodule-path>
   ```
3. **Conan 多源声明**：conandata.yml `sources` 用列表，逐项 `url`+`sha256`，
   用 `destination` 指定解压落点；配方 `source()` 逐项 `get(self, **item)`：
   ```yaml
   sources:
     - url: "https://github.com/banditcpp/bandit/archive/v2.0.0.tar.gz"
       sha256: "e86b7c..."
     - url: "https://github.com/joakimkarlsson/snowhouse/archive/34d4b6df....tar.gz"
       sha256: "71e4af..."
       destination: "bandit/assertion_frameworks/snowhouse"
   ```
4. 只对**打包必需**的 submodule 进 conandata；纯构建期工具（如 cotire）不进配方
   （header-only 配方不构建 specs 时不需要）。

## 验证

- bandit 2.0.0：补齐 snowhouse 后本地 `cmake + make bandit-specs` 成功，上游测试
  310/314 通过；`conan create`（W3/G2）通过，消费者用例 `1/1 Test Passed`。
- 命令与退出码：`cmake -S . -B build -DCMAKE_POLICY_VERSION_MINIMUM=3.5`（exit 0）；
  `CMAKE_POLICY_VERSION_MINIMUM=3.5 make -C build bandit-specs`（exit 0）；
  `conan create .../bandit/2.0.0 -pr:h=ci/conan/profiles/ohos-aarch64 --build=missing`（exit 0）。

## 适用边界 / 反例

- 适用：GitHub（或同类"archive 不含 submodule"托管）C/C++ 库，submodule 为头文件/编译硬依赖。
- 边界：submodule 为**可选**功能依赖时，优先 E425 方案（占位裁剪，不下载），避免把外部
  submodule 混入本库 PR；需要真实功能时按 R36 先单独适配发布依赖。
- 反例：submodule 依赖其他非官方源/私有仓库时不可用（锁定 commit 后仍须官方可达）。

## 查重与关系

- similar_to: E150（submodule missing 识别）、E425/DRAFT-pico-sdk-empty-submodules-scope（可选依赖裁剪，方向互补）
- caused_by: 无；prerequisite_of: 无；conflicts_with: 无
- exact_duplicate=false, causal_duplicate=false, trigger_overlap=true（同"tarball 缺 submodule"触发）
- solution_overlap=partial（E425 占位 vs 本方案官方补齐），combination_novelty=true（API 锁定 commit+多源 destination 打包组合）
