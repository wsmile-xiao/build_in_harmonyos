# DRAFT-libgff-2.0.1：init-build 按 URL 猜测构建系统把 codeload 的 CMake 项目误判为 autotools

> 状态: 草稿（未审核、未合入正式知识库）
> 来源: libgff 2.0.1 (COMBINE-lab) 适配会话，task_id libgff-2.0.1-r01-bootstrap-and-adapt-pc2-16-20260922T115701Z
> 查重: knowledge/graph 无等价命中（E074/E097/E117/E281/E308 均不匹配）；与正式条目 E276/E483（codeload BadZipFile）为同一适配会话的不同问题。

## 问题描述

`ohc-run.py init-build` 对 codeload 官方 tag 归档 URL 初始化时，生成的
`.build-context` 把 `BUILD_SYSTEM` 判定为 `autotools`，`conan-init` 据此生成
Autotools 模板的 `conanfile.py`（`AutotoolsToolchain` / `Autotools`）。当项目
实际使用 CMake 构建（源码根目录只有 `CMakeLists.txt`、无 `configure` 脚本）时，
配方与构建系统不符，`conan create` / `conan-verify` 无法按配方自包含构建。

## 根因

`init_build._guess_build_system(url)` 仅按 URL 字符串关键字判断：
- 含 `cmake` → cmake
- 含 `mesonbuild` → meson
- 含 `openssl` / `python` → custom
- **其余一律默认 `autotools`**

`codeload.github.com/<owner>/<repo>/tar.gz/refs/tags/vX.Y.Z` 这类官方 tag 归档
URL 不含任何 cmake/meson 关键字，因此被默认误判为 autotools。URL 猜测只是启发式，
不能替代对实际源码构建系统的确认。

## 解决方案（可复用修复模式）

1. 在源码 work 目录确认实际构建系统：存在 `CMakeLists.txt` 且无 `configure` → CMake。
2. 用 `templates/conanfile-cmake.py.tmpl` 重写 `conanfile.py`：
   - `layout()` → `cmake_layout(self)`
   - `generate()` → `CMakeToolchain`，`tc.variables["BUILD_SHARED_LIBS"] = "OFF"`（R26）
   - `source()` → `get(self, **self.conan_data["sources"], strip_root=True)`
   - `build()` / `package()` → `CMake(self).configure()/build()/install()`
   - `package_info()` → `cpp_info.libs` 用上游 CMake 目标 basename（如 libgff 的
     `gff` 目标 → `libs = ["gff"]`，产物 `libgff.a`），并声明
     `cmake_file_name`/`cmake_target_name` 供 CMakeDeps 消费
     （`libgff::libgff`）。
3. 同步修正 `manifest.yaml`：`build_system: cmake`，配置选项补
   `-DBUILD_SHARED_LIBS=OFF`。
4. `test_package`：若模板默认是 C 项目而上游头文件是 C++（如 `gff.h`），
   须改为 `project(test_libgff CXX)` + `.cpp` 测试源；测试必须真实调用被测包
   API（R34），如 `GffReader` 解析真实 GFF3 输入并断言转录本 ID/数量。
5. 重新运行 `ohc-run.py conan-verify` 全门禁（G0-G4、L2/L4/L5）。

## 验证

libgff 2.0.1 实测：重写为 CMake 配方 + manifest `build_system: cmake` +
test_package 改 CXX 后：
- `conan-verify` G0-G4 / L2 / L4 / L5 全部通过；
- `conan create` 干净构建成功（`libgff.a` + `test_libgff`）；
- test_package 真实调用 `GffReader` 解析 GFF3 通过（断言 2 项）；
- W3 本地 CI 模拟 100% (1/1)，`.ci-result.json` exit_code=0。

## 适用边界

- 仅当 URL 猜测与实际源码构建系统不一致时适用；
- registry 已显式声明 `build_system`、或 URL 含 cmake/meson 关键字时不会误判；
- 纯 header-only 库走 headeronly 模板、数据包走 data-package 模式
  （E241/E281），不套用本模式。

## 反例 / 限制

- 含 `cmake` 关键字的 URL（如 cmake.org 托管）会正确判 cmake，无需重写；
- openssl / python URL 判 custom，属既有特殊分支；
- 本模式不改 URL（保持官方源 R39），只改配方模板与 manifest 声明。

## 关联条目

- 正式条目 E276 / E483：codeload tar.gz URL 无扩展名导致 `get()` BadZipFile，
  本适配会话在 `conandata.yml` 中显式声明 `filename` 修复（等价命中，路径 A）。
- 本草稿与 E276/E483 无冲突：前者是配方模板层问题，后者是下载解压层问题。