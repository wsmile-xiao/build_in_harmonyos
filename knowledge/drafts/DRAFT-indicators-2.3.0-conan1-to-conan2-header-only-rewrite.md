# DRAFT — 上游自带 Conan 1.x 配方向 Conan 2.x 重写：header-only 库的可复用边界

> 状态: 草稿（基于 indicators 2.3.0 R01/R02 真实证据，待查重/提升）。
> 依据: SKILL §6 归档规范 + 铁律 R39（官方源）+ E017（ghfast 镜像）/ E221（消费者契约）。

## 真实问题（场景）

indicators 2.3.0（p-ranav/indicators，Activity Indicators for Modern C++）上游自带
**Conan 1.x 配方** `conanfile.py`：

```python
from conans import CMake, ConanFile, tools   # ← Conan 1.x 导入路径
...
def set_version(self):
    m = re.search(r"project\(.*VERSION ([0-9a-zA-Z.-]+)[ )]",
                  open(os.path.join(self.recipe_folder, "CMakeLists.txt")).read())
    self.version = m.group(1)
```

本项目 CI 使用 **OHOS 适配版 Conan 2.29.1**，`from conans import ...` 直接语法不兼容，
配方无法原样运行。同时项目的 Conan 2 体系要求：`layout()`（cmake_layout）、
`package_type = "header-library"`、`CMakeToolchain` 注入 OHOS 目标平台
（CMAKE_SYSTEM_NAME=Linux / CMAKE_SYSTEM_PROCESSOR=aarch64）、`CMakeDeps` 生成
`find_package(indicators)` / `indicators::indicators` imported target。

## 根因

1. **Conan 1.x/2.x API 断裂**：`from conans import`（1.x）vs `from conan import`（2.x）；
   1.x 的 `tools.get_env` / `self._configure_cmake()` 模式在 2.x 无对应物。
2. **版本标识不来自配方**：上游用 `set_version()` 正则从 `CMakeLists.txt` 的
   `project(indicators VERSION 2.3.0 ...)` 提取版本——重写后必须显式 `version = "2.3.0"`，
   且与任务版本、`archives/i/indicators/2.3.0/` 目录名三方一致（CI L0m 校验）。
3. **header-only 语义**：库无编译产物，`package()` 只做 CMake install（头 + cmake config
   + pkgconfig），必须声明 `package_type = "header-library"` 且 `cpp_info.libs = []`，
   否则 CMakeDeps 会对不存在的库文件生成空/错误 target（E221 同族陷阱）。
4. **源码获取沿用官方 URL + SHA-256 硬校验**：`conandata.yml` 保持官方
   `https://github.com/p-ranav/indicators/archive/refs/tags/v2.3.tar.gz`（R39 官方源），
   SHA-256 `70da7a693ff...`（本机实测与 FreeBSD ports 归档逐字节一致，双源交叉确认）。
   本环境 `github.com:443` 不可达时按 E017 机制临时注入 ghfast.top 官方镜像，
   conan `get()` 用 SHA-256 硬校验内容，镜像只是传输通道，源码逐字节一致。

## 方案（重写边界）

1. **导入与骨架**：`from conan import ConanFile`；`from conan.tools.files import get,
   apply_conandata_patches, export_conandata_patches`；`from conan.tools.cmake import
   CMake, CMakeToolchain, cmake_layout`。
2. **配方字段**：`name="indicators"`、`version="2.3.0"`、`license="MIT"`、
   `package_type="header-library"`、`settings="os","compiler","build_type","arch"`
   （R32：OHOS 需四件套）。
3. **layout/source/generate**：`cmake_layout(self)`；`get(self, **self.conan_data["sources"],
   strip_root=True)`（conandata 保持官方 URL+sha256）；`generate()` 内当
   `settings.os in ("Linux","OHOS")` 时注入 CMAKE_SYSTEM_NAME=Linux、
   CMAKE_SYSTEM_PROCESSOR=aarch64，`tc.generate()`。
4. **build/package**：CMake configure（默认关闭 INDICATORS_DEMO/SAMPLES）+ install；
   安装物为 `include/indicators/*.hpp`（16 头）+ indicatorsConfig/cmake + indicators.pc。
5. **package_info**：`cpp_info.set_property("cmake_file_name","indicators")`、
   `set_property("cmake_target_name","indicators::indicators")`、`cpp_info.libs=[]`。
6. **消费者验证（test_package）**：`find_package(indicators REQUIRED)` +
   `target_link_libraries(test PRIVATE indicators::indicators)`，源码真实调用
   `ProgressBar{option::BarWidth, option::Stream, ...}`、`set_progress(100)`、
   `is_completed()`、`IndeterminateProgressBar`；`option::Stream` 避免污染终端。

## 验证（indicators 2.3.0 实测）

```bash
# conan create（OHOS aarch64 profile）+ test_package
conan create archives/i/indicators/2.3.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# → Package 6b129b068851896169fae42d399fa922d239ce8a created
# → test_package: [.<==>.....] PASS: indicators header-only 库链接和核心 API 验证通过 (exit 0)

# conan-verify 八门禁（G0-G4 + L2/L4/L5）
python3 scripts/ohc-run.py conan-verify indicators 2.3.0 --profile ohos-aarch64
# → G1/G0/G2/G3/G4 PASS; 配方验证通过，可标记 published

# 产物架构核验（OHOS aarch64）
file <build>/test_indicators   # → ELF shared object, 64-bit LSB arm64

# W3 本地 CI（prdiff junk_check）
zsh ci/conan/build_and_test.sh archives/i/indicators/2.3.0
# → JC_RESULT=pass Junk Files 0; conan create passed; Pass rate 100.0% (1/1)
```

## 适用边界

- **适用**：上游自带 Conan 1.x 配方、header-only / INTERFACE 库、无编译期依赖、
  CMake 构建、官方 tag tarball 有稳定 SHA-256 的库（同类：any-lite 重写先例）。
- **适用平台**：OHOS aarch64 / Linux；CMakeToolchain OS 注入逻辑复用。
- **不适用**：源码包内无 CMake 工程；有编译产物且与系统同名库冲突（R26 静态策略）；
  上游无 tag/release（须 source_provenance_unavailable 停）；多依赖链库。

## 局限

- 本环境 `github.com:443` 不可达：conan create/W3 需 E017 ghfast.top 镜像注入，
  验证后必须恢复官方 URL（conandata 最终保持官方源，R39）。
- 上游无独立 CTest 套件（INDICATORS_BUILD_TESTS 为孤立声明）时，质量验证责任
  完全落在 test_package 消费者——不得虚报上游测试数。
- `set_version()` 正则提取版本仅适用于 CMake `project(... VERSION ...)` 形式；
  其他构建系统需等价处理，否则版本号失去单一事实源。

## 引用证据（可追溯）

- conanfile.py: `archives/i/indicators/2.3.0/conanfile.py`（Conan 2.x 重写版）
- conandata.yml: `archives/i/indicators/2.3.0/conandata.yml`（官方 URL + sha256 70da7a69...）
- conan create 日志: `archives/i/indicators/2.3.0/reports/conan-create.log`
- conan-verify 报告: `archives/i/indicators/2.3.0/reports/conan-verify-report.md`
- W3 日志: `archives/i/indicators/2.3.0/reports/w3-local-ci.log`
- 上游原始 1.x 配方: `p-ranav/indicators v2.3` 仓库根 `conanfile.py`
- R01/R02 结果: `indicators-result-r01-bootstrap.json` / `indicators-result-r02-formal-adapt.json`