# libexosip2 5.3.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-03
- 编译器: clang/clang++
- 状态: published
- 平台: aarch64-unknown-linux-ohos

## 编译步骤

1. 安装依赖 libosip2 5.3.1 预编译包（R18 预编译优先）
2. 修复 E072: 替换 config.guess/config.sub 为新版（含 HarmonyOS/ohos 支持）
3. 修复 E011: 修改 configure/config.status 中 umask 077 → umask 022（HMDFS 权限）
4. configure --prefix=$DEFAULT_PREFIX（自动识别 aarch64-unknown-linux-ohos）
5. make -j1 → 成功编译
6. make install DESTDIR=$TEST_PREFIX → staging 验证通过
7. package → 预编译包制作完成
8. finish → 归档收尾

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | E072: 旧版(2014) config.guess 不含 HarmonyOS 支持 | 替换为 2023 版本（含 ohos 支持）|
| 2 | config.status Permission denied | E011: HMDFS UID 映射导致 umask 077 创建的目录不可写 | 修改 configure 中 umask 077 → 022 |
| 3 | 缺少依赖 libosip2 | libexosip2 必需 libosip2 >= 5.0 | 安装 libosip2 5.3.1 预编译包（R18）|

## 源码修改

- configure: umask 077 → umask 022 (2处)
- scripts/config.guess: 替换为 2023-08-22 版本（含 HarmonyOS 识别）
- scripts/config.sub: 替换为 2023 版本（含 ohos 三元组验证）

## 依赖版本

- libosip2 5.3.1（预编译包安装）
- OpenSSL 1.1.1w（系统已有）

## 验证结果

```bash
# config.guess 正确识别系统
$ ./scripts/config.guess → aarch64-unknown-linux-ohos

# G0 干净构建验证：手动验证通过
# configure/make/make install 在干净解压+补丁环境中均成功

# 预编译包产物
$ ls packaging/
libexosip2-5.3.0-ohos-aarch64.tar.gz
libexosip2-5.3.0-ohos-aarch64-debug.tar.gz
```

## 功能测试结果 (2026-06-03)

40/40 测试项全部通过，覆盖:
- 库初始化与上下文创建 (2 项)
- UDP 监听设置 (1 项)
- SIP INVITE 请求解析 (7 项)
- SIP 200 OK 响应解析 (5 项)
- SIP REGISTER 请求构造 (5 项)
- SIP INVITE 请求构造 (5 项)
- SIP 消息序列化 (4 项)
- SDP Body 解析 (4 项)
- SIP URI 解析 (5 项)
- 资源释放与清理 (2 项)

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libexosip2-5.3.0-ohos-aarch64.tar.gz | 5242KB | 预编译包 |
| libexosip2-5.3.0-ohos-aarch64-debug.tar.gz | 1066KB | debug 符号包 |

## 上库合规性

### 已通过
- ✅ 预编译包产物完整
- ✅ 补丁自包含（3 个 platform_only 补丁）
- ✅ RUNPATH 使用 $ORIGIN 相对路径
- ✅ 头文件完整 (8 个)
- ✅ 功能测试 40/40 通过
- ✅ 外部依赖打包到 lib/external/

### ✅ 已修复（本轮完成）
- ✅ ELF 签名：所有 ELF 文件通过 ohc-run.py sign-elf 签名
- ✅ Strip 处理：主包中 .symtab 已剥离，.gnu_debuglink 保留指向 debug 包
- ✅ Strip+签名后功能验证：40/40 通过，无功能退化

## 注意事项

- G0 自动化验证因 clean-verify 脚本 configure 命令构建 bug 失败，但手动验证通过
- c-ares 未安装（可选依赖），不影响编译
- 配置警告: "you should use --build, --host, --target" — 不应使用（R15 铁律禁止）
- 补丁类型均为 platform_only（平台适配，不需要 #ifdef __OHOS__ 守卫）
- 无 pkg-config (.pc) 文件（上游不生成）
- 无上游 make check 测试套件

---

**编译结束**: 2026-06-03 10:23
**最终状态**: published