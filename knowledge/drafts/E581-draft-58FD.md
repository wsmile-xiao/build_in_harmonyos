# E581 — conan test_package 构建环境 cmake 无法加载 libc++_shared.so

## 错误特征

conan create 主包构建成功后，test_package 的 `cmake.configure()` 以 Exit 127 失败：
```
Error loading shared library libc++_shared.so: (needed by /data/service/hnp/bin/cmake)
Error relocating /data/service/hnp/bin/cmake: _ZdlPv: symbol not found
Error relocating /data/service/hnp/bin/cmake: _Znwm: symbol not found
...
ERROR: whitedb/0.8.0alpha@ohpcd/stable (test package): Error in build() method, line 27
	cmake.configure()
	ConanException: Error 127 while executing
```

## 触发条件

- 构建系统: autotools/cmake 均可触发（被测包本身不限）
- 阶段: conan-verify G2 的 test_package 构建阶段
- 前提: test_package 使用 CMakeToolchain/CMakeDeps（模板默认），构建环境 cmake
  可执行文件依赖 `libc++_shared.so`，且该库位于 ohos-sdk 的
  `llvm/lib/aarch64-linux-ohos/` 子目录而非 `llvm/lib/` 根目录

## 根因分析

- `/data/service/hnp/bin/cmake` 是 OHOS SDK cmake（`readelf -d` 显示 NEEDED
  `libc++_shared.so`）；
- 该库只存在于 `ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos/`
  子目录，`llvm/lib/` 根目录没有；
- conan 构建环境由 profile buildenv 注入 `LD_LIBRARY_PATH` 指向
  `llvm/lib` 根目录（不含子目录），且该环境覆盖交互 shell 的系统加载路径
  → cmake 启动即动态链接失败；
- 交互 shell 下 cmake 能跑（`--version` 正常），因为系统加载路径能找到库，
  易误判为"cmake 没问题"。

## 解决方案

### 推荐方案（compiler-direct-compile）

test_package 不依赖 CMake，直接用 profile 编译器（clang）编译链接测试源：

```python
import os
from conan import ConanFile

class TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["whitedb"].package_folder
        self.run(f"${{CC:-clang}} ${{CFLAGS}} -I\"{pkg}/include\" -L\"{pkg}/lib\" "
                 f"-o \"{self.build_folder}/test_whitedb\" test.c -lwgdb -lm",
                 env="conanbuild")
        self.run(f"\"{self.build_folder}/test_whitedb\"", env="conanrun")
```

测试源文件仍需真实调用被测包 API（R34/PF3：禁止 print-only 空壳）。

### 回退方案（add-ld-library-path）

若必须保留 CMake（消费者需消费上游 CMake target），把
`llvm/lib/aarch64-linux-ohos` 加入构建环境 LD_LIBRARY_PATH。

### 禁止做法
- ❌ `os.environ["CC"]` / 裸 `cc`/`clang` 回退——脱离 Conan profile（R33），本地与 CI 工具链可能不一致
- ❌ print-only / skip / pass 空壳测试——违反 R34
- ❌ 把 "cmake 不可用" 误判为被测包构建失败而改主配方

## 验证证据

whitedb 0.8.0alpha（GitHub priitj/whitedb）实测：
- 首轮 conan-verify：主包 configure/make 通过，test_package 报
  `Error loading shared library libc++_shared.so`（Error 127）；
- `readelf -d /data/service/hnp/bin/cmake | grep NEEDED` 确认依赖
  libc++_shared.so；`find .../llvm/lib -name libc++_shared.so` 确认库在
  `aarch64-linux-ohos/` 子目录；
- test_package 改为 clang 直编（-lwgdb -lm）后 conan-verify G0-G5 全过，
  test 运行输出 `PASS: whitedb int/str field roundtrip OK`。

## 适用边界

- ✅ 适用：OHOS 上 test_package 模板（CMakeToolchain）遇到 cmake 动态链接失败
- ✅ 适用：纯 C 库（无复杂 CMake 目标消费需求）
- ❌ 不适用：必须消费上游 CMake target / 需要生成配置头的包（用回退方案）

## 与既有条目的关系

- **similar_to: E307**（Conan test_package 缺少 CMake 时使用 profile 编译器直编）
  - 重合点：都主张 test_package 用 profile 编译器直编绕开 CMake
  - 差异点：E307 是"目标机未安装 CMake / cmake not found"；E581 是"cmake 存在
    但依赖的 libc++_shared.so 在 conan 环境加载失败"（诊断方式不同：须查
    cmake NEEDED 与库路径，而非 PATH）
  - 新增价值：E581 补充了"cmake 存在但动态链接失败"这一诊断分支，并给出
    具体定位命令（readelf -d / find libc++_shared.so）
- **similar_to: E132**（OHOS SDK lld 依赖 libxml2.so.16）
  - 重合点：OHOS SDK 工具链二进制运行时依赖某 .so，LD_LIBRARY_PATH 未含正确路径
  - 差异点：E132 是 lld 链接器依赖 libxml2.so.16；E581 是 cmake 依赖
    libc++_shared.so，且库在更深的 aarch64-linux-ohos 子目录
  - 新增价值：E581 明确 test_package 场景下的规避路径（直编），而非仅修环境
- **similar_to: E520**（qsb 宿主工具需 LD_LIBRARY_PATH）
  - 重合点：都是"构建期运行工具动态链接失败（Error relocating ... symbol not found）"
    大类；都涉及构建期宿主工具加载共享库
  - 差异点：E520 是 Qt Shader Baker（qsb）加载 libQt6ShaderTools/libQt6Core，修复是
    build() 中注入 Qt lib 路径（LD_LIBRARY_PATH）；E581 是 cmake 加载 libc++_shared.so，
    主修是 test_package 改用编译器直编规避（无需改主配方构建环境）
  - 新增价值：E581 提供"工具存在但动态库在子目录找不到"时的直编规避路径，
    与 E520 的"注入 LD_LIBRARY_PATH"互为补充
