# libmwaw-tools 0.3.22 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-09-16
- 编译器: clang 15 (aarch64, OHOS 6.0)
- 状态: published

## 编译步骤

本包 = libmwaw 上游源码构建产物中的命令行工具集 + libmwaw 共享库。

1. conan source 下载 libmwaw-0.3.22.tar.xz (SourceForge)
2. 应用 3 个 OHOS 移植补丁（config.guess / config.sub / configure umask）
3. staging 依赖：从 librevenge/zlib conan 包复制 .a 到 build/depstaging/lib，
   复制头文件，本地生成 prefix 正确的 .pc（zlib / librevenge-0.0 /
   librevenge-generators-0.0 / librevenge-stream-0.0）
4. PKG_CONFIG_PATH=depstaging/lib/pkgconfig ./configure --with-docs=no
5. make -j4 && make install
6. 打包 bin/(7 个工具) + lib/(libmwaw-0.3.so*) + include/libmwaw-0.3/ + licenses/

## 遇到的问题与解决方案

| 问题 | 根因 | 解决方案 |
|------|------|----------|
| configure 报 aarch64-unknown-linux-ohos 未知 | config.guess 2014 年版本不认识 HarmonyOS | 补丁 0001 加 OHOS 识别分支 |
| config.sub 拒绝 linux-ohos 三元组 | 内核-OS 白名单无 ohos | 补丁 0002 加白名单 |
| config.status 写 subs1.awk "Permission denied" | umask 077 临时目录在 HMDFS 上不可写 | 补丁 0003 改 umask 022 |
| pkg-config 找不到依赖 / prefix 错误 | librevenge 包 .pc 文件 prefix 硬编码为 / | 配方内 staging .a + 本地生成正确 prefix 的 .pc |
| libtool 报 //lib/librevenge-0.0.la is not a valid libtool archive | .la 内嵌 prefix=//lib 已失效，libtool 优先读 .la | staging 目录只放 .a，libtool 直接链静态库 |
| 头文件 librevenge/RVNGInputStream.h 找不到 | staging .pc 的 Cflags 少了 /librevenge-0.0 子目录 | Cflags 改 -I includedir/librevenge-0.0（与上游一致） |
| test C++ 无 RVNGMemoryStream.h | librevenge 0.0.5 包不发布该头文件 | 测试内自实现 RVNGInputStream 内存流 |
| CMakeDeps 生成空 LIBS/INCLUDE_DIRS | application 包默认 require traits headers/libs=False | test recipe 显式 requires(ref, headers=True, libs=True) |
| CXXLD libmwaw-0.3.la 报 R_AARCH64 relocation (z_errmsg, recompile with -fPIC) | zlib/1.3.1 发布二进制为 --static 非 PIC，libz.a 被静态链入共享库 libmwaw-0.3.so (CI 实测) | override 到同源 -fPIC 变体 zlib/1.3.1.1（先例: abiword-plugin-docbook） |

## 源码修改

3 个 OHOS 移植补丁（见 patches/）：
- 0001: config.guess 增加 HarmonyOS 识别（输出 aarch64-unknown-linux-ohos）
- 0002: config.sub 白名单增加 linux-ohos
- 0003: configure/config.status umask 077→022（HMDFS 兼容）

未修改上游测试用例（上游无测试套件）。

## 依赖版本

- librevenge/0.0.5 (conan, 已先行构建)
- zlib/1.3.1.1 (conan, override；同源 -fPIC 静态变体，见下"zlib PIC"问题)
- 运行时仅 libc++_shared.so / libc.so（依赖库静态链入 libmwaw-0.3.so）

## 验证结果

conan-verify (G0 风险评估 / G1 完整性 / G2 conan create / G3 同名库隔离 / G4):
python3 scripts/ohc-run.py conan-verify libmwaw-tools 0.3.22 → 配方验证通过 (G0-G4 全 PASS)

CLI 冒烟 (conan test_package 内执行):
mwawFile --version → mwawFile 0.3.22
mwaw2text --version → mwaw2text 0.3.22

C++ API 实质测试 (mwaw_api_test: 链接 libmwaw, 调 MWAWDocument::isFileFormatSupported 断言分类):
PASS: non-Mac payload rejected (confidence=NONE)
PASS: empty stream rejected (confidence=NONE)
PASS: libmwaw API test completed

## 注意事项

- 上游 make check 无自动化测试（源码树无 tests/ 目录），功能验证依赖 test_package
- commands.json 已声明 7 个工具；binary 字段在发布制品仓后改 true
- staging 方案只对包构建有效，系统级安装 librevenge 不受影响

## 最终状态

- 状态: COMPLETED
- conan-verify G0-G4: 全部 PASS
- test_package (CLI 冒烟 + C++ API 实质测试): PASS
- 交付: archives/l/libmwaw-tools/0.3.22/ (conanfile.py + conandata.yml + 3 补丁 + test_package + reports)
