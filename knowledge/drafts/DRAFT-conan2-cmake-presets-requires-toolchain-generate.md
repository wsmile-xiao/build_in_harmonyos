# Conan 2.x 中 cmake_layout 只定义目录布局、不产出 CMakePresets.json，CMake(self) 构建前必须在 generate() 显式 CMakeToolchain().generate()；OHOS 目标按 E092 设 CMAKE_SYSTEM_NAME=Linux（首报案例：kicad-library-symbols 10.0.5）

- **草稿 ID**: DRAFT-conan2-cmake-presets-requires-toolchain-generate
- **来源**: kicad-library-symbols 10.0.5 HarmonyOS PC 适配（权威 CI attempt3 真实失败 → 修复后全绿）
- **分类**: conan / cmake / build-system / toolchain / packaging
- **状态**: 本地草稿（B 类知识库贡献候选，随本 run 单提交交付）

## 问题 / 错误签名

`conan create` 进入 build() 即失败，报错固定出现在 CMake 帮助类初始化：

```
ERROR: kicad-library-symbols/10.0.5: Error in build() method, line 71
	cmake = CMake(self)
ConanException: CMakePresets.json was not found in
	/storage/.../.conan2/p/b/<pkg-hash>/b/build/Release/generators folder.
	Check that you are using CMakeToolchain as generator to ensure its
	correct initialization.
```

真实失败证据（本 run 权威 CI attempt3 日志 165-170 行）：
`/storage/Users/currentUser/tmp/oh-device-porting-v2/kicad-library-symbols-10.0.5-ci-attempt3.log:165-170`。
日志旁证：整个构建记录中**不存在 `Calling generate()` 阶段**（只有 `Calling export_sources()/source()/build()`），即 conan 从未运行任何 generator。

## 根因（机理叙事）

Conan 2.x 的配方执行管线是三段式：`layout()` → `generate()` → `build()`，三段职责互不替代：

1. **`cmake_layout(self)` 只算目录，不产文件。** 它依据 `settings.build_type` 等把 build 目录定为 `build/<build_type>`、generators 目录定为 `build/<build_type>/generators`，并把这些路径挂到 `conanfile.folders` 上。它不生成任何工具链、preset 或依赖文件。
2. **`CMakePresets.json` 由 `CMakeToolchain` 在 generate() 阶段产出。** `CMakeToolchain(self).generate()` 才会把 `conan_toolchain.cmake` 与 `CMakePresets.json` 写进 generators 目录（CMakeDeps 等其他 generator 同理，各自在 generate() 阶段写自己的产物）。
3. **conan 2.x 不隐式补生成。** 配方既没写 `generate()` 方法、也没写 `generators` 属性时，generate 阶段什么都不产出（日志缺 `Calling generate()` 即此状态）；随后 `build()` 里 `CMake(self)` 初始化时按约定到 `<build>/Release/generators` 找 `CMakePresets.json`，找不到即抛 `ConanException`。

一句话：`layout` 解决"文件放哪"，`generate` 解决"工具链从哪来"。把 `cmake_layout` 误当成"完整 CMake 集成"是本类失败的共同语义错位——`cmake_layout` 与 `CMake` 帮助类齐备、唯独缺 `CMakeToolchain().generate()`，构建必然在 `CMake(self)` 处崩。

## 推荐解法（rec）：generate() 显式 CMakeToolchain + OHOS 平台守卫

```python
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout

    def layout(self):
        cmake_layout(self)

    def generate(self):
        toolchain = CMakeToolchain(self)
        # CMake 没有 OHOS 平台模块（见 E092）：显式对齐平台语义
        if self.settings.os in ("Linux", "OHOS"):
            toolchain.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            toolchain.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8"
                else str(self.settings.arch)
            )
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
```

要点：

- `generate()` 中必须**调用** `toolchain.generate()`，只实例化不调用等于没写。
- OHOS 目标按 **E092** 的平台语义处理：CMake 无 `Platform/HarmonyOS.cmake`，故 `CMAKE_SYSTEM_NAME=Linux`；conan settings 的 `armv8` 即 64 位 ARM，CMake 侧名称为 `aarch64`，需做映射。平台守卫只是本条 rec 的一个细节，平台语义本体由 E092 承载，不另立条。
- 对 `project(... NONE)` 的纯数据安装工程与 POSIX 纯库，该平台对齐无副作用；平台集成类项目（systemd/dbus/X11 等 Linux 专有逻辑）需按 E092 的边界另行评估。

## fallback（退路，诚实权衡）

若环境暂时无法走 `generate()`（如受限的旧 conan 包装层），可在 `build()` 绕开 CMake 帮助类，`self.run` 直接调系统 cmake 并手传平台变量：

```python
    def build(self):
        self.run("cmake -S . -B build -DCMAKE_BUILD_TYPE=Release "
                 "-DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=aarch64")
        self.run("cmake --build build")
```

**权衡**：此路失去 conan 工具链与依赖集成——conanbuild 环境、profile conf（编译器路径等）、CMakeDeps 依赖路径均不再自动注入，跨 profile 可复现性丧失。仅作临时退路，不得作为常规方案沉淀。

