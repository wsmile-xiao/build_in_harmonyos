# E606 — FETCHCONTENT_SOURCE_DIR_&lt;DEP&gt; 目录名与 conan get(strip_root=True) 落位不一致

> 草稿（draft）。来源任务：osqp/1.0.0 适配（HarmonyOS PC aarch64），Agent 56F6，2026-09-08。

## 错误特征

```
CMake Error at .../Modules/FetchContent.cmake:2057 (message):
  Manually specified source directory is missing:

    FETCHCONTENT_SOURCE_DIR_QDLDL --> /.../b/src/_offline_deps/qdldl-0.1.8
Call Stack (most recent call first):
  /.../Modules/FetchContent.cmake:2384 (__FetchContent_Populate)
  algebra/_common/lin_sys/qdldl/qdldl.cmake:20 (FetchContent_MakeAvailable)
```

配置阶段直接失败，一个源文件都没编译。

## 触发条件

- 构建系统: CMake（上游用 `FetchContent_Declare(... GIT_REPOSITORY ...)` 引入依赖）
- 阶段: configure（`conan create` 的 build() → cmake.configure()）
- 前置: 配方在 `source()` 里用 `conan.tools.files.get(..., strip_root=True)` 把依赖官方
  tarball 落到本地，并试图用 `-DFETCHCONTENT_SOURCE_DIR_<DEP>` 让上游 FetchContent 离线消费

## 根因分析

`get(..., strip_root=True)` 会**剥掉 tarball 顶层目录**（GitHub 归档的 `qdldl-0.1.8/`），
依赖源码直接落在 `destination` 本身。而 `FETCHCONTENT_SOURCE_DIR_<uppercaseName>` 的语义是
"把这个目录**当作**依赖源码根目录"，与 tarball 内部的目录名无关。配方若按 tarball 目录名
拼接路径（`.../_offline_deps/qdldl-0.1.8`），该路径必然不存在 → CMake 在
`__FetchContent_Populate` 处判定"Manually specified source directory is missing"。

## 解决方案

### 推荐方案：显式目录名 + 两处共用同一常量

```python
class OsqpConan(ConanFile):
    # 上游 FetchContent(qdldl) 的离线源码落位目录（相对 source_folder）
    QDLDL_OFFLINE_SUBDIR = ("_offline_deps", "qdldl")

    def source(self):
        get(self, **self.conan_data["sources"]["qdldl"],
            destination=os.path.join(self.source_folder, *self.QDLDL_OFFLINE_SUBDIR),
            strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["FETCHCONTENT_SOURCE_DIR_QDLDL"] = os.path.join(
            self.source_folder, *self.QDLDL_OFFLINE_SUBDIR)
```

要点：
1. 目录名由我们指定（`qdldl`），不受 tarball 顶层目录名与版本升级影响；
2. `source()` 与 `generate()` 共用同一个类常量，杜绝两处路径漂移；
3. 用 `tc.cache_variables`（等价 `-D`），保证在 `FetchContent_MakeAvailable` 之前生效。

采用该方案后**不需要**给上游 CMake 打"自建 vendor 开关"补丁（历史上 osqp 曾用
`BUILD_QDLDL` 开关补丁，本方案零补丁达成同样离线效果）。

### 禁止做法

- ❌ 假定 `strip_root=True` 后仍存在 `qdldl-<version>/` 子目录；
- ❌ 在 `source()` 与 `generate()` 各写一遍字面量路径（版本升级/重构时只改一处 → 静默失效）；
- ❌ 为此再写一个改上游构建系统的 vendor 补丁（FetchContent 原生支持覆盖源目录）；
- ❌ 保留联网 `git clone`（配置期取 HEAD 标签内容，不可复现，CI 抖动）。

## 验证

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=同一 profile
# 期望：configure 输出出现 "-- Fetching/configuring QDLDL solver" 且不再有
#       "Manually specified source directory is missing"；构建与 test_package 均 exit 0
grep -E "Manually specified source directory" <create.log>; echo "无输出=已修复"
```

实测（osqp 1.0.0 / OHOS aarch64 / clang 15.0.4 / Conan 2.29.1）：
第一次 conan create exit 1（本错误）→ 按推荐方案修改后 exit 0，
产物 `libosqpstatic.a` + `share/osqp/codegen_files/src/qdldl.c` 均正常。

## 关联条目

- 相关: E342（test-only FetchContent 联网下载阻塞离线构建：禁用网络测试 + 消费者测试，
  其 fallback 正是"注入已校验的离线测试依赖源码"）
- 相关: E378（conan source_folder 与 worktree 污染）
