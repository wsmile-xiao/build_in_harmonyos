# ccrtp 2.1.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-06
- 编译器: clang/clang++ 15.0.4 (OHOS aarch64, cppstd=17)
- 状态: built

## 编译步骤

1. 下载源码: `ccrtp-2.1.2.tar.gz`（sha256 f035ca0e1b5d37b78e358f07a25b05c5cdaf2c85c4b31cf29f6be17f288a349e，官方 ftp.gnu.org）
2. 打 4 个适配补丁（见 patches/，均在 conandata.yml 声明）：
   - 0001 config.guess：识别 HarmonyOS → `aarch64-unknown-linux-ohos`（2013 版脚本在 OHOS 上无法猜测 build type，E007）
   - 0002 config.sub：接受 `-linux-ohos*` 三元组
   - 0003 configure：无条件定义 SRTP_OPENSSL/SRTP_GCRYPT automake 条件（支持 `--disable-srtp`）+ config.status 临时目录 umask 022（E129 HMDFS setgid）
   - 0004 src/CryptoContextCtrl.cpp：显式 include `ccrtp/CryptoContext.h`（SRTP 关闭时 SrtpEncryptionNull/SrtpAuthenticationNull 在 SRTP_SUPPORT 守卫外被引用但声明未拉入）
3. 编译命令（conanfile.py build() 实际流程）：
   ```bash
   ./configure --prefix=<prefix> --disable-srtp --enable-static --disable-shared
   make -j1
   make check    # 上游无 automake TESTS，为 no-op
   make install
   ```
4. 编译依赖通过 conan 管理：ucommon/7.0.1（含 commoncpp 兼容层，commoncpp.pc Version 7.0.1 >= 6.2.2 满足 configure 的 PKG_CHECK_MODULES commoncpp >= 6.2.2）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 `No package 'commoncpp' found` | ccrtp 用 PKG_CHECK_MODULES 检查 `commoncpp`（ucommon 的兼容模块），但 ucommon 配方 pkg_config_name=ucommon，PkgConfigDeps 只生成 ucommon.pc | generate() 注入 `PKG_CONFIG_PATH=<generators_folder>`，并生成 shim `commoncpp.pc`（Requires: ucommon + -lcommoncpp） |
| 2 | configure 报 `Cannot find libgcrypt or OpenSSL crypto library` | SRTP 为可选加密层，上游在缺少 libgcrypt/OpenSSL 时硬失败 | `--disable-srtp` 关闭 SRTP（核心 RTP 功能不依赖加密后端） |
| 3 | clang 编译 `-ansi`(C++03) 触发 ucommon nullptr shim 冲突 | ccrtp WARN_FLAGS 传 `-ansi`，ucommon platform.h 的 legacy nullptr shim 与 libc++ 冲突 | CXXFLAGS 追加 `-std=c++17`（profile cppstd=17，位于编译命令行最后覆盖 -ansi） |
| 4 | configure 的 conftest 运行报 "Error loading shared library" (exit 127) | OHOS loader 无 conan 缓存共享库默认搜索路径 | generate() 为每个依赖 libdir 设置 LD_LIBRARY_PATH（同 aaphoto/0.45 E064） |
| 5 | libtool 链接报 `'//lib/...' is not a valid libtool archive` | 依赖包内的 .la wrapper libdir 指向 CI 构建的假 prefix | build() 中删除依赖包 libdir 下的 *.la 文件 |
| 6 | **消费者仅 require ccrtp 时找不到 `<commoncpp/pointer.h>`** | Conan 2 `transform_downstream()` 对 static→static 库链把下游消费者的传递依赖 require.headers 置为 False，CMakeDeps 在数据文件中把 ucommon_INCLUDE_DIRS_RELEASE 渲染为空；仅 `cpp_info.requires=["ucommon::ucommon"]` 只传递链接边不传递头文件路径 | requirements() 声明 `self.requires("ucommon/7.0.1", transitive_headers=True)`，使下游对 ucommon 的 require.headers 保持 True（见 E269 草稿） |

## 源码修改

4 个补丁，见 `patches/`：
- `0001-autoconf-config.guess.patch` — autoconf/config.guess
- `0002-autoconf-config.sub.patch` — autoconf/config.sub
- `0003-configure.patch` — configure
- `0004-src-CryptoContextCtrl.cpp.patch` — src/CryptoContextCtrl.cpp

## 依赖版本

- ucommon/7.0.1（制品仓已发布，R36；含 commoncpp 兼容层）
- tool_requires: pkgconf/3.0.5

## 验证结果

```bash
# conan create（含 test_package 消费者验证）
ccrtp/2.1.2@ohpcd/stable (test package): 1/1 Test #1: test_ccrtp ... Passed
# conan-verify: G0-G4 + L2/L4/L5 全 PASS
# make check: no-op 通过（上游无 automake TESTS）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（autotools，--disable-srtp，ucommon transitive_headers） |
| conandata.yml | 源码 URL/SHA256 + 4 补丁声明 |
| test_package/ | 消费者 smoke test（InetHostAddress + IncomingRTPPkt，仅 require ccrtp 验证 include 传递） |
| patches/ | 4 个适配补丁 |
| manifest.yaml | 版本编译元数据 |

## 注意事项

1. SRTP 未启用（`--disable-srtp`），需要时需提供 libgcrypt/OpenSSL
2. 消费者 include 传递：主配方必须 `requirements()` 用 `transitive_headers=True` 声明依赖（仅 `cpp_info.requires` 不够），否则下游只 require ccrtp 时找不到 ucommon/commoncpp 头文件（E269）
3. 必须使用 conan ucommon/7.0.1（commoncpp.pc 提供 commoncpp >= 6.2.2）
---

**编译结束**: 2026-09-06 12:02
**最终状态**: built
