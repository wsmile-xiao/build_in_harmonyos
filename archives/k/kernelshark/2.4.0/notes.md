# kernelshark 2.4.0 适配笔记（核心层 libkshark）

## 编译环境
- 构建系统: cmake（libkshark）+ makefile（vendored trace 三库）
- 编译日期: 2026-09-18
- 编译器: clang/clang++（/data/service/hnp/bin/clang, clang 15）
- 状态: built

## 交付范围（分层第一层）

| 层 | 依赖 | 本次 |
|---|------|------|
| libkshark 核心库 | libtraceevent + libtracefs + libtracecmd + json-c | 交付（libkshark.so + 头 + libkshark.pc + vendored 三库随包） |
| libkshark-plot | freeglut + GLU（仓内/制品仓均无） | 不构建（CMake 补丁双条件门控） |
| libkshark-gui / kernelshark / kshark-record | Qt6(Widgets/Network/OpenGLWidgets/StateMachine) + FreeSans 字体 + 依赖 plot 层 | 不构建（Qt 缺席时自然关闭；plot 层缺失为硬阻塞） |

## 依赖闭包决策（R36 证据）

libtraceevent 1.9.0 / libtracefs 1.8.3 在仓内 archives/l/ 只有 manifest
笔记归档（无 conanfile.py）；libtracecmd（trace-cmd 项目）仓内完全没有；
ohpcd 制品仓检索亦无。→ 参照
archives/a/address-standardizer/3.7.0（vendored PostgreSQL 18.3 bootstrap）
先例，三库官方源码（kernel.org tar.gz，SHA256 见 conandata.yml）在 recipe
构建期 vendored 编译并随包交付，构成 libkshark.so 的 DT_NEEDED 运行时闭包。

## 编译步骤（recipe 自动化，手工复核路径）

1. vendored libtraceevent 1.9.0：vendored trace-btf-compat.h + include 补丁 →
   `make -j1 libdir_relative=lib` → 手工 stage（设备无 /bin/install）
2. vendored libtracefs 1.8.3：vsock 头冲突补丁 → 同上（PKG_CONFIG_PATH 指向 stage）
3. vendored trace-cmd v3.3.3（libtracecmd 1.5.3）：快照不含
   lib/traceevent、lib/tracefs 子模块，Makefile 走 pkg-config 外部依赖；
   `make -j1 libs NO_VSOCK=1`
4. kernelshark 2.4.0：`cmake -DCMAKE_POLICY_VERSION_MINIMUM=3.5
   -DCMAKE_DISABLE_FIND_PACKAGE_OpenMP=TRUE -DCMAKE_PREFIX_PATH=<stage>
   -DJSONC_INCLUDE_DIR=<json-c include 父目录> ...` → `cmake --build` →
   `cmake --install`（绝对 DESTINATION 直接落 package 布局）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | OHOS btf.h 无 BTF_KIND_FLOAT/DECL_TAG/TYPE_TAG/ENUM64、struct btf_decl_tag/btf_enum64；musl 无 qsort_r | OHOS 内核 UAPI 头停在 DATASEC(15)，NR_BTF_KINDS 已是宏(=16) | vendored trace-btf-compat.h：#undef NR_BTF_KINDS 后重定义为 20、补 kinds 16-19 与结构体、qsort_r 宏模拟（qsort+thunk） |
