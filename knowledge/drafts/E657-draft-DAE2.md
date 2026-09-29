# E657 — OHOS conan 沙箱中不兼容 libc++_shared.so 遮蔽导致宿主工具符号重定位失败，前置 /system/lib64 修复

## 错误特征

```
Error relocating /data/service/hnp/bin/cmake: _ZNKSt4__n119__shared_weak_count13__get_deleterERKSt9type_info: symbol not found
Error loading shared library libc++_shared.so: (needed by /data/service/hnp/bin/cmake)
```

或 ECM/KDEInstallDirs 在 configure 期运行 qtbase 的 `qtpaths` 宿主工具时报同样 libc++ 符号重定位错误。

## 触发条件

- OHOS (arm64) 平台，Conan 构建沙箱。
- 配方 `generate()`/`build()` 把各依赖包的 `lib/` 目录 prepend 进 `LD_LIBRARY_PATH`。
- 依赖链中存在与宿主二进制 ABI 不兼容的 `libc++_shared.so`，且该路径位于 `/system/lib64` 之前，遮蔽了兼容版本。
- 宿主 C++ 工具（`/data/service/hnp/bin/cmake`、qtbase 的 qtpaths）被触发执行 → 加载错 libc++ → 符号重定位失败 → configure 直接失败。

## 根因

OHOS conan 沙箱把依赖注入路径放在 `LD_LIBRARY_PATH` 前端，而沙箱/依赖目录里的 `libc++_shared.so` 与宿主工具编译时链接的 libc++ ABI 不一致。加载器按 `LD_LIBRARY_PATH` 顺序优先解析到不兼容版本，宿主工具 `_ZNSt4__n1*`（libc++ 命名空间）符号全部 "symbol not found"。

## 解决方案

对 OHOS 分支，在配方 `build()`/`test()` 使用的 `Environment` 中 **prepend `LD_LIBRARY_PATH=/system/lib64`**，使加载器优先解析系统兼容 libc++：

```python
def _library_runtime_env(self):
    env = Environment()
    for dep in self.dependencies.values():
        if dep and dep.package_folder:
            env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
    for rel in ("bin", "lib", os.path.join("src", "lib")):
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
    if self.settings.os == "OHOS":
        env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
    env.define("QT_QPA_PLATFORM", "offscreen")
    return env
```

- `build()` 阶段：`with self._library_runtime_env(include_build=True).vars(self).apply(): cmake.configure(); cmake.build()`
- `test()` 阶段（test_package 的 build/test 同样需要，因为其 `cmake.configure()` 也会运行宿主 cmake：`_libcxx_env()` prepend `/system/lib64`，build 与 test 均应用）。

回退方案：test_package 中再叠加 SDK LLVM lib 目录
`/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib`（存在时 prepend），与 `/system/lib64` 并用。

## 验证

- `ksyntaxhighlighting 6.26.0`：`conan create archives/k/ksyntaxhighlighting/6.26.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable` → G2 PASS，上游 CTest 6/6 通过，test_package PASS。
- 修复前后对照：未加 `/system/lib64` 时 configure 报 `Error relocating /data/service/hnp/bin/cmake: _ZNKSt4__n119__shared_weak_count... symbol not found`；加上后 configure 正常执行。

## 适用边界

- **适用**：OHOS conan 沙箱中运行宿主 C++ 工具的 CMake/ECM 工程（KF6 系列、Qt 系库）；配方依赖注入经历了 `LD_LIBRARY_PATH` prepend 的场景。
- **不适用**：非 OHOS 平台；无宿主工具触发的纯编译链路（无 configure 期宿主二进制运行）；依赖注入不涉及 `LD_LIBRARY_PATH` prepend 的配方。

## 关联条目

- `similar_to: E538`（统一 C++17/libc++ profile 后依赖图选项不一致，同为 libc++/profile 相关但根因不同）。
- 同模式先例：kconfig/kcrash/kio/kxmlgui 6.26.0、ksanecore 26.04.0（note 中记录的 `/system/lib64` 前置修复），均为 KF6 系列包。

## 不适用/禁止

- 禁止删除 `libc++_shared.so` 或 `unset LD_LIBRARY_PATH` 绕过：影响沙箱依赖链自身解析，破坏并发任务。
- 禁止把修复写死为 `== Linux`（R32：OHOS 判断须 `in ("Linux", "OHOS")`）。