# E088 扩展草稿：Conan 原生模块进入 HAP 后的 SDK C++ 运行库装载契约

## 错误特征

Boulder 1.02 在 OHOS 真机上 Conan create / test_package 通过，生成的 HAP 安装成功且 ArkUI 首页可显示，但调用游戏原生模块时失败：

```text
load libc++_shared.so failed, namespace=ndk no inherits, errno=2
load libc++_shared.so failed, namespace=moduleNs_default, errno=2
Error loading shared library libc++_shared.so: (needed by .../libboulderhost.so)
```

这是已发生的失败，不是人为推演。`archives/b/boulder-game/1.02/reports/hap-runtime-evidence.md` 保存来源与修复前后证据。

## 触发条件与根因

- OHOS/HarmonyOS aarch64；Conan 在 shell/HiShell 环境构建和测试 C++ 模块，DevEco 将预编译模块集成进 ArkUI HAP。
- 原生模块依赖动态 SDK C++ 运行库，HAP 只复制了业务模块，遗漏 libc++_shared.so。
- shell/Conan 与应用运行时的动态链接命名空间不同。系统目录存在同名库，不代表当前应用命名空间有权搜索并装载该文件。这里日志是 namespace + ENOENT，而不是编译链接失败、缺符号或签名 Permission denied。
- 探索工程由 DevEco 编译时可自动带入运行库，但从 Conan 预编译工程交付时只复制业务模块，不会自动继承探索工程的依赖打包行为。只重测 shell 下的测试程序无法发现这个缺口。

## 与已有知识的关系

本草稿明确作为 **E088 的应用打包场景扩展候选**，不宣称首次发现 OHOS namespace 或发明“复制库到私有目录”。

| 条目 | 已有范围 | 本次新增范围 |
|---|---|---|
| E088 | Python/lib-dynload 的外部库可见性，将依赖复制到模块目录并签名 | Conan 预编译模块→ArkUI HAP 的交付边界，实际编译器定位 SDK 运行库、目标 ABI 私有打包与 NOTICE、最终 HAP 产物同源核验 |
| E073 | HMDFS .so 符号链接装载异常 | 本例为 HAP 缺运行库与 namespace 可见性，不是符号链接修复 |
| E474 | 原生消费者与辅助观察者结果的区分 | 采用真实消费者验证原则；新增的是具体依赖遗漏的定位和打包过程，不重复申请“必须真机验证”原则 |
| E489 | CTest 前构建树 ELF 加载对象的签名 | 本例处理应用交付包中的遗漏运行库，未改系统安全策略或构建树签名机制 |
| Curtain E429-draft-9C4B | GUI 原生宿主与行为核心迁移模式 | 本例不把新建 ArkUI 宿主本身作为新增知识 |

正式编号/合并方向由知识库维护者决定。查重快照、官方 draft-review 结果另附报告；相似度建议不等于 B 复审通过。

## 推荐方案

1. 先确定实际加载者是 shell 程序还是 HAP 内的 NAPI 模块，保留错误发生时的 hilog 与模块名称。不能只看 Conan 测试是否通过。
2. 使用匹配 SDK 的 `llvm-readelf -d` 检查模块 NEEDED，列出实际缺失依赖；解压最终 HAP 检查 `libs/arm64-v8a`。这里只对确认缺失且允许随应用分发的 SDK libc++ 处理，不盲目复制系统框架库。
3. 从实际 CMake C++ 编译器查询 libc++_shared.so；有 target 时传递 target；要求命令成功、返回绝对存在路径，否则构建失败，不能静默省略运行库。
4. 把该运行库安装到 Conan 包提供的 ArkUI 工程的 `entry/libs/arm64-v8a`。保留 SDK native/NOTICE.txt；业务模块与运行库 ABI/架构/SDK 必须兼容，不使用另一个机器/SDK 的同名文件凑数。
5. 消费者自动测试检查原生模块、运行库和 NOTICE，同时执行真实资源解码/地图读写；这只覆盖包内检查，不代替图形应用运行。
6. 从该 Conan 包内工程重新构建签名 HAP，核查最终归档含三个运行所需库，安装并调用原生功能；测试进入/退出页面的生命周期和输入。
7. DevEco 可能 strip 原生库，完整文件哈希变化不能单独判断来源不一致。保存构建复制链，并比对 ELF 的 SHF_ALLOC 节名称、类型、虚拟地址、大小与内容。Boulder 本例三个库 23/23/24 个分配节全部相同；这用于核对载入内容，不证明所有可能的 ABI 兼容性。

