# miniscript 1.6.2：上游 CMake 仅 install(TARGETS) 未安装头文件 → 配方 package() 补装（草稿，预留条目 E543）

- **软件**：miniscript 1.6.2（https://github.com/JoeStrout/miniscript，MiniScript C++ 实现）
- **构建系统**：CMake（可执行 miniscript CLI + 静态库 libminiscript-cpp.a）
- **平台**：HarmonyOS PC / aarch64（`aarch64-unknown-linux-ohos`），编译器 clang 15.0.4
- **状态**：DRAFT（预留编号 E543）

## 现象

`conan create` 的 test_package 阶段 configure 失败（conan-verify G2 硬失败）：

```
CMake Error in CMakeLists.txt:
  Imported target "miniscript::miniscript" includes non-existent path
    "/storage/Users/currentUser/.conan2/p/b/minisb8fe9beee7435/p/include"
  in its INTERFACE_INCLUDE_DIRECTORIES.
  ...
  The installation package was faulty and references files it does not provide.
```

## 根因

上游 `CMakeLists.txt` 对 `miniscript-cpp` / `minicmd` 只写了：

```cmake
install(TARGETS miniscript-cpp minicmd)
```

**没有** `install(DIRECTORY ...)` 安装公开头文件。CMake 的 `install(TARGETS)` 对
`PUBLIC` include 目录只记录安装规则，不会自动复制头文件。于是 Conan `package()`
阶段产物目录（package_folder）只有 `lib/` 和 `bin/`，缺少 `include/`；而 CMakeDeps
生成的 imported target 仍声明 `INTERFACE_INCLUDE_DIRECTORIES` 指向
`package_folder/include`（不存在），test_package configure 阶段即报错。

## 修复

conanfile.py `package()` 中在 `cmake.install()` 之后补装公开头文件，并保持与上游
include 路径一致的目录结构（`#include <MiniScript/...>`）：

```python
from conan.tools.files import copy
import os

def package(self):
    cmake = CMake(self)
    cmake.install()
    copy(self, "*.h",
         src=os.path.join(self.source_folder, "MiniScript-cpp", "src", "MiniScript"),
         dst=os.path.join(self.package_folder, "include", "MiniScript"))
```

同时核对 `cpp_info.libs` 与上游 target 名一致（上游 target 为 `miniscript-cpp`，
不能沿用模板默认的 `miniscript`）。

## 验证

- 修复后 `conan-verify`：G0-G4 全 PASS；
- test_package 消费者测试通过公开 `MiniScript::Interpreter` API 运行脚本，
  校验 `print "answer is " + x` 输出 `answer is 42` 与全局变量 `x == 42`；
- W3 本地 CI（setup.sh + build_and_test.sh）通过，`.ci-result.json` exit_code=0。

## 适用边界 / 反例

- **适用**：上游 CMake 仅 `install(TARGETS ...)` 而未 `install(DIRECTORY ...)`
  头文件的 C/C++ 库，在 OHOS aarch64 + Conan 2 CMakeDeps 下 conan create 必现。
- **不适用**：上游已正确安装头文件（含 install(DIRECTORY ...) 或 EXPORT + install headers）
  的库；header-only INTERFACE 库（参见 E322，路径不同）。
- **反例**：用空目录/占位文件伪造 include 存在属禁止项（消费者仍无法编译）。

## 查重结论（本条目）

- 与 E322（header-only INTERFACE 配方）同属 CMake 配方打包域但场景不同：
  E322 解决"头文件已随上游 install/export 分发"的消费方式，本条解决"上游根本没安装头文件"。
- 与 E498（headerless 库清空 include）方向相反。
- 正式知识、图谱、草稿三范围查重均未命中本错误签名，判定为**新增知识候选**，
  路径 B（知识库扩展），`new_draft`。