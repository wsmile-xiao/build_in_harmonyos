# draft-rdma-core-61.0-conan-libexecdir-bin-collision

## 症状

`conan create` 在 **package() 阶段**失败：

```
CMake Error at srp_daemon/cmake_install.cmake:82 (file):
  file INSTALL destination:
  /storage/.../.conan2/p/b/rdma-*/p/bin/srp_daemon
  is not a directory.
ERROR: rdma-core/61.0@ohpcd/stable: Error in package() method, line 102
	cmake.install()
	ConanException: Error 1 while executing
```

## 根因

1. **工具链默认值陷阱**：本仓库 OHOS conan 工具链生成的
   `conan_toolchain.cmake` 将 `CMAKE_INSTALL_LIBEXECDIR` 默认设为 `"bin"`
   （与 `CMAKE_INSTALL_BINDIR` 相同）——对按 GNU 惯例把 libexec 独立成目录的
   项目，这是一个隐藏的目录冲突源。
2. **同名文件/目录冲突**：rdma-core 的 srp_daemon 既安装可执行文件 `bin/srp_daemon`，
   又向 `${CMAKE_INSTALL_LIBEXECDIR}/srp_daemon`（展开 = `bin/srp_daemon/`）安装
   `start_on_all_ports` 脚本。文件先落地，目录后到达 → `file(INSTALL)` 拒绝
   "is not a directory"。

## 最小修复方案

在 conanfile.py 的 `generate()` 中显式覆盖该变量，恢复 libexec 语义：

```python
tc.variables["CMAKE_INSTALL_LIBEXECDIR"] = "libexec"
```

不修改上游 CMakeLists、不打补丁——这是纯配方层修复，对所有
CMake 安装目标含 `${CMAKE_INSTALL_LIBEXECDIR}/<子目录>` 的包通用。

## 验证

- 修复前：conan create package() FAIL（日志可溯，cmake_install.cmake:82）；
- 修复后：conan-verify G2 通过，test_package 三测试（L1/鸿蒙专项/消费者）实跑 PASS；
- staging 树出现独立 `libexec/` 目录，`bin/srp_daemon` 与 `libexec/srp_daemon/` 不再冲突。

## 适用范围 / 边界

- 适用：所有使用 conan CMakeToolchain 且 CMake 向 ${LIBEXECDIR}/<子目录> 安装
  内容、且子目录名与 bin 内可执行文件同名的项目（跨库可复用）；
- 边界：若上游代码运行期硬编码 libexec 绝对路径，需同时核对 CMAKE_INSTALL_LIBEXECDIR
  覆盖后的运行期查找行为；
- 与 E092 关系：同为 conan CMakeToolchain 注入变量的平台陷阱，本条目为 LIBEXECDIR 维度。
