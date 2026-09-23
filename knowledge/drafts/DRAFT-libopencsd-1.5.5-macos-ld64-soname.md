# DRAFT: macOS 本机验证 makefile 系 OHOS 包时，ld64 不认 -soname/-Wl,-z,defs，需以 -install_name 替代并置空 PLATFORM_LDFLAGS

- **草稿**: DRAFT-libopencsd-1.5.5-macos-ld64-soname
- **来源库**: libopencsd 1.5.5（Linaro/OpenCSD，纯 Makefile C++ 库）
- **门禁**: conan create（default profile）/ W3 本地 CI / conan-verify G2
- **状态**: DRAFT — 需审核后 promote 为正式 E 条目

## 问题

libopencsd 1.5.5 的 `decoder/build/linux/makefile` + `unix_common/makefile.common`
为 GNU 链接器编写的共享库链接行固定携带 `-Wl,-soname,libopencsd.so.1`
（`SONAME_FLAG` 变量）与 `-Wl,-z,defs`（`PLATFORM_LDFLAGS` 变量）。
在 macOS 本机以 conan default profile 验证时，ld64 报错：

```
ld: unknown option: -soname,libopencsd.so.1
ld: unknown option: -z defs
```

OHOS CI（lld）与 Linux（GNU ld）均支持这两个参数，不会出错。

## 根因

macOS 的 ld64 不支持 GNU 风格的 `-soname` 与 `-z defs` 链接参数；其等价物是
`-install_name`（记录 dylib 标识名）。上游 makefile 以 `SONAME_FLAG` /
`PLATFORM_LDFLAGS` 两个变量携带这些参数，为命令行覆盖留了口子。该差异纯属
平台链接器参数，与库源码无关，不能在配方里全局改写（否则破坏 OHOS 目标平台
的 DT_SONAME 语义，见 L5/A2 门禁）。

## 方案

仅在 macOS 本机验证路径上，以 make 命令行变量覆盖：

```bash
make SONAME_FLAG=-install_name PLATFORM_LDFLAGS= \
     MASTER_CC=<cc> MASTER_CXX=<cxx> MASTER_LINKER=<cxx> MASTER_LIB=<ar> -j1
```

配方侧用平台判定（`sys.platform == "darwin"`）把覆盖限制在本机 default
profile；OHOS/CI 保持上游默认参数（lld 生成 DT_SONAME）。

## 验证

- libopencsd 1.5.5，macOS apple-clang，conan 2.29.1（default profile）
- conan create 全绿（构建 + test_package consumer 3 断言 + dlopen 链验证）
- 上游 61 个测试场景 61/61 通过
- conan-verify default profile G1-G4 全 PASS；W3 本地 CI exit 0（L0/L1/L4 PASS）
- OHOS 侧 DT_SONAME 由远程 CI（lld）复核

## 适用边界 / 限制

- 仅适用于 macOS 本机验证（conan default profile / W3）；Linux/OHOS 保持上游默认。
- `-install_name` 只影响 dylib 标识，不参与 ELF DT_SONAME 语义；A2 SONAME 断言只在 OHOS 上执行。
- 禁止在 OHOS/CI 路径去掉 `-soname`（丢失 DT_SONAME 会违反 L5 门禁与 A2 断言）。

## 查重差异

已扫描官方只读快照 `knowledge/graph/E*.kv` 与 `knowledge/drafts/`：
- 无等价命中：无条目覆盖 macOS ld64 与 GNU 链接参数的差异及 `SONAME_FLAG` /
  `PLATFORM_LDFLAGS` 覆盖路径。
- 相邻条目 E207（HarmonyOS CMake 相对路径链接/SONAME 缺失）、E316（共享库
  加载失败）均为 OHOS/Linux 侧，不覆盖本机 macOS 验证场景。
- 本草稿聚焦 macOS 本机验证 makefile 系 OHOS 包的链接参数差异，对在本仓库
  用 default profile 做本地预验证的适配者具跨库复用价值。
