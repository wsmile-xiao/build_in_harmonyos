# libkcompactdisc 25.12.1 适配笔记

## 编译环境
- 构建系统: cmake（ECM 6.26 / CMake ≥ 3.16，Conan CMakeToolchain + Ninja→Make）
- 编译日期: 2026-09-24
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang，OHOS sysroot 26.0.0.18）
- 状态: published（conan-verify 8 门禁全绿：G0-G4 + L2/L4/L5）

## 编译步骤

```bash
conan create archives/l/libkcompactdisc/25.12.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

配方要点（同 karchive/solid/ki18n/phonon4qt6 的 KDE 包模式）：
- `KF_IGNORE_PLATFORM_CHECK=TRUE` 绕过 KDE 平台检测（OHOS 不在 KDE 平台列表）；
- E092：注入 `CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG="-Wl,-soname,"`（CMAKE_SYSTEM_NAME=HarmonyOS 无 CMake 平台模块，SONAME flag 缺失）；
- qtbase/solid/ki18n/phonon4qt6 均 `cmake_find_mode=none`，手工生成 `conan_cmakedeps_paths.cmake`（PREPEND 各依赖 package_folder 的 lib/cmake、lib、include）+ `CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON`；
- ECM_MODULE_PATH 手工指向 ecm 包的 share/ECM/{modules,find-modules,kde-modules}；
- ki18n 包内已打补丁的 KF6I18nMacros（Gettext QUIET + msgfmt 缺失走 python fallback）保证 `ki18n_install(po)` 可用；
- alsa-lib CMakeDeps 生成 `ALSA::ALSA`，src/CMakeLists 的 find_package(ALSA) 命中（音量控制启用）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Could NOT find Qt6DBus`：Qt6Config 置 Qt6_FOUND=FALSE | 本仓发布的 qtbase/6.11.1 以 `FEATURE_dbus=OFF` 构建，Qt6DBus 平台级不可用（solid 配方同因 USE_DBUS=OFF） | 适配补丁把 DBus 改为可选特性 `WITH_QTDBUS`（默认 ON 保持上游语义），配方设 OFF；唯一 DBus 消费点 urlToDevice 的 mediamanager 查询回退为原始设备路径 |
| 2 | `CMake Error: failed to create symbolic link '../bin/libKCompactDisc6.so.5': Permission denied`（cmake_symlink_library，100% 复现） | **conan(python3) 进程树的所有后代进程都被 HMDFS/SELinux 拒绝 symlink()**（实测 os.symlink、self.run ln、subprocess ln 全部 EPERM，而交互 shell 后代的 ln/cmake 均成功——进程标签继承所致，E018/E050 新根因）；带 VERSION/SOVERSION 的目标其 Makefile 规则 `$(CMAKE_COMMAND) -E cmake_symlink_library` 必然执行 symlink() | 适配补丁去掉 set_target_properties 的 VERSION/SOVERSION（触发符号链接步骤的开关），保留 E092 注入的 `-Wl,-soname,` 使 DT_SONAME=libKCompactDisc6.so；产物为单一未版本化文件，运行期 DT_NEEDED 直接命中包内实体文件 |
| 3 | `LINKER:SHELL:-soname,...` 产生 `ld.lld: error: unknown argument '-soname,KCompactDisc6.so.5'` | OHOS clang-15 驱动对 `-Wl,a,b` 不拆分逗号，原样透传单个 token 给 ld.lld | 放弃 target_link_options 自定义 soname，统一走 E092 注入的 CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG 机制（link.txt 中 `-Wl,-soname,libKCompactDisc6.so` 形式验证可用） |
| 4 | 同一目录"刚写入文件→立即建符号链接"疑为竞态 | 经 cmake -E create_symlink + dd 5/5 通过验证排除，实为问题 2 的进程标签因素 | 见问题 2 方案 |

## 源码修改（3 个补丁，均在 OHOS 下应用，无平台宏，平台中性）

