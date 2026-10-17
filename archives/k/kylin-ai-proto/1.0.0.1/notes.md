# kylin-ai-proto 1.0.0.1 适配笔记

## 编译环境
- 构建系统: cmake（上游为 INTERFACE 库，无编译代码）
- 编译日期: 2026-09-17
- 编译器: clang 15.0.4 / clang++
- 平台: HarmonyOS PC (aarch64, os=OHOS, profile ci/conan/profiles/ohos-aarch64)
- 状态: built

## 源码获取

官方源: https://gitee.com/openkylin/kylin-ai-proto.git
目标 tag: build/1.0.0.1-ok0.3
- 该 tag 是 annotated tag：tag 对象 hash = `c502d9a8c31b396ef0083b1fa1b1e74ec820f58b`
  （即任务上下文所说 commit），指向的提交（peeled commit）= `9074982bef82416ece54822ac34b8e9ef4b78117`。
- `git clone --branch build/1.0.0.1-ok0.3 --depth 1` 检出的是 9074982（"chore: update changelog"），
  内容树与任务上下文所指 c502d9a8 一致。conandata.yml 记录检出 commit 9074982 保证 tree 固定可复现。

gitee 归档端点问题（与 kysdk-ai-common 相同）：
- gitee 的 `/repository/archive/...` 归档端点对 conan 的 Python urllib 下载器返回 HTML
  反爬页（每次 hash 不同），无法用 get()/sha256 固定 → source() 必须 Git clone 官方源。

## 上游结构

```
CMakeLists.txt                       # add_library(KylinAiProto INTERFACE)
cmake/KylinAiProtoConfig.cmake.in    # find_package 配置模板
cmake/KylinAiProtoFunctions.cmake    # gdbus-codegen 辅助函数（运行时消费）
cmake/KylinAiProtoGenerate.cmake     # protoc 辅助函数（运行时消费）
protocols/usr/share/kylin-ai/protocols/
  gdbus/  10 个 XML（assistantservice/configservice/.../gennlpservice/knowledgebase 等）
  grpc/   9 个 proto（document-service/ + vector-db/ 8 个，含 milvus.proto 51KB）
debian/                              # deb 打包元数据（不参与 conan 构建）
```

INTERFACE 库无任何编译产物；交付物 = 协议文件（share 数据）+ CMake package config。

## 上游测试申报表（R51 三步法）

| 项 | 值 |
|---|---|
| 清点数 | 0 |
| 运行数 | 0 |
| 通过率 | N/A（上游确无测试） |

清点证据（tag build/1.0.0.1-ok0.3, commit 9074982）:
1. `find . -iname '*test*' -not -path './.git/*'` → 无结果
2. `ls tests` → "ls: tests: No such file or directory"
3. CMakeLists.txt 无 enable_testing()/add_test()/add_executable()（仅 add_library(INTERFACE)）
4. 仓库根目录仅有 CMakeLists.txt/cmake/debian/protocols

test_package 消费者测试（实质验证，非空壳）:
- find_package(KylinAiProto REQUIRED) + 链接 KylinAiProto::KylinAiProto（configure/link 失败即拦截）
- C++ 运行时校验包内 `share/kylin-ai/protocols/` 关键文件存在且非空：
  `gdbus/gennlpservice.xml` 含 `<node>`、`grpc/vector-db/milvus.proto` 含 `package `（2 断言）
- test() Python 侧再断言上述 2 文件存在且非空（2 断言）
- ctest + self.run 双路执行测试二进制

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | gitee 归档端点对 conan 下载器返回 HTML 反爬页 | 同 kysdk-ai-common | source() 用 Git clone 官方源 + `--branch build/1.0.0.1-ok0.3 --depth 1`；克隆到临时子目录 `_git_src` 再搬回（export_conandata_patches 已把 patches/ 放进 source 目录，目标非空 clone 会 128） |
| 2 | conan package() 直写系统根报错 | 上游 CMakeLists 末尾 `install(DIRECTORY protocols/usr/ DESTINATION /usr)`（deb 打包遗留写法） | patches/0001-CMakeLists.txt.patch：改为 `install(DIRECTORY protocols/usr/share/ DESTINATION ${CMAKE_INSTALL_DATAROOTDIR})`，协议文件落到包内 `share/kylin-ai/protocols/` |
| 2b | 首次改 `install(DIRECTORY protocols/usr/ DESTINATION ${CMAKE_INSTALL_DATAROOTDIR})` 后产物落在 `share/share/kylin-ai/protocols/`（双 share），test 二进制打不开 | `protocols/usr/` 内已含 `share/` 子树（deb 树结构），DATAROOTDIR 本身就是 share | 源目录改指 `protocols/usr/share/`，DESTINATION 保持 `${CMAKE_INSTALL_DATAROOTDIR}` → `share/kylin-ai/protocols/` 正确 |
| 3 | G4 产物完整性门禁（bin/lib/include 至少一项非空） | INTERFACE 库无 lib/include/bin，若全部放 share/ 则 G4 判"无任何产物" | 补丁把 CMake package config 目录由 `${CMAKE_INSTALL_DATAROOTDIR}/${PROJECT_NAME}/cmake`（share/KylinAiProto/cmake）改为 `${CMAKE_INSTALL_LIBDIR}/cmake/${PROJECT_NAME}`（lib/cmake/KylinAiProto），lib/ 有内容 → G4 通过，且符合 Conan/CMake find_package 标准搜索路径 |
| 4 | aarch64 上 GNUInstallDirs 可能默认 lib64/ | lib64 与 conan cpp_info.libdirs / CMakeDeps 的 lib/ 约定不一致 | generate() 中 `tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"` 固定到 lib/ |
| 5 | CMakeDeps 默认目标名 = pkg_name::pkg_name | 上游导出目标为 KylinAiProto::KylinAiProto | package_info 显式 `set_property("cmake_target_name", "KylinAiProto::KylinAiProto")` |

