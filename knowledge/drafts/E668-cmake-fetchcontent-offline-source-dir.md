# E668 CMake FetchContent 构建期 git clone 不可复现：FETCHCONTENT_SOURCE_DIR_<名> 离线注入

> 状态: Draft（待审核 promote）| 日期: 2026-09-22
> 来源: feat/blaspp-2024.10.26（上游 test/CMakeLists.txt 构建期 FetchContent 拉取 testsweeper tag v2024.05.31）
> 机器可读层: 同目录 `E668-cmake-fetchcontent-offline-source-dir.kv`

## 现象

blaspp 的上游 tester 需要 testsweeper 库，`test/CMakeLists.txt` 用
`FetchContent_Declare(GIT_REPOSITORY github…/testsweeper GIT_TAG v2024.05.31)`
+ `FetchContent_MakeAvailable` 在 **conan create / CI 构建期**实时 git clone。
这意味着配方 sha256 锚定的源码之外，构建输入还被构建期的网络行为决定。

## 根因（三重不可复现面）

1. CI worker / 设备构建环境的网络与 github 可达性不受配方控制；
2. `git` 二进制是否在构建 env 的 PATH 里不受配方控制（OHOS Python 对裸命令
   名不做 PATH 搜索是另一独立坑，见 notes/device-facts.md §一.14）；
3. GIT_TAG 非commit 锚定时上游 force push 会改写构建输入——配方源码
   sha256 管不住构建期下载物。

## 解法（上游机制内，零 CMakeLists 改动）

1. 同 tag 源码以**解包源码形态**随配方导出（`export_sources()` 把
   `vendor/testsweeper-2024.05.31/` 复制进源码树；PF2/JC3 制品闸禁 tarball，
   必须解包入仓——上游解包 71 文件，剔除与构建无关的仓库元数据 6 个
   （`.github/workflows/` 5 个 + `.gitignore`，按评审意见删除），本例 65 文件 / 714K）；
2. configure 时设 CMake 官方变量
   `FETCHCONTENT_SOURCE_DIR_TESTSWEEPER=<源码树>/vendor/testsweeper-2024.05.31`
   ——`FetchContent_MakeAvailable` 检测到该变量即跳过下载、用本地目录；
3. 版本一致性：vendor 版本与上游 CMakeLists 钉死的 `GIT_TAG v2024.05.31`
   一致（sha256 `64ac685f94132f71bde82d4ac38021dfe2c42dc3d2387829d1d26dc91e805f9d`）。

```python
# conanfile.py
def export_sources(self):
    copy(self, "*", src=os.path.join(self.recipe_folder, "vendor", "testsweeper-2024.05.31"),
         dst=os.path.join(self.export_sources_folder, "vendor", "testsweeper-2024.05.31"))

def generate(self):
    tc.variables["FETCHCONTENT_SOURCE_DIR_TESTSWEEPER"] = os.path.join(
        self.source_folder, "vendor", "testsweeper-2024.05.31")
```

实测：构建日志出现 `_deps/testsweeper-build` 直接由本地目录构建，无任何
Cloning/下载行。

## 边界与备选

- 变量名映射：declare 名小写 → 变量后缀大写（testsweeper → `…_TESTSWEEPER`）；
  上游 declare 多个外部项目时需逐个锚定。
- `-D FETCHCONTENT_FULLY_DISCONNECTED=ON` 是更宽的官方开关（要求所有依赖
  已就位），定向变量更可控；`add_subdirectory(vendor/…)` 补丁形态与上游
  CMakeLists 耦合，仅当该文件本就要打补丁时合并使用。

## 对下游的直接复用

lapackpp 2024.10.26 的 tester 同样 FetchContent testsweeper（同 tag）——
本条 + E667（BLAS_LIBRARIES 直通与链接序）是 lapackpp 配方的直接技术预置。
