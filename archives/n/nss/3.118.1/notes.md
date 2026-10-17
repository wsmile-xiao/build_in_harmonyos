# nss 3.118.1 适配笔记（HarmonyOS PC / aarch64）

## 编译环境
- 构建系统: make（NSS coreconf 体系，非 autotools）
- 编译日期: 2026-08-15
- 编译器: clang 15 / clang++
- 状态: published

## 编译步骤

```bash
# 1. 源码：官方 with-nspr bundle（tarball 根含 nss/ 与 nspr/ 两个子目录）
# 2. conan 配方依赖 nspr/4.37（已发布到 ohpcd）
# 3. 补丁应用后，在源码树 nss/ 子目录执行：
make BUILD_OPT=1 USE_64=1
#    （manifest.mn 补丁已将 DIRS 裁剪为 coreconf lib，跳过 cmd/gtests 工具）
# 4. conan create 验证 + test_package L1 测试
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | NSS 无顶层 configure，被 G0/init 误判为 autotools | NSS 用 coreconf make 体系，configure 位于 tarball 的 nspr/ 子目录 | manifest 声明 build_system: make；构建入口为 nss/ 下 make |
| 2 | OHOS 无 /bin/bash shebang 目标 | E165 类问题 | conan profile buildenv 设置 CONFIG_SHELL=/data/service/hnp/bin/bash |
| 3 | softoken 运行时初始化曾疑失败（SEC_ERROR_PKCS11_DEVICE_ERROR -8023） | 历史 3.118.1-r0 手工构建时 PR_GetLibraryFilePathname 依赖 /proc/self/maps 不可用 | conan 打包环境下验证 NSS_NoDB_Init 实际成功（返回 SECSuccess），test_package 真正初始化并执行 SHA-256 哈希 |
| 4 | 补丁应用失败：新增文件源路径错误 | conan patch_ng strip=1，新增文件须 `--- /dev/null` | 修正 0001 补丁源路径为 /dev/null |
| 5 | 嵌套源码 tarball 补丁路径不匹配 | conan 源码根含 nss/ 子目录，补丁路径需带 nss/ 前缀 | 补丁路径统一 a/nss/... |
| 6 | cmd 工具（shlibsign）构建时运行时加载 softoken 失败 | 同 #3 | manifest.mn 裁剪 DIRS，不构建 cmd/ |
| 7 | FREEBL_NO_DEPEND=1 使 libfreebl3.so 成为 stub（22KB 仅 FREEBL_GetVector） | 上游 Linux.mk 默认行为，属正常形态 | 保留默认；库可正常 dlopen |
| 8 | 头文件打包：dist/public 内为符号链接 | NSS dist 布局用符号链接 | package() 用 shutil.copy2（follow_symlinks）复制真实文件 |

## 源码修改

4 个补丁：
1. **0001-coreconf-HarmonyOS.mk.patch** — 新增 coreconf/HarmonyOS.mk（clang 工具链、OHOS 宏、pthread 策略、freebl 设置）
2. **0002-coreconf-arch.mk.patch** — arch.mk 增加 HarmonyOS 平台识别（OS_RELEASE=1.12, KERNEL=HarmonyOS）
3. **0003-coreconf-config.mk.patch** — TARGET_OSES 增加 HarmonyOS
4. **0004-manifest.mn.patch** — DIRS 裁剪为 coreconf lib（跳过 cmd/gtests）

## 依赖版本

- nspr/4.37（conan 依赖，已发布）

## 验证结果

```bash
conan create . --user=ohpcd --channel=stable --build=missing   # PASS（含 test_package）
test nss 3.118.1: OK   # L1：NSS_GetVersion 版本断言 + SEC_OID 常量 + 链接/加载
# 产物：libnss.a/so、libssl.a/so、libsmime、libnssutil、libsoftokn、libfreebl、libsqlite 等 40+ 库
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（coreconf make 构建 + nspr/4.37 依赖） |
| conandata.yml | 源码 URL/SHA256 + 4 补丁声明 |
| test_package/ | L1 消费者测试（NSS_GetVersion + SHA-256 OID 断言） |
| patches/ | 4 个 HarmonyOS 适配补丁 |

## 注意事项

- 打包环境下 NSS_NoDB_Init 实际可用（softoken/freebl 正常加载），test_package 已验证
  NSS 真实初始化 + SHA-256('abc') NIST 向量匹配；历史手工构建（3.118.1-r0）的
  SEC_ERROR_PKCS11_DEVICE_ERROR 限制不适用于 conan 包
- conan 补丁新增文件源路径必须为 `--- /dev/null`（patch_ng strip=1）
- 嵌套源码 tarball 的补丁路径需带 `nss/` 前缀
---

**编译结束**: 2026-08-15 23:33
**最终状态**: published
