# sonic 0.2.0 适配笔记

## 编译环境
- **构建系统**: Makefile（纯 make，无 configure/cmake）
- **编译日期**: 2026-09-02
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0（纯 ANSI C，零依赖，无需 OHOS 改动）

## 编译步骤（conan create 全流程）

```bash
conan create archives/s/sonic/0.2.0 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 GitHub gh-proxy/codeload tarball 下载。
注意上游 tag 是 `release-0.2.0`（`v0.2.0` 404 实测）。

### 2. 构建（build()）
- 纯 `make -j1`（R9）：产出 `sonic` CLI、`libsonic.so.0.2.0`
  （SONAME `libsonic.so.0`，含 .so/.so.0 symlink）、`libsonic.a`
- R33：GnuToolchain 注入 CC/CFLAGS（OHOS clang）

### 3. 打包（package()）
- `bin/sonic`（CLI）
- `include/sonic.h`
- `lib/libsonic.so.0.2.0` + .so/.so.0 symlink + `lib/libsonic.a`
- E077 四步签名（remove-section → sign → chmod）：OHOS 内核拒绝未签名
  可执行文件/共享库

## 依赖
- 无（纯 ANSI C，零第三方依赖）

## 上游测试（rule 4）
- sonic 0.2.0 **无独立测试套件**：无 test/ 目录、无 make test 目标，
  README 只含手动性能基准——rule 1.2 如实声明"上游无测试"（非跳过）
- 本地验证：conan create 通过，sonic 与 libsonic.so/.a 编译链接成功并打包
- 适配后：test_package R34 真实产物校验——sonic 可执行 + libsonic.so 存在 +
  ELF + 运行 sonic（无参数打印 usage），1/1 = 100%

## 已知限制
- 无