## 实现片段（来自本次已验证配方）

```cmake
set(_runtime_query "${CMAKE_CXX_COMPILER}")
if(CMAKE_CXX_COMPILER_TARGET)
  list(APPEND _runtime_query "--target=${CMAKE_CXX_COMPILER_TARGET}")
endif()
execute_process(COMMAND ${_runtime_query} -print-file-name=libc++_shared.so
  OUTPUT_VARIABLE BOULDER_CXX_RUNTIME OUTPUT_STRIP_TRAILING_WHITESPACE
  RESULT_VARIABLE _runtime_result)
if(NOT _runtime_result EQUAL 0 OR NOT IS_ABSOLUTE "${BOULDER_CXX_RUNTIME}" OR NOT EXISTS "${BOULDER_CXX_RUNTIME}")
  message(FATAL_ERROR "The OHOS compiler did not provide libc++_shared.so")
endif()
install(FILES "${BOULDER_CXX_RUNTIME}"
  DESTINATION share/boulder/harmony-project/entry/libs/arm64-v8a)
```

NOTICE 定位采用本例 SDK 布局：真实 compiler 的 `bin/../..` 为 native 根目录，必须存在 NOTICE.txt；其他 SDK 布局要显式适配，不能假定此相对目录永远有效。

## 验证步骤与结果

```sh
# 原生模块实际依赖
llvm-readelf -d libboulderhost.so
# 应包含 NEEDED libc++_shared.so；此检查不代表装载已成功。

# 构建 HAP 后查看实际归档，而不是仅查看项目目录。
python3 -c 'import zipfile; z=zipfile.ZipFile("entry-default-signed.hap"); print("\n".join(n for n in z.namelist() if n.endswith(".so")))'
# 本例应有 libboulderhost.so、libeditorhost.so、libc++_shared.so。

hdc install -r entry-default-signed.hap
hdc shell aa start -a EntryAbility -b com.kasumizawamiyuu.boulderhost
# 进入游戏，Enter 启动关卡，Right 移动；回首页→编辑器→首页→游戏。
```

2026-09-20 真实成品：菜单、关卡、角色移动、编辑器显示及同进程往返通过；此前保存的地图仍能读取。新增 CTest 3/3 和消费者测试 1/1 通过；上游没有自动测试套件，不把新增测试称为上游用例。先前用户已确认音乐可听见，本次没有再次声称完成听感测试。

## 适用范围和禁止做法

适用于以 Conan 预编译 C++ 模块交付 ArkUI/HAP、模块确实需要动态 SDK C++ 运行库的同类项目。本例实证仅为 Boulder 的游戏/编辑器两个模块、aarch64、SDK 26.0.0.18，不宣称第二个独立项目已验证或支持全部 SDK/ABI。

- 不复制全部 NEEDED 库，系统框架库与可再分发 SDK 运行库要区分。
- 不替换系统 libc++，不修改设备 namespace 配置，不关闭权限校验。
- 不通过设置 shell LD_LIBRARY_PATH 来宣称应用命名空间问题已解决。
- 若是 undefined symbol、ABI 不一致或签名错误，另行诊断；本方法不是所有 dlopen 错误的通用补丁。
- 当前代码显式打包已确认依赖，不是自动分析任意 ELF 依赖图的工具。
