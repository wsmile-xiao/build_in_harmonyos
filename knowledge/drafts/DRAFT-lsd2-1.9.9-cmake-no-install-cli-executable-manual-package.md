# CMake 无 install 规则的 CLI 可执行文件：package() 手动拷贝到 bin/ + commands.json

- **草稿 ID**: DRAFT-lsd2-1.9.9-cmake-no-install-cli-executable-manual-package
- **来源**: lsd2 1.9.9（tothuhien/lsd2）HarmonyOS PC 适配
- **分类**: cmake / conan / packaging / application / cli
- **状态**: 本地草稿（随 lsd2 1.9.9 归档同 PR 提交，路径 B 知识库扩展）

## 问题 / 错误签名

- conan-init 默认按 URL 推导 build 系统（lsd2 被误判为 autotools），上游实际是 CMake。
- 上游 CMakeLists.txt 只有 `add_executable(lsd2 ...)`，**没有任何 install 规则**；
  照搬 `cmake.install()` 会静默打包 0 个文件 → G4/L5 产物门禁失败。
- 本包是 CLI 工具（非库），因此还需软件级 commands.json（R38）。

## 根因

上游只定义可执行目标、不写 `install(TARGETS/FILES ...)`；Conan 模板假定有 install()。
另外 build_system 被 URL 推导误导为 autotools，需改为 CMake 模板。

## 最小修复方案（在 archives/l/lsd2/1.9.9 范围内）

1. conanfile.py 改 CMake 模板：`USE_LSD2=OFF`（→ add_executable），`CMAKE_BUILD_PARALLEL_LEVEL=1`（R9）。
2. `package()`：`copy(self, "lsd2", build_folder, package_folder/bin)`——上游无 install()，
   直接拷二进制。
3. `package_info()`：`cpp_info.bindirs=["bin"]`。
4. `archives/l/lsd2/commands.json`：CLI 声明（type=tool，binary=true，version ref 对齐 1.9.9）。
5. `test_package/conanfile.py` test() 直跑已安装二进制（消费者验证）：`lsd2 -h` 版本横幅 +
   h1n1 示例 dating 运行并断言 rate/tMRCA 输出，非空壳。

## 验证结果

- `ohc-run.py conan-verify lsd2 1.9.9`：G1/G2/G3/G4 + L2/L4/L5 全 PASS。
- conan create 日志：`Packaged 1 file: lsd2` + test_package PASS（date dating run rate=0.00268625）。
- test_ohos（鸿蒙专项）：T1 ELF64 AArch64 / T2 musl / T3 .codesign / T4 无宿主路径 / T5 真实定年 → 全 PASS。
- commands.json 已暂存、进入 commit、出现在 PR 文件列表。

## 适用边界

- **适用**：上游 CMake 仅 add_executable、无 install 规则的 CLI/application 三方库；OHOS aarch64 + Conan 2。
- **不适用**：上游自带完整安装/export 的库；静态库（见 DRAFT-fusion：手动装配 include/ + .a）；
  header-only 库。
- **与 DRAFT-fusion 的差异（本草稿新增）**：Fusion 覆盖库型+include/需要头+静态库；
  本草稿覆盖 CLI 可执行文件型（bin/ + commands.json + 消费者直跑二进制），命令与产物布局不同。

## 反例 / 相互冲突

- 若库实际有 install() 规则却仍手动拷 bin/，会与标准安装重复；应先确认上游无 install() 再手动装配。
- commands.json 若仅存在于 worktree、未进 PR，属当前库交付失败（L4/R38）。

## 关系

- similar_to: DRAFT-fusion-1.3.3-cmake-no-install-rule-manual-package
- caused_by: (无)
- prerequisite_of: (无)
- conflicts_with: (无)