| 2 | tracefs-vsock.c 的 linux/vm_sockets.h 连带 linux/socket.h 重定义 sockaddr_storage | OHOS SDK 头冲突 | 本地定义 AF_VSOCK(40)/VMADDR_CID_ANY/struct sockaddr_vm（对齐仓内 libtracefs 归档补丁，重制为计数正确的 diff；设备 /usr/bin/patch 对计数偏差的 hunk 会静默不应用，conan 2 纯 Python patcher 无此问题） |
| 3 | 上游 plot 层只按 OPENGL_FOUND 门控但链接 GLUT::GLUT/GLU | 上游 CMake 缺陷 | 补丁改双条件 OPENGL_FOUND AND GLUT_FOUND（examples/ 本来就是双条件） |
| 4 | 顶层 find_package(Qt6 ... REQUIRED) 在 Qt 缺席时配置失败 | 与上一行 Qt6Widgets 可选探测矛盾 | 补丁去 REQUIRED，GUI 层由 Qt6Widgets_FOUND AND TT_FONT_FILE 自然关闭 |
| 5 | cmake_minimum_required(3.1.2) 被本仓 CMake 拒绝 | CMake≥3.27 移除 <3.5 兼容 | -DCMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 6 | libkshark.h 用 <json-c/json.h>，上游 FindJSONC 返回 json-c 子目录 | FindJSONC PATH_SUFFIXES json.h 与 include 风格不匹配 | -DJSONC_INCLUDE_DIR=<json-c include 父目录>、-DJSONC_LIBRARY 显式指定 |
| 7 | libtraceevent/libtracefs .pc 默认 libdir=lib64 | Makefile libdir_relative 按 LP64 探测 | make 显式 libdir_relative=lib |
| 8 | make install 报 install: not found | /bin 不在构建 PATH 且 HNP 无 coreutils install | 全部手工 stage（conan copy + os.symlink），cmake install 用 cmake 内建拷贝 |
| 9 | install() 期 bash ldconfig | 上游 Linux-ism | 补丁删除该 install(CODE) 块 |
| 10 | find_package(OpenMP) 命中 SDK libomp，但 OHOS 运行时无 libomp.so | 运行时库不可部署 | -DCMAKE_DISABLE_FIND_PACKAGE_OpenMP=TRUE |
| 11 | libtraceevent 插件目录烧入 staging 绝对路径 | PLUGIN_DIR 编译期宏 | 随包交付 lib/traceevent/plugins，运行期 TRACEEVENT_PLUGIN_DIR 覆盖 |
| 12 | 首轮 CI test_package 探针 FAIL: kshark_export_all_filters 返回 NULL | kshark_export_all_filters → kshark_export_all_event_filters → kshark_get_data_stream() 要求 stream->interface 非空；kshark_add_stream() 的裸流没有 interface（libkshark.c:364），打开真实 tep 数据前在所有平台（含 Linux）都返回 NULL——上游 examples/configio.c 对该返回值不检查，属"看起来能用" | 探针改用公共 API kshark_filter_config_new + kshark_export_filter_array / kshark_import_filter_array（直接操作 hash 过滤器，不经流查找），round-trip 断言不变（清空后从 conf.json 反序列化校验 314/42） |
| 13 | 二轮 CI L5a：libkshark.so 缺 DT_SONAME（上游明明设了 SOVERSION 2） | profile os=OHOS → OHOS 适配版 conan 生成 CMAKE_SYSTEM_NAME=HarmonyOS，HNP CMake 4.1.2 未带 Platform/HarmonyOS.cmake → CMAKE_SHARED_LIBRARY_SONAME_C_FLAG 未定义 → set_target_properties(SOVERSION/VERSION) 被静默忽略（链接命令无 -Wl,-soname，输出名退化为 libkshark.so 且无版本符号链接） | 仓内 attica/attica5/expat 已验证模式：CMakeToolchain tc.variables 显式给 CMAKE_SHARED_LIBRARY_SONAME_[C|CXX]_FLAG="-Wl,-soname," + CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE（单文件 libkshark.so，DT_SONAME=libkshark.so，与 vendored 三库的 DT_NEEDED 解析路径一致） |

## 运行时验证（真机）

- 首轮权威 CI（2026-09-18，build_and_test.sh，CI_PACKAGES=archives/k/kernelshark/2.4.0）：
  vendored 三库 + libkshark 构建与打包全部成功，test_package 编译链接成功，
  探针在 kshark_export_all_filters 断言失败（问题 #12，上游 API 契约）。
- 二轮 CI：探针重写后 L1/test_package 通过（conf.json 真实落盘+读回 round-trip，
  kshark_hash_id_clear 清空后 import，pid 314/42 与 "Hello Kernel" 逐项断言，
  L1e 破坏性反向验证确认真实依赖），L5a SONAME 门禁暴露问题 #13 后按仓内
  模式修复。三轮日志：run tmp/ci-full-{1,2,3}.log。

## 产物

- lib/libkshark.so（DT_SONAME=libkshark.so，单文件；见问题 #13——HarmonyOS 平台模块缺失致 SOVERSION 失效，按仓内 attica/expat 模式显式 soname + 关闭版本化链接）
- lib/libtracecmd.so.1.5.3 / libtracefs.so.1.8.3 / libtraceevent.so.1.9.0（vendored，含 .so/.so.1 符号链接）
- lib/traceevent/plugins/plugin_*.so（13 个）
- include/kernelshark/*.h（4 个公共头）+ include/trace-cmd|tracefs|traceevent（vendored 头）
- lib/pkgconfig/libkshark.pc

## 注意事项

- DT_NEEDED: libkshark.so → libtracecmd.so.1/libtracefs.so.1/libtraceevent.so.1/libjson-c.so.5(+libc)；libtracecmd → libz.so（/system/lib64/ndk）
- GUI/plot 层后续迭代需先解决 freeglut/GLU（GUI 依赖 plot 层）与 FreeSans 字体（TT_FONT_FILE），Qt6 侧 qtbase/6.11.1.2 + qtscxml/6.11.1 制品仓已有
- zlib 压缩支持由 trace-cmd Makefile 自动探测（SDK sysroot），zstd 未探测到（正常，无 libzstd.pc）
- kshark_export_all_filters/kshark_import_all_filters 等流级 API 需要 stream->interface（打开真实 tep 数据后才有）；无数据文件的消费方应使用 kshark_export_filter_array/kshark_import_filter_array（见问题 #12）
