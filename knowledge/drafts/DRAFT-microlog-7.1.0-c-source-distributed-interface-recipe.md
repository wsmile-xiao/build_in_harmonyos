# DRAFT-microlog-7.1.0-c-source-distributed-interface-recipe

> **Contributor**: AtomCode | **Status**: VERIFIED DRAFT | **Updated**: 2026-09-23
> **Source event**: microlog 7.1.0 HarmonyOS PC 适配（task microlog-7.1.0-r01-pc4-42-20260922T193355Z）

## 知识类型与提升边界

本条目是路径 B 知识库扩展候选，不预占正式 E 编号。它只进入 `knowledge/drafts/**`，
不修改 `knowledge/graph/`、`knowledge/doc/`、索引或运维规则，也不声称已经 promote。
是否提升及最终分类由知识库维护者和评审决定。配对文件：同 stem 的 `.kv`。

## 适用场景

适用于同时满足以下条件的 C 库：

- 上游是 CMake `INTERFACE` 库，但 install 不仅装头文件，还**把 `.c` 源文件装入
  `share/<lib>/src/`**，并由包内手写/导出的 `micrologTargets.cmake` 在**消费方**重新定义
  STATIC target（`target_sources(PRIVATE 已装 .c)` + `target_include_directories(PUBLIC include)`）；
- 特性宏（如 `ULOG_BUILD_EXTRA_OUTPUTS` / `ULOG_BUILD_TOPICS_MODE` / `ULOG_BUILD_TIME`）
  须在**编译期由消费者配置**，默认配置下部分公开 API（自定义输出/主题）为禁用态；
- 目标为 OHOS aarch64 真机或 CI，消费者通过 `find_package(<lib> CONFIG)` 获 `<lib>::<lib>` target。

典型家族：rxi/log.c 系（microlog/ulog、各类 log.c fork）、stb 风格单文件 C 库。

## 问题模型

三类容易误判的处理方式：

1. 套用 header-only 配方（`package_type="header-library"` + `self.info.clear()`，E321/E322）——
   源码分发库有消费方编译语义，`.c` 源参与编译，不是纯头文件；
2. 套用常规库配方假设有预编译 `.a`/`.so` 并填 `cpp_info.libs` —— 该模式无预编译产物，
   伪造 libs 会让下游链接失败；
3. 消费者测试在**默认配置**下断言自定义输出/主题 API 可用 —— 特性宏未启用时
   `ulog_output_add`/`ulog_topic_add` 返回 `INVALID`（`WARN: 'ulog_output_add' called
   with ULOG_BUILD_EXTRA_OUTPUTS disabled`），必须按上游语义在编译期补 `-D` 宏。

## 推荐方案

### 1. conanfile.py（CMake 配方，非 autotools 模板）

```python
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches

class MicrologConan(ConanFile):
    name = "microlog"; version = "7.1.0"; license = "MIT"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}; default_options = {"shared": False}

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["ULOG_BUILD_TESTS"] = False   # 上游单测单独执行
        tc.generate()

    def build(self):
        cmake = CMake(self); cmake.configure(); cmake.build()

    def package(self):
        cmake = CMake(self); cmake.install()       # 原样装 include + share/src + lib/cmake

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "microlog")
        self.cpp_info.set_property("cmake_target_name", "microlog::microlog")
        self.cpp_info.set_property("cmake_find_mode", "none")   # 用包自带 config
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.builddirs = ["lib/cmake/microlog"]        # 透传自带 config 目录
```

### 2. conandata.yml 官方 URL

源码 URL 必须带 `.tar.gz` 扩展名（`https://github.com/<owner>/<repo>/archive/refs/tags/v<ver>.tar.gz`）。
codeload 的 `tar.gz/refs/tags/<tag>` 形式 basename 无扩展名 → `conan get()` 误按 zip 解压 →
`BadZipFile: File is not a zip file`（与 E276 同根因；换官方 archive URL 或给 `get()` 传
`filename=` 均可）。SHA-256 以官方 tarball 实测为准。

### 3. 消费者测试（test_package / test_ohos）

- `find_package(microlog CONFIG REQUIRED)` + `target_link_libraries(... microlog::microlog)`
  （自带 targets 会在消费方编译已装 `ulog.c`）；
- 特性宏在消费方编译期配置（与上游 tests/unit 相同的基础配置）：
  `-DULOG_BUILD_EXTRA_OUTPUTS=8 -DULOG_BUILD_TIME=1 -DULOG_BUILD_PREFIX_SIZE=16
  -DULOG_BUILD_TOPICS_MODE=ULOG_BUILD_TOPICS_MODE_STATIC -DULOG_BUILD_TOPICS_STATIC_NUM=8`；
- 断言可观察输出（stdout 捕获 / 文件输出 / handler 计数），禁止空壳；
- 文件输出测试用显式可写路径，勿依赖 `tmpfile()`（OHOS /tmp 只读且 libc 不遵循 TMPDIR，
  见既有 E002/E265/E272 体系）。

### 4. 测试双口径台账

上游 `tmpfile()` 类失败如实计入分母（`reports/upstream-test-ledger.md`），不修改上游测试源码。

## 注意事项

- 不要用 `package_type="header-library"` 处理源码分发库；也不要伪造 `cpp_info.libs`。
- `cmake_find_mode="none"` 时 CMakeDeps 不生成 config，消费方必须经 `builddirs`
  指向包自带 `lib/cmake/<lib>`（E451 与 DRAFT-E322 为消费方目标名桥接知识，本条目为打包侧模式）。
- 上游测试临时目录失败要按恢复规则逐候选目录实测后归类（HMDFS 2771 非 0700 不合格；
  /dev/shm 真实 tmpfs 但 libc `tmpfile()` 仍失败时如实记平台阻塞）。

## 已验证示例

microlog 7.1.0（官方 tag v7.1.0，SHA-256 `fd8aa1e9...4063b`）。OHOS aarch64：
conan-verify G1/G0/G2/G3/G4 + L2/L4/L5 全过（conan create 干净构建）；test_package 1/1 通过
（stdout 捕获断言）；test_ohos T1 aarch64 ELF / T2 无宿主路径泄漏（-ffile-prefix-map）/
T3 消费者编译链接运行（主题路由 + 文件输出 + 级别字符串 + ulog_event_to_cstr）全过；
上游测试双口径 113/119 (95.0%)，4 失败用例全为 `tmpfile()` 平台限制。

复现入口：

```sh
CI_PACKAGES="archives/m/microlog/7.1.0" zsh ci/conan/build_and_test.sh
python3 scripts/ohc-run.py conan-verify microlog 7.1.0
sh archives/m/microlog/7.1.0/test_ohos/run_ohos_test.sh
```

## 证据来源

- `archives/m/microlog/7.1.0/conanfile.py`
- `archives/m/microlog/7.1.0/conandata.yml`
- `archives/m/microlog/7.1.0/test_package/`
- `archives/m/microlog/7.1.0/test_ohos/`
- `archives/m/microlog/7.1.0/reports/upstream-test-ledger.md`
- `archives/m/microlog/7.1.0/knowledge-candidate-ledger.md`
