# libfido2 1.15.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-04（W3 conan 配方化完成）
- 编译器: clang/clang++ (OHOS SDK 15.0.4, aarch64-linux-ohos)
- 状态: built（W3 conan create 通过）

## 依赖（制品仓实际版本）
| 软件 | 版本 | 备注 |
|------|------|------|
| libcbor | 0.10.2 | 制品仓唯一版本（历史 manifest 写 0.11.0 不在仓） |
| openssl | 3.5.6 | 静态链接进包；fido.h 公开头 include openssl/*.h，配方需 transitive_headers=True |
| zlib | 1.3.1 | 上游 CMakeLists pkg-config 检测，缺了直接 FATAL |

## 编译步骤（conan 配方，W3 验证通过）

```bash
# profile: $HOME/.conan2/profiles/ohos-aarch64
python3 -c "from conans.conan import run; import sys; sys.argv=['conan','create','<配方目录>','--name=libfido2','--version=1.15.0','-pr:h=$HOME/.conan2/profiles/ohos-aarch64','-pr:b=$HOME/.conan2/profiles/ohos-aarch64','--build=missing','-v']; run()"
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | HID backend未定义 | CMakeLists.txt未识别HarmonyOS系统 | patch 0001/0002: 添加 OHOS 识别，HID backend 走 hid_linux.c + hid_unix.c |
| 2 | ppoll系统调用"不可用" | **历史结论修正**：OHOS musl 的 poll.h 有 ppoll 声明，但需要 _GNU_SOURCE 宏（未定义时编译器报 implicit declaration）| patch 0003 保留 __OHOS__ 下 poll() 回退（保守）；工具链 CMAKE_C_FLAGS 补 -D_GNU_SOURCE -D_DEFAULT_SOURCE |
| 3 | libudev.h缺失 | HarmonyOS缺少libudev库 | patch 0004: static-inline libudev.h stub（全部函数返回 NULL/-1） |
| 4 | patch 0004 应用失败 | conan apply_conandata_patches 拒绝 new-file patch 的 a/ 路径头 | 补丁头改 git 风格 `--- /dev/null` + `new file mode 100644` |
| 5 | pkg_search_module(CRYPTO libcrypto) 失败 | PkgConfigDeps 只按 openssl 配方 pkg_config_names 生成 openssl.pc，不生成 libcrypto.pc | generate() 里基于 openssl 依赖真实路径手写 libcrypto.pc 到 generators 目录 |
| 6 | CMakeDeps target 未找到 | 配方未设 cmake_target_name，默认生成 libfido2::libfido2，与上游 fido2 不一致 | package_info 设 cmake_file_name/cmake_target_name = fido2（与上游 libfido2.pc 一致） |
| 7 | test_package 编译缺 openssl/ec.h | fido.h 公开头直接 include openssl 头，openssl 是头文件级公开依赖 | requires openssl 加 transitive_headers=True |
| 8 | **安装后 tools 报 "Error loading shared library ../src/libfido2.so"** | conan CMakeToolchain 的 rpath 布局导致链接命令缺 -Wl,-soname；无 SONAME 时链接器把 NEEDED 写成构建期相对路径，装到包目录后不可用 | toolchain 注入 CMAKE_SHARED_LINKER_FLAGS="-Wl,-soname,libfido2.so"（不带版本号，与 conan 包内单文件布局匹配）|

## SONAME 问题的详细证据链（可复用模式）

现象：`conan create` 成功，但 `$PKG/bin/fido2-token -V` 报
`Error loading shared library ../src/libfido2.so: (needed by ./fido2-token)`

诊断：
```bash
llvm-readelf -d <pkg>/bin/fido2-token | grep NEEDED
# → NEEDED: ../src/libfido2.so   ← 构建目录相对路径，安装后失效
llvm-readelf -d <pkg>/lib/libfido2.so | grep SONAME
# → (无 SONAME 条目)             ← 根因
```

根因：上游 CMakeLists 用 `set_target_properties(fido2_shared PROPERTIES VERSION 1.15.0 SOVERSION 1)`，
正常 Linux 构建时 CMake 会传 `-Wl,-soname,libfido2.so.1` 并生成版本符号链接；
但 conan CMakeToolchain 的 rpath/输出布局（CMAKE_SKIP_RPATH）下 CMake 不传 soname。
无 SONAME → 链接 tools 时 ld 把 NEEDED 记录为命令行里给出的路径（../src/libfido2.so）。

修复：conanfile generate() 里
`tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = "-Wl,-soname,libfido2.so"`
（conan 包内单文件布局 → soname 不带版本号；若带 .so.1 则包内无该文件，运行时仍找不到）

验证：
```bash
llvm-readelf -d <pkg>/lib/libfido2.so | grep SONAME   # → libfido2.so
llvm-readelf -d <pkg>/bin/fido2-token | grep NEEDED   # → libfido2.so (正确)
LD_LIBRARY_PATH=<pkg>/lib ./fido2-token -V            # → 1.15.0
```

## 测试结果（W3 验证）

| 测试 | 结果 |
|------|------|
| 上游 regress_assert / cred / dev / eddsa / es256 / es384 / rs256 | 7/7 PASS（本机 OHOS aarch64 直接运行，需 LD_LIBRARY_PATH 指向包 lib） |
| regress_compress | 未构建（仅 BUILD_STATIC_LIBS 时编入；本配方默认 shared） |
| test_package（consumer API 烟雾测试） | PASS：fido_init/fido_dev_new/es256_pk_from_ptr(uncompressed+x||y)/rs256_pk/eddsa_pk/fido_strerr |
| fido2-token -V | 输出 1.15.0 |
| fido2-assert -V / fido2-cred -V | 正常输出 usage/退出 |

## 源码修改（4 个补丁，main 已合并的 f39c1c1 版本 + 0004 头格式修正）

1. **0001-CMakeLists.txt.patch**：HarmonyOS 识别 + NFC_LINUX OFF + stub-udev include
2. **0002-src-CMakeLists.txt.patch**：HarmonyOS 走 Linux HID backend
3. **0003-src-hid_unix.c.patch**：__OHOS__ 下 poll() 替代 ppoll（保守回退）
4. **0004-src-stub-udev-libudev.h.patch**：static-inline libudev stub（补丁头改为 /dev/null 格式以通过 conan patch 应用）

## 注意事项

- openssl/zlib/libcbor 在本平台均为静态链接（包内只有 .a），libfido2 shared 库仅 NEEDED libc.so + libfido2.so
- 历史记录（2026-05-19/20）的手动编译产物在 /storage/Users/currentUser/usr/local（fido2-token 等），与本 conan 包无关
- 历史 pr-547 曾把 libcbor/0.11.0 与 hidapi stub 方案带入（5 轮修复未收敛后回滚）；本次 libcbor 改用仓内 0.10.2，hidapi 不引入（USE_HIDAPI=OFF 默认，走 hid_linux 直连）

## 平台功能限制（R40 适配完整性说明，需人工确认）

libfido2 属外设访问类库（USB HID 认证器通信）。OHOS 无 libudev/hidraw
udev 集成，本适配的 stub-libudev 方案对**设备发现**路径的影响：

| 功能 | 状态 | 说明 |
|------|------|------|
| 库核心（CTAP2 协议、CBOR 编解码、attestation/assertion 签名验证、加解密） | ✅ 完整 | 纯计算逻辑，上游 7 个 regress 测试全过，test_package 实测 API |
| ES256/RS256/EdDSA/ES384 公钥操作 | ✅ 完整 | openssl 3.5.6 支撑，regress_es256/es384/eddsa/rs256 全过 |
| fido2-token -V / usage / -L（无设备） | ✅ 正常 | CLI 工具运行正常 |
| **fido_hid_manifest 设备枚举**（fido2-token -L 列举真实设备） | ⚠️ 降级 | udev_new() stub 返回 NULL → 返回 FIDO_ERR_INTERNAL（0 列表），**无 udev 时设备发现不可用** |
| 设备打开/IO（fido_dev_open 指定路径） | ⚠️ 未验证 | hid_linux.c 走 /dev/hidraw 直连（fido_hid_unix_open），若 OHOS PC 提供hidraw 设备节点则路径存在，**无真实 FIDO 硬件未实测** |

OHOS PC 正确的 HID 适配方向（后续版本可参考）：接入 OHOS HID-DDK
或直接扫描 /dev/hidraw*（跳过 udev 枚举）。设备发现是外设类库的
平台相关功能，当前以 stub 方案保证库与工具链可用，协议栈完整。

---

**编译结束**: 2026-09-04 02:31
**最终状态**: built
