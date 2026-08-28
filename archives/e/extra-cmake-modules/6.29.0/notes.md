# 适配笔记 — extra-cmake-modules 6.29.0

## 任务
- task_id: extra-cmake-modules-6.29.0-r02-bootstrap-adapt-pc1-30-20260827-132300
- executor: pc1-30
- 分支: feat/extra-cmake-modules-6.29.0
- worktree: /storage/Users/currentUser/junshi_liu/worktrees/pc1-30-extra-cmake-modules-6.29.0
- HEAD: 7bc8f354aa9e3acff32965ba9eea8015ee810b3a（以本地 main 为基线创建）
- remote_authorization: none（未 commit/push/PR/Issue/远端 CI/Conan 远端写）

## 一、软件简介

ECM（Extra CMake Modules）是 KDE 提供的扩展 CMake 模块集合，为项目构建系统提供额外的
CMake 宏、工具链文件和 `find_package` 查找模块。纯 CMake 模块包（无编译二进制），
安装 .cmake/.py 脚本到 share/ECM/。

## 二、源码信息（核验）

- 软件名称：extra-cmake-modules
- 适配版本：6.29.0
- 官方来源：https://download.kde.org/stable/frameworks/6.29/extra-cmake-modules-6.29.0.tar.xz
  （302 -> 官方 mirrorbits 镜像）
- GitHub 官方 tag：v6.29.0（refs/tags/v6.29.0, object sha 2334cb6eab01afc7adaeb92179b0080ba54743e7）
- SHA-256（本轮实际下载计算）：`aaf2542edd5c5af9ea56a46468892d38a7978af65f0f3518379fa8ce66cad2b8`
- 下载字节数：339516
- 源码顶层：VERSION "6.29.0"（CMakeLists.txt set(VERSION ...)）
- 许可证：BSD-3-Clause

## 三、依赖与消费者

- 强制依赖：无（纯 CMake 模块包，project LANGUAGES NONE）
- 可选（测试/文档）：Qt5/Qt6、Python3、Sphinx、ReuseTool —— 非适配阻塞
- registry 发布状态：extra-cmake-modules/6.19.0 已发布（本地+远端 ohpcd）；
  别名 ecm/6.20.0、6.26.0、7.0.7 已发布。ECM 为已发布基础设施，非缺失依赖（L0i 无缺失项）。
- 消费者：仓库内 karchive/6.19、kcoreaddons/6.14、kdoctools/6.19、attica(6.18/6.28) 等
  通过 find_package(ECM) + requires("extra-cmake-modules/...") 消费。
- 任务列举的 kdnssd/knewstuff/libkdegames 在本仓库无归档，非 ECM 强制依赖。

## 四、适配内容

1. 新增 Conan 配方 `extra-cmake-modules/6.29.0`：package_type="build-scripts"（纯 CMake 模块包）。
2. `package_id()` 用 `self.info.clear()` 统一包 ID（无编译产物）。
3. `generate()` 设 `BUILD_TESTING=OFF`（上游测试可选、Qt 依赖；模块本体无运行时依赖）。
4. 采用 CMakeToolchain + CMakeDeps，clang-only 环境不依赖裸 `$CC/$CXX`（R33）。
5. `package()` 用 `cmake.install()` 安装到 share/ECM/。
6. `package_info()` 设 cmake_file_name=ECM，builddirs=share/ECM/cmake，供下游 find_package(ECM)。

## 五、编译与测试结果

- conan create（OHOS aarch64 clang 15, libc++）通过，test_package 构建+运行 ./test_ecm 退出码 0。
  - 成功复验 stdout SHA-256: `cfb861edcaf6e0c65babe420a277eb22cec41cbdff4c2211d94591e8a099266b`（W3 本地验证）
- 鸿蒙特有测试 tests/ohos-ecm-consumer/（真实消费者工程）：
  - 调用 ECM 实际模块 ECMFindModuleHelpers + ECMConfiguredInstall + ECMGenerateExportHeader + ECMFeatureSummary
  - ECMGenerateExportHeader 生成真实导出头 ohosconsumer_export.h
  - ctest 1/1 Passed；./ohos_ecm_test 退出码 0，输出 ECM_VERSION=6.29.0 PASSED
- 上游测试（BUILD_TESTING=ON 单独构建源码）：87 例中 77 通过、10 失败。
  10 例失败（ExecuteKDEModules/KDEFetchTranslations/KDEInstallDirsTest.vars_in_sync_*×4/
  ecm_add_tests×4）均因缺失 Qt5/Qt6（FindQt5CoreConfig 未找到、No Qt5 qmake），
  属环境前置缺失，非本包适配缺陷（与已发布 6.26.0/6.19.0 结论一致）。

## 六、OH 设备约束处理

- 临时目录：$TMPDIR（/tmp 只读，已用 $TMPDIR）
- HMDFS 软链接：未涉及（无软链接替换）
- ELF 签名：测试 ELF 在设备可直接运行（clang 生成，验证通过）
- clang-only：配方不依赖裸 $CC/$CXX（CMakeToolchain 提供）
- SELinux chmod：未触发
- syscall 排除：上游测试未涉及 setreuid/chroot，无需排除

