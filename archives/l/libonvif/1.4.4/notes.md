# libonvif 1.4.4 适配笔记

## 任务信息
- 任务号: 8317（开源鸿蒙PC专项积分赛-依赖）
- 分支: feat/libonvif-1.4.4（worktree ~/qzy/GLM-55-libonvif-1.4.4）
- 适配路径: 路径 A（依赖适配）；无跨仓库新知识增量，不走路径 B（判断依据见下）

## 路径 B 判断（2026-09-19，构建后复核）
- 判断依据：本次仅常规 CMake 配方适配（libxml2 依赖注入 + 工具链旗标保全 + 安装目录归一化），所遇问题均为知识库已有模式（CMAKE_CXX_FLAGS 覆盖、RPATH 处理）或单库特定的上游写法，不构成可跨仓库复用的新知识；知识库查重未发现需新增条目（CMake set(CMAKE_CXX_FLAGS) 覆盖场景已在既有经验范围）。判定：纯路径 A。

## 编译环境
- 构建系统: cmake（上游顶层 CMakeLists，cmake_minimum_required 3.17）
- 编译日期: 2026-09-19
- 编译器: clang/clang++ 15（OHOS 工具链，conan profile ohos-aarch64）
- 状态: built（conan-verify W3 通过后更新）

## W0 依赖检查
- libxml2: 上游 libonvif/CMakeLists.txt `find_package(LibXml2 REQUIRED)`，配方锁定 libxml2/2.15.3.1；`conan download libxml2/2.15.3.1 -r=ohpcd` 实测二进制存在（OHOS/armv8 shared=True）。
- Iconv: 上游 `find_package(Iconv REQUIRED)` 仅在 `if(WIN32)` 分支内，OHOS 不触发，无需注入。
- 其余: 无外部依赖。BUILD_GUI=OFF（默认未开）时 libavio/onvif-gui（Qt/ffmpeg）不参与构建。

## W0b 历史经验
- 归档无 libonvif 历史版本，无历史 notes 可迁移。
- 语言预检 lang-preflight: detected_language=cpp（91% C++），与任务语言兼容族，通过。

## 上游测试清点（五维账本）
- N_static = 0：上游 v1.4.4 tarball 全树核对（`find . -iname "*test*"` 零命中，无 tests/ 目录，顶层与子目录 CMakeLists 均无 add_test()/enable_testing()），上游无自动化测试资产。
- N_registered = 0；N_executed = 0（无可执行项，非"有而不跑"）。
- N_consumer = 1：test_package/test_onvif_api.c（编译链接 onvif 库 + libxml2 头传播，调用 getUUID/prefix2mask/mask2prefix/initializeSession/closeSession/clearData，10 处断言，退出码即结果）。
- 消费者测试断言取自源码实现核对：prefix2mask(24)=255.255.255.0 与 prefix2mask(16)=255.255.0.0 按 htonl 位运算实现；mask2prefix 逐位右移计数；clearData 对 token/name/width/frame_rate 显式清零（onvif.c 2682-2741 行）。

## 编译步骤
1. conan create（conan-verify G2）：source() 从官方 tarball（codeload 主源 + github 备源，sha256 01b0311f885967d679f979d278aca1b203eabf478ffc3c75af4a43cd638a1444）。
2. build() 内 replace_in_file：顶层 CMakeLists 的 `set(CMAKE_CXX_FLAGS "-D_FORTIFY_SOURCE=2 ...")` 改为等价 `add_compile_options(...)` —— 原写法整体覆盖 Conan 工具链注入的 CMAKE_CXX_FLAGS（丢失 -stdlib=libc++ 等），硬化旗标本身逐字保留。
3. cmake configure + build（-DBUILD_GUI=OFF，CMAKE_SKIP_INSTALL_RPATH=ON，musl 忽略 DT_RUNPATH 且 cmake --install 的 RPATH 改写可能产出 OHOS 加载器拒收的 ELF）。
4. package()：cmake.install() 后把 include/<arch>/onvif.h 归一化到 include/（上游 CMAKE_INSTALL_INCLUDEDIR=include/${CMAKE_LIBRARY_ARCHITECTURE}）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | onvif-util（C++）可能丢失工具链旗标 | 上游 set(CMAKE_CXX_FLAGS ...) 覆盖 Conan 注入 | 改为 add_compile_options 等价形式（旗标逐字保留） |
| 2 | onvif.h 安装进 include/<arch>/ 子目录 | 上游 CMAKE_INSTALL_INCLUDEDIR 含 CMAKE_LIBRARY_ARCHITECTURE | package() 内归一化到 include/ |
| 3 | 公共头 onvif.h 不自带 libxml2 include | 上游头文件只 include stdbool/time，但 API 签名用 xmlDocPtr 等 | 消费端先包含 libxml 头；test_package 显式 find_package(libxml2) 并链接 LibXml2::LibXml2（CMakeDeps 按 libxml2 配方声明的目标名） |
| 4 | test_package 编译报 libxml/tree.h not found | CMakeDeps 对 libonvif→libxml2 依赖边按 LINK_ONLY 生成，不传播头文件路径 | test_package 直接链接 LibXml2::LibXml2 取得 include 路径 |

## 源码修改
- 无 patches/ 文件；build() 内 replace_in_file 一处（CMakeLists.txt 顶层旗标行，sources-only 变更，理由与验证见上表 #1）。

## 依赖版本
- libxml2/2.15.3.1（ohpcd 制品仓已发布，binary 实测存在）

## 验证结果
```bash
python3 scripts/ohc-run.py conan-verify libonvif 1.4.4
# G1/G2/G3/G4 + L2/L4/L5 通过后回填：conan create 退出码、消费者测试 10/10 断言通过
```

## 交付物
- libonvif.so（SOVERSION 1，shared）
- bin/onvif-util（ONVIF 摄像头命令行工具，commands.json 已声明）
- include/onvif.h（唯一公共头）

## 注意事项
- 上游 v1.4.4 tag 的 GitHub 归档与 codeload 归档 sha256 一致（01b0311f...），conandata.yml 双官方源。
- onvif-util 运行需网络摄像头环境，消费者测试仅覆盖离线可断言 API；真机 hicmd 验证后 commands.json binary 字段再置 true。
---

**编译结束**: 2026-09-19 02:40
**最终状态**: built