## 禁止模式：预置/提交生成物 CMakePresets.json 充数

```python
# ❌ 错误：把生成物 CMakePresets.json 塞进 export_sources/仓库来"喂饱"存在性检查
```

- **原因**：`CMakePresets.json` 是 `CMakeToolchain` 按具体包 ID 构建目录（`.conan2/p/<pkg>/<package_id>/b/.../generators`）生成的文件，预置副本与真实路径必然失配；且它掩盖 `generate()`/`CMakeToolchain` 缺失这一根因。
- **后果**：本机某次构建侥幸通过，换版本、换 profile、换缓存路径后 `CMake(self)` 再次崩溃；预置文件里的编译器/平台变量脱离 conan profile 管理，丧失可复现性，并构成生成物入库的审计问题。检出正则见 kv `forbid_1_pattern`（`(^|/)CMakePresets\.json$`）。

## 先例证据（配方树同模式实践，不含本次案例）

配方树中"`generate()` 显式调用 `CMakeToolchain`"已是主流实践，以下计数命令与数字均可现场复验（2026-09-18，run worktree 根目录执行）：

- `grep -rln --include=conanfile.py CMakeToolchain archives | xargs grep -l 'def generate' | wc -l` → **2254** 处配方使用 generate()+CMakeToolchain 模式；
- 其中带 OHOS 平台守卫（`CMAKE_SYSTEM_NAME` + armv8/aarch64 映射）的约 **144** 处；
- 可抽查的确切路径：`archives/a/adlplug/1.0.2/conanfile.py`、`archives/a/apitrace/14.0/conanfile.py`（均为此模式）。

## 验证

- **真实失败**：kicad-library-symbols 10.0.5 权威 CI attempt3 在 `CMake(self)` 处抛 `CMakePresets.json was not found`（证据路径见"问题"节）。
- **修复后**：补 `generate()`+`CMakeToolchain`（含 OHOS 守卫）后，权威 CI attempt5 全门禁通过（L0/L1 pass，JC prdiff 9 文件 pass，Build Summary Success 1/1），日志：`/storage/Users/currentUser/tmp/oh-device-porting-v2/kicad-library-symbols-10.0.5-ci-attempt5.log`；日志中可见 `Calling generate()` → `CMakeToolchain generated: .../CMakePresets.json` → `Calling build()` 的完整链路。
- **独立复现探针**：kv `verification_cmd` 字段的自包含二步脚本——STEP1 无 `generate()` 复现 `CMakePresets.json was not found`（exit 非 0），STEP2 加 `generate()` 后 exit=0；任意 conan 2.x + CMake 环境可执行，不依赖任何日志路径。

## 去重与审计

- **CMakePresets 语义查重**：`grep -ri CMakePresets knowledge/` 实测（2026-09-18）共 **1 处**命中——`knowledge/drafts/DRAFT-libical3-pkgconfig-consumer-chain.md:75`，语境为 pkgconfig 消费链草稿顺带提及 `--preset` 下游用法，与本条"缺 `generate()` 导致 CMakePresets 缺失"的机理**无语义重叠**，不构成重复条目（Curator 预审时 0 命中的判定与此处 1 命中差异即该附带提及，不影响 A+B 结论）。
- **E092 已覆盖平台守卫语义**（CMake 不识别 HarmonyOS 平台 / 平台名语义），故本条不另立平台条目，OHOS 守卫仅作为 rec 细节收录并显式链回 E092。
- **E526**（conan 配方工具语义族，如 apply_conandata_patches strip 语义）与本条同属"conan 2.x 帮助类默认行为语义错位"家族，`similar_to` 关联。

## 适用范围

- 任何使用 conan 2.x CMake 帮助类（`CMake`/`CMakeConfigure`/`CMakeBuild` 等）且配方缺 `generate()` 的项目；
- 数据型 CMake 安装工程（`project(... NONE)`）与普通编译型工程同样受影响——失败与源码语言无关，纯粹是生成管线缺段。

## 非适用边界

- 已有 `generators = "CMakeToolchain"` 属性写法的配方：属性写法同样会在 generate 阶段产出工具链，不属于本条失败面（但显式 `generate()` 方法是可注入 cache_variables 的更通用形态）；
- 因 conandata/source 阶段失败导致未达 build() 的构建，报错面不同，勿套用本条；
- 平台集成类项目在 OHOS 上的 `CMAKE_SYSTEM_NAME=Linux` 风险边界见 E092，本条不重复承载。

## 关联原则

- **P-TOOLCHAIN-001**（工具链受管纪律）：构建所用工具链必须来自受控来源并显式声明（鸿蒙 SDK 仅 LLVM/Clang 一族；conan 场景即由 CMakeToolchain 统一生成），不允许绕开或伪造工具链生成环节——本条禁止预置 CMakePresets.json 充数即是该纪律在 conan 2.x 生成管线上的投影。

## 相似条目

- **E092**（CMake 不识别 HarmonyOS 平台）：平台名语义与守卫来源，本条 rec 的 OHOS 分支依其语义实现；
- **E526**（conan 2.x 配方工具默认语义族）：同属 conan 帮助类默认行为与开发者预期错位的机理家族。