| 补丁 | 内容 | 类型 |
|------|------|------|
| 0001-CMakeLists.txt.patch | `find_package(Qt6 ... COMPONENTS Core DBus)` 拆分：Core 必选，DBus 由 `option(WITH_QTDBUS)`（默认 ON）控制，置 `HAVE_QTDBUS` | feature（平台中性可选特性） |
| 0002-src-CMakeLists.txt.patch | Qt::DBus 链接与 `target_compile_definitions(KCompactDisc PRIVATE HAVE_QTDBUS)` 条件化；移除 VERSION/SOVERSION 属性（HMDFS 符号链接限制，见问题 2/3） | feature + 平台适配 |
| 0003-src-kcompactdisc.cpp.patch | `QDBusInterface/QDBusReply` 包含与 mediamanager DBus 调用用 `#ifdef HAVE_QTDBUS` 守卫，无 DBus 时回退 `deviceUrl.path()`（与无效回复路径一致） | feature |

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| qtbase | 6.11.1 | Qt6Core（Qt6DBus 平台未发布，已可选化） |
| solid | 6.26.0 | KF6 设备枚举（光驱发现） |
| ki18n | 6.26.0 | KF6I18n（po 翻译安装） |
| phonon4qt6 | 4.12.0 | 音频后端（REQUIRED，≥4.8.0） |
| alsa-lib | 1.2.16.1 | ALSA 音量控制（可选，已启用） |
| ecm | 6.26.0 | tool_requires，KDE 构建模块 |

## 验证结果

```bash
# G2 conan create（test_package 消费者测试）
1/1 Test #1: test_kcompactdisc ................   Passed    0.14 sec
100% tests passed, 0 tests failed out of 1

# 上游 testkcd 手动程序真实构建+运行（R51 三步法，aarch64 真机）
#   moc(qtbase libexec) + clang++ 编译，LD_LIBRARY_PATH 指向 conan 依赖包
$ ./testkcd; echo EXIT=$?
Testing libKF5CompactDisc
Starting test
We have 2 audo systems available:
"phonon"
"alsa"          # HAVE_ALSA 生效（alsa-lib/1.2.16.1）
We have 0 cdrom drives available:   # 无光驱硬件，预期
The disc status is 4 (Nodisc)       # 安全退化
EXIT=0

# 产物
package/lib/libKCompactDisc6.so          # DT_SONAME=libKCompactDisc6.so（E092 注入）
package/lib/cmake/KCompactDisc6/...      # 上游导出 config（find_dependency Qt6Core）

# 上游测试清点（R51）：tests/testkcd.cpp 存在但未注册 ctest（ctest -N = 0），
# 为手动运行的 QCoreApplication 程序；已真实构建+运行，如上。
```

## 平台知识沉淀（跨版本通用）

1. **conan 进程树 symlink() 一票否决**：HMDFS/SELinux 按进程标签拒绝 symlink()，
   python3 及其后代（make→cmake）全部被拒；交互 shell 后代不受影响。任何带
   VERSION/SOVERSION 的 CMake 共享库在本机 conan create 下必然失败——必须去掉
   VERSION/SOVERSION 属性并依赖 E092 注入的 soname flag（产物为未版本化单文件，
   功能无损）。注意：qtbase 等含 SOVERSION 的包应是 CI 端构建，本地复现会踩此坑。
2. **OHOS clang-15 对 `-Wl,a,b` 不拆分**：自定义 linker flags 避免 LINKER:SHELL
   逗号多参形式，用 CMake 平台变量注入（E092）或单 token 形式。
3. Qt6DBus 在本仓 qtbase 中未构建（FEATURE_dbus=OFF），KDE 包遇到 DBus 组件时
   应参照 solid（USE_DBUS=OFF）做可选化，禁止 find_package(DBus REQUIRED)。
---

**编译结束**: 2026-09-24 23:45
**最终状态**: published