## 七、路径 B 证据（r03-r05 补充）

### 7.1 真实首错（结构化证据，原始 stdout/stderr 的 SHA-256 留证）
- 命令: `conan create . --build=missing -pr:b default -pr:h default`
- cwd: `archives/e/extra-cmake-modules/6.29.0/`
- 退出码: 1
- 触发 profile: 默认 profile `compiler.libcxx=libstdc++11`（os=OHOS, clang 15）
- 错误签名（摘自真实失败 stdout/stderr 首错行，非完整日志）:
  ```
  -- Conan toolchain: Defining libcxx as C++ flags: -stdlib=libstdc++
  -- Check for working CXX compiler: <OHOS clang 工具链> - broken
  clang-15: error: invalid library name in argument '-stdlib=libstdc++'
  ```
- 原始失败完整 stdout/stderr SHA-256: `d82a6cba460067c682618f0bb26147fbf17e05f9442520f2caa2f17a3e8d3c67`
  （原始日志为本地构建产物，未提交进仓库；哈希可追溯真实复现）

### 7.2 根因
Conan profile 中 `compiler.libcxx=libstdc++11` 时，CMakeToolchain 生成的
`conan_toolchain.cmake` 注入 `-stdlib=libstdc++`；OHOS 工具链 clang 15 仅提供 libc++，
拒绝该 flag，导致编译器 TryCompile 失败（`Check for working CXX compiler ... broken`）。

### 7.3 修复
改用仓库预置 OHOS profile（`compiler.libcxx=libc++`）：
```bash
conan create . --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```
禁止在 recipe 内写死 `-stdlib=libstdc++`（R33）。

### 7.4 复验
- conan create（libc++ profile）exit 0，成功 stdout SHA-256 `cfb861edcaf6e0c65babe420a277eb22cec41cbdff4c2211d94591e8a099266b`。
- test_package `./test_ecm` 退出码 0。
- 鸿蒙特有测试 `tests/ohos-ecm-consumer/` ctest 1/1 Passed，`./ohos_ecm_test` exit 0。

### 7.5 查重结果
- `grep -rl 'stdlib=libstdc++|invalid library name'` 知识库：仅 DRAFT 草稿自身命中，无既有条目。
- E092（CMake 平台识别 unknown）→ 本库非阻塞 fallback，不适用。
- E140（CMAKE_SYSTEM_NAME=HarmonyOS 平台检测）→ 未触发，不适用。
- E130（libc++ 头 C++17 要求 nullptr_t）→ 无关。
- E191（链接阶段缺 libc++/libc++abi 库，方案 STATIC_LIBRARY 绕过）→ 最接近但为 configuration
  阶段 `-stdlib=libstdc++` flag 拒绝，E191 修复不能解决本错误，未覆盖。
- 其余 E082/E133/E189/E216/E238/E247/E306 → gnulib/musl头/qmake/CMakeDeps/链接等，均不适用。

### 7.6 新增知识草稿（配对，同 stem，关键字段一致）
- `knowledge/drafts/DRAFT-ecm629-stdlib-libstdcxx-invalid.kv`
  SHA-256: `d859670fda0789b276e10c76284fb7de72db71fe6ec4e8f51efaecddefec6170`
- `knowledge/drafts/DRAFT-ecm629-stdlib-libstdcxx-invalid.md`
  SHA-256: `b874b52d6906d713bd9757aff445e4ca1a331f62b44072a545bb0418654104f8`
- 关键字段（title/error_signature/root_cause/rec_approach/rec_description）两文件一致。

## 八、路径判定

主体路径 A（常规基础适配，ECM 有成熟构建方式 + 知识库/历史归档 6.19.0/6.26.0），
同时具备路径 B（知识库扩展）：本轮确认真实增量诊断知识
`-stdlib=libstdc++` invalid library name（OHOS clang 拒绝、Conan profile libcxx 误配），
新增配对草稿 DRAFT-ecm629-stdlib-libstdcxx-invalid.kv/.md（见 7.6）。

## 九、原子性审计

- 本轮实际修改仅限 `archives/e/extra-cmake-modules/6.29.0/`（conanfile.py、conandata.yml、
  manifest.yaml、notes.md、test_package/、tests/ohos-ecm-consumer/、reports/path-b-issue-pr-evidence-draft.md）
  与配对知识草稿 `knowledge/drafts/DRAFT-ecm629-stdlib-libstdcxx-invalid.kv/.md`。
- 未修改其他库、共享框架、上游测试断言或全局 Skill。
- 仓库中 archives/l/libXext/ 的 README.md/manifest.yaml 修改为 session 开始前已存在的
  环境状态（工作树创建时即携带，非本任务引入），不在允许范围，未触碰。
- remote_authorization: none：未 commit/push/创建 PR/Issue/远端 CI/Conan 远端写。

## 十、未完成项 / 唯一下一步

- 本轮为本地适配验证（status=built 对应本地验证通过）。
- 制品发布/PR 提交与知识草稿 promote 因 remote_authorization: none 未执行，
  交由分析端获得授权后处理。