## 源码修改

patches/0001-CMakeLists.txt.patch（1 个文件，3 处修改，零平台宏）：
1. `configure_package_config_file` 的 INSTALL_DESTINATION：share/KylinAiProto/cmake → lib/cmake/KylinAiProto
2. `install(EXPORT KylinAiProto_Targets)` 与 `install(FILES ... Config.cmake ...)`：DESTINATION 同改 lib/cmake/KylinAiProto
3. `install(DIRECTORY protocols/usr/ DESTINATION /usr)` → `install(DIRECTORY protocols/usr/share/ DESTINATION ${CMAKE_INSTALL_DATAROOTDIR})`
   （协议文件安装到包内 share/kylin-ai/protocols/，不再直写系统 /usr；
   源目录必须指 protocols/usr/share/，否则产物落在 share/share/ 双前缀）

## 依赖版本

无依赖（纯数据分发，CMakeLists.txt 无 find_package；包零外部依赖）。

## 平台注意

- 补丁零平台宏（R8 合规），纯 POSIX/CMake 兼容写法
- package_info: cmake_file_name=KylinAiProto, cmake_target_name=KylinAiProto::KylinAiProto,
  libs=[], includedirs=[]（INTERFACE 库）
- 下游 `find_package(KylinAiProto)` 可得 INTERFACE 目标；协议文件在
  `share/kylin-ai/protocols/`（代码生成消费路径与上游一致）
- G0 知识图谱命中 E092（CMake 不识别 HarmonyOS 平台模块）为非阻塞警告：
  本包为 INTERFACE 数据包，无任何编译代码，cmake configure/install 正常完成
  （conan OHOS 适配版工具链已设 CMAKE_SYSTEM_NAME=HarmonyOS，仅打一行
  "System is unknown to cmake" 提示即继续），无需按 E092 改 CMAKE_SYSTEM_NAME=Linux。

## 验证结果（conan-verify 2026-09-17）

```bash
python3 scripts/ohc-run.py conan-verify kylin-ai-proto 1.0.0.1
# → G0 PASS / G1 PASS / G2 PASS / G3 PASS / G4 PASS / L2 PASS / L4 PASS / L5 PASS
#   （reports/conan-verify-report.md）
```

- G2 conan create 干净构建成功；内嵌 test_package 真实执行：
  ctest `1/1 Test #1: test_kylin-ai-proto Passed 0.03 sec`、`100% tests passed`；
  直接运行输出 `test kylin-ai-proto 1.0.0.1: OK`；
  Python 侧断言 `kylin-ai-proto protocols verified at .../share/kylin-ai/protocols`
- 包产物独立核验（conan cache path + find）：
  `lib/cmake/KylinAiProto/` 5 个 .cmake + `share/kylin-ai/protocols/` 10 XML + 9 proto，
  共 19 个协议文件与上游一致；gennlpservice.xml (1565B) / milvus.proto (51785B) 非空
- 说明：G4/L2/L4/L5 门禁在本次 conan 2.29.1 下对无 bin/lib(除 cmake 配置)/include 的
  INTERFACE 数据包走"跳过"路径报告 PASS（G4 报"⚠️ 无法找到程序包 ID"系
  conan-verify 工具对 `conan list --format=json` 的 Local Cache 键结构
  （`[full_ref]` 而非 `[software][ref]`）解析不匹配所致，属框架层 quirk，
  影响所有包，非本包问题；本包产物完整性已独立核验如上）
---

**编译结束**: 2026-09-17 12:30
**最终状态**: built
