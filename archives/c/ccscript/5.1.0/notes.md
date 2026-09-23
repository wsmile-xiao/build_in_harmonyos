# ccscript 5.1.0 适配笔记

## 编译环境
- **构建系统**: autotools (configure + make)
- **编译日期**: 2026-09-16
- **编译器**: clang（OHOS 工具链）
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过——conan create 全绿）
- **补丁数量**: 0（配方内联处理——无独立补丁文件）
- **依赖**: ucommon/7.0.1（硬依赖，`PKG_CHECK_MODULES(ucommon >= 7.0.0)` 探测；传递依赖 gnutls/nettle/hogweed/libtasn1/libgcrypt/libgpg-error/gmp/libunistring）

## 编译步骤（conan create 全流程）

```bash
conan create archives/c/ccscript/5.1.0 --build=missing
```

### 1. 源码获取（source()）
```bash
tar -xzf ccscript-5.1.0.tar.gz --no-same-owner || true
cp -a ccscript-5.1.0/. . && rm -rf ccscript-5.1.0
```

### 2. generate() 前置处理
- **AutotoolsToolchain(self).generate()**：不生成则 conanbuild 无 CC/CXX，老 configure 的编译器候选列表不含 clang++。
- **依赖库可重定位副本**（关键攻坚）：
  - 依赖 `.la` 记录构建期路径或错误 libdir——实测 `libgpg-error.la` 的 `libdir='//lib'`（其安装前缀为 `/`），libtool 解析依赖时 `sed: //lib/libgpg-error.la: No such file or directory`；ucommon 的 `.la` 则记录构建缓存绝对路径（`was moved` 警告 + `is not a valid libtool archive`）。
  - 处置：把所有依赖的 `*.la/*.a/*.so*` 复制到 `<build>/deps-lib`，`dependency_libs` 清空、`libdir` 指向副本；LDFLAGS 最前置该目录。**不改 conan 缓存中的依赖包本体**。
  - 注意：依赖混合静态/动态（libtasn1/libgcrypt/libgpg-error 为 `.so`，libgmp/libunistring 为 `.a`），`.so*` 必须一并复制。
- **自建 ucommon.pc**：依赖 `.pc` 同样不可重定位（`ucommon.pc` 的 `prefix` 指向构建缓存；`gpg-error.pc` 为 `prefix=/`，做路径替换会破坏所有 `/`）。改为在 `<build>/deps-pkgconfig/ucommon.pc` 自建，路径全部指向真实 `package_folder`，经 `PKG_CONFIG_PATH` 提供。

### 3. build() 处理
- **config.status mktemp**：`mktemp -d "./confXXXXXX"` → `${TMPDIR}/confXXXXXX`（TMPDIR=/data/storage/el2/base/cache）。
- **config.sub**：补 `linux-ohos` 模式（识别 ohos 三元组）。
- **依赖路径**：CXXFLAGS/LDFLAGS 显式给出全部依赖的 `-I/-L`（置于探测内容之前）。
- configure：`./configure --with-pkg-config --build=aarch64-unknown-linux-ohos --prefix=/usr --disable-shared`
- `make -j2`

### 4. 上游测试（build() 集成——rule 4/R51 实测回填）
上游测试入口：`test/Makefile.am` 的 `TESTS = testScript`（automake check 注册项）。
`test/script.cpp` 驱动解释器编译并执行 `testscript.scr`/`mergescript.scr`（含
check/check.exit/check.main/check.event/check.loop/check.refs/check.manip 断言计数
与 `@exit` 处理器验证），退出码判定——真实行为测试。

实测结果（build() 内 `make check` 真实执行）：
```
PASS: testScript
# PASS:  1
# FAIL:  0
```

### 5. 打包（package()）
```bash
make install DESTDIR=<package_folder>
```
安装布局：`usr/include/ccscript.h`、`usr/lib/libccscript.a`、`usr/lib/pkgconfig/ccscript.pc`；
cpp_info：includedirs=["usr/include"]、libdirs=["usr/lib"]、libs=["ccscript"]

## 验证结果
- **构建**: `ccscript/5.1.0: Package created`（conan create 全绿）
- **上游测试**: 实测 **1/1 通过**（testScript，automake TESTS 注册项，无跳过、无平台受限项）
- **R34 消费者验证**: test_package — 以库使用者身份编译链接并运行 `smoke.cpp`
  （`Script::init()` + `Script::compile()` 编译内联脚本并校验 `getErrors()==0`），
  输出 `ccscript Script::compile OK`

## 已知限制
- 库以静态方式构建（`--disable-shared`，与 commoncpp2/ccaudio 同族先例一致）；
  传递依赖（gnutls 等）为动态库，由 Conan 管理依赖链。
- 消费者引入头文件需同时提供 ucommon 的 include（`ccscript.h` 依赖 `<ucommon/ucommon.h>`）。
---

**编译结束**: 2026-09-16 00:39
**最终状态**: built
