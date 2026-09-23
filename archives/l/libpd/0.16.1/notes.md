# libpd 0.16.1 适配笔记

## 编译环境

- 构建系统: makefile（上游手写 Makefile，无 configure）
- 编译日期: 2026-09-15
- 编译器: OHOS clang 15.0.4（`/data/service/hnp/bin/clang`，target `aarch64-unknown-linux-ohos`）
- Conan: 2.29.1（OHOS 适配版），profile `ci/conan/profiles/ohos-aarch64`
- 设备: OpenHarmony PC aarch64（`uname -s` = `HarmonyOS`）

## 编译步骤

```sh
# 库（动态，默认）
make libpd -j1 CC="<clang>" \
  ADDITIONAL_CFLAGS="-O3 -DNDEBUG -DHAVE_ALLOCA_H -DHAVE_LIBDL" \
  ADDITIONAL_LDFLAGS="-ldl -Wl,-soname,libpd.so"
# 库（静态，-o shared=False）
make libs/libpd.a -j1 CC="<clang>" ADDITIONAL_CFLAGS="..."
# 安装（prefix 直接指向 package_folder）
make install prefix="<package_folder>" CC="<clang>"
```

`make install` 安装布局：

```
include/libpd/{z_libpd.h,m_pd.h,m_imp.h,g_canvas.h,PdBase.hpp,PdTypes.hpp,PdReceiver.hpp,PdMidiReceiver.hpp}
include/libpd/util/{z_print_util.h,z_queued.h}
lib/libpd.so | lib/libpd.a
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|---------|
| 1 | GitHub 源码包里 `pure-data/` 是空目录，`make` 报 `No rule to make target 'pure-data/src/d_arithmetic.o'` | libpd 通过 git submodule 引入 Pure Data，GitHub 归档不含子模块内容 | conandata.yml 新增 `submodules.pure-data`（固定 commit `f009fd8d`），`source()` 用 `get(..., destination="pure-data", strip_root=True)` 注入 |
| 2 | OHOS 上 `HAVE_LIBDL`/`HAVE_ALLOCA_H` 未定义，dlopen 支持被静默关闭 | Makefile 用 `UNAME = $(shell uname)` 分支，OHOS 上 `uname -s` 是 `HarmonyOS`（不是 `Linux`），Linux 分支不触发 | 经 `ADDITIONAL_CFLAGS` 显式加 `-DHAVE_ALLOCA_H -DHAVE_LIBDL`、`ADDITIONAL_LDFLAGS` 加 `-ldl`（`alloca.h`/`dlfcn.h` 在 OHOS sysroot 中实测存在；OHOS 的 `dlopen` 符号在 libc，`libdl` 为空壳，`-ldl` 链接成功） |
| 3 | 环境变量 `CFLAGS` 对上游 Makefile 无效 | Makefile 用 `CFLAGS = ...`（`=` 赋值）覆盖环境变量 | 只用 Makefile 自带的 `ADDITIONAL_CFLAGS` / `ADDITIONAL_LDFLAGS` 钩子传 Conan 工具链 flags |
| 4 | `test()` 里 `libpd_openfile` 打不开夹具 | `libpd_openfile(name, dir)` 把 `name` 当相对名拼到 `dir` 后，传绝对路径会被二次拼接 | 传夹具基名 `libpdtest.pd` + 所在目录 `self.build_folder` |
| 5 | 本地 CI 的 L5a 质量门禁报 `libpd.so 缺少 DT_SONAME`（下游链接器无法按 SONAME 寻址，CMakeDeps 会退化成 `IMPORTED_NO_SONAME`） | 上游链接命令只给 `-shared -Wl,-Bsymbolic`，不设置 SONAME | `ADDITIONAL_LDFLAGS` 追加 `-Wl,-soname,libpd.so`（与安装出的未版本化文件名一致），不改上游源文件 |

## 源码修改

无补丁（`patches/` 为空）。上述问题均在配方层解决，未改动任何上游源文件。

## 依赖版本

无第三方依赖（只用到 OHOS sysroot 的 libc / libm / pthread）。

内嵌源码快照：

| 组件 | 版本/commit | 来源 |
|------|-------------|------|
| libpd | 0.16.1（tag） | https://github.com/libpd/libpd/archive/refs/tags/0.16.1.tar.gz |
| pure-data（子模块） | `f009fd8d7b537e209e09898d487fdf1bf547da2b`（项目内版本号 0.56.5） | https://github.com/pure-data/pure-data/archive/f009fd8d7b537e209e09898d487fdf1bf547da2b.tar.gz |

## 验证结果

```sh
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# → rc=0；test_package 消费者断言 16/16 PASS，failures=0
```

上游测试清点（N = 84 个用例，N′ = 0；完整清单与逐项原因见
`test_package/MANIFEST.yml` 与 `reports/test-report.md`）：

- **JUnit 4 绑定测试 19 个用例**（`samples/java/test/.../PdBaseTest.java` 16、
  `PdDispatcherTest.java` 3）——需 JVM + JUnit + `jni/` 构建的 `libpdnative`；OHOS 目标无该运行时，
  上游 CI 也完全未触及 `samples/java`。
- **NUnit 绑定测试 63 个用例**（`samples/csharp/pdtest/` 13 个 `*Tests.cs`）——需 .NET/Mono + NUnit；
  OHOS 目标无 .NET 运行时，上游 CI 未触及 `samples/csharp`。
- **无框架 assert 程序 2 个**（`samples/c/pdtest_thread` 17 处 assert、`samples/c/pdtest_queued`
  3 处 assert）——走 `libpd_new_instance`/`libpd_queued_init`，需 `PD_MULTI=true`；本配方沿用上游
  默认 `PD_MULTI=OFF`（此时 `libpd_new_instance()` 返回 NULL，见 `libpd_wrapper/z_libpd.c`），
  测的是未交付的构建变体；上游 CI 只编译、从不运行。
- 其余示例（`samples/c/pdtest` 等 5 个、`samples/cpp`、`emscripten`、`objc`、`python`）与
  pure-data 的 `libpd/test_libpd`、`gtk/test1.pd` 均**无断言**，不构成测试入口。

适配后以 `test_package` 消费者断言（16 条）覆盖核心路径，作为交付物的验收证据。

## 交付物

| 文件 | 说明 |
|------|------|
| `include/libpd/z_libpd.h` | 公共 C API（消费者入口） |
| `include/libpd/m_pd.h` / `m_imp.h` / `g_canvas.h` | Pure Data 公共头 |
| `include/libpd/util/*.h` | queued/print 工具头 |
| `include/libpd/*.hpp` | C++ 封装头 |
| `lib/libpd.so`（默认） / `lib/libpd.a`（`-o shared=False`） | 库本体 |

## 注意事项

- `PD_EXTRA=ON`（上游默认）会把 bob~/bonk~/fiddle~/sigmund~/pd~ 等 extra 对象编入库；
  `libpd_init()` 会打印 `pd <version>` 与各 extra 的版本横幅。
- 多实例 API（`libpd_new_instance` 等）需要上游的 `PD_MULTI` 构建开关
  （等价 Makefile 变量 `MULTI=true`，即 `-DPDINSTANCE -DPDTHREADS`）。本配方沿用上游
  默认值 `PD_MULTI=OFF`（CMake 与 Makefile 的默认一致），故不导出该组符号；需要时
  在上游以 `MULTI=true` 构建即可，与平台适配无关。
- 交付物**不是**系统同名库，保留 Conan 管理的动态链接默认值（`shared=True`）。
- `libpd.so` 的 `DT_SONAME` 由配方追加的 `-Wl,-soname,libpd.so` 设置（与安装文件名一致）；
  上游 Makefile 不设置 SONAME，本地 CI 的 L5a 门禁会拒绝缺失 SONAME 的共享库。
