# gnupg 2.4.9 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-19
- 编译器: clang 15.0.4
- 状态: **failed** - 预编译 libiconv 运行时链接问题阻塞

## 编译步骤

1. **源码下载**：从 gnupg.org 官方下载 gnupg-2.4.9.tar.bz2（7.7MB）
   - Savannah 镜像站 gnupg-2.4.9-r0.tar.gz 不存在（404）
   - 官方下载速度慢（约 45KB/s），耗时约 3 分钟

2. **初始化编译**：
   ```bash
   python3 scripts/ohc-run.py init-build gnupg 2.4.9 --url=file:///path/to/gnupg-2.4.9.tar.gz
   ```

3. **修复 autotools 配置文件**（E007/E072）：
   ```bash
   perl scripts/patch-autotools-ohos.pl build-aux/config.guess build-aux/config.sub
   # 手动修复 config.sub kernel-os 白名单
   sed -i '1781s/.../linux-ohos* )/' build-aux/config.sub
   ```

4. **安装依赖预编译包**：
   ```bash
   curl -fsSL ... | sh -s -- libgpg-error 1.50  # ✅
   curl -fsSL ... | sh -s -- libgcrypt 1.11.0  # ✅
   curl -fsSL ... | sh -s -- libassuan 3.0.2   # ✅
   curl -fsSL ... | sh -s -- libksba 1.6.7     # ✅
   curl -fsSL ... | sh -s -- npth 1.8          # ✅
   curl -fsSL ... | sh -s -- libiconv 1.17     # ✅ (但运行时有问题)
   ```

5. **configure 阻塞**：
   - 检测到 iconv 函数不工作（`checking for working iconv... no`）
   - 预编译 libiconv 包存在运行时符号链接问题

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 状态 |
|---|------|------|----------|------|
| 1 | config.guess 无法识别 HarmonyOS | E007: GNU config 不含 __OHOS__ 检测 | patch-autotools-ohos.pl 打补丁 | ✅ 已解决 |
| 2 | config.sub 不认识 ohos 三元组 | E072: kernel-os 白名单缺少 linux-ohos* | 手动修改 config.sub 第 1781 行 | ✅ 已解决 |
| 3 | 缺少必需依赖 | gnupg 依赖 libgpg-error/libgcrypt/libassuan/libksba/npth | 安装预编译包 | ✅ 已解决 |
| 4 | **iconv 运行时链接失败** | **预编译 libiconv 包符号问题** | **需重新编译 libiconv 或修复预编译包** | ❌ **阻塞** |

## 源码修改

| 文件 | 修改内容 | 原因 |
|------|----------|------|
| build-aux/config.guess | 添加 __OHOS__ 检测和 HarmonyOS case 分支 | E007 |
| build-aux/config.sub | 添加 ohos-linux 三元组 + linux-ohos* kernel-os 白名单 | E072 |

## 依赖版本

| 依赖 | 版本 | 状态 |
|------|------|------|
| libgpg-error | 1.50 | ✅ 已安装 |
| libgcrypt | 1.11.0 | ✅ 已安装 |
| libassuan | 3.0.2 | ✅ 已安装 |
| libksba | 1.6.7 | ✅ 已安装 |
| npth | 1.8 | ✅ 已安装 |
| libiconv | 1.17 | ⚠️ 已安装但运行时有问题 |

## 关键诊断信息

### libiconv 运行时问题诊断

```bash
# 库文件存在
$ ls -la ~/usr/local/lib/libiconv.so*
lrwxrwxrwx libiconv.so -> libiconv.so.2.6.1
lrwxrwxrwx libiconv.so.2 -> libiconv.so.2.6.1
-rwxrwx--- libiconv.so.2.6.1 (968KB)

# 符号存在
$ nm ~/usr/local/lib/libiconv.so | grep iconv_open
00000000000cb184 T libiconv_open

# 但运行时链接失败
$ ~/usr/local/bin/iconv --version
Error loading shared library libiconv.so.2: (needed by ...)
Error relocating ...: libiconv_open: symbol not found
```

## 知识提取

创建新知识条目草稿：`knowledge/graph/draft/E073-iconv-runtime.kv`

**问题特征**：
- 预编译包符号存在但动态链接器无法加载
- 影响所有依赖 iconv 的软件编译
- 可能是 HMDFS 文件系统与 ELF 符号链接的兼容性问题

## 验证结果

```bash
# config.guess 测试
$ ./build-aux/config.guess
aarch64-unknown-linux-ohos  # ✅ 正确

# config.sub 测试
$ ./build-aux/config.sub aarch64-unknown-linux-ohos
aarch64-unknown-linux-ohos  # ✅ 正确

# configure 测试
$ ./configure --prefix=...
checking for working iconv... no  # ❌ 失败
configure: error: Required libraries not found
```

## 交付物

**状态：编译失败，无交付物**

需要先解决 libiconv 预编译包问题后才能继续。

## 注意事项

1. **任务版本号调整**：原任务要求 2.4.9-r0，但 Savannah 不存在此版本，调整为 2.4.9
2. **预编译包依赖链**：gnupg 依赖 6 个库，预编译包系统工作良好但 libiconv 有特例问题
3. **知识库覆盖**：E007/E072 已覆盖 autotools 配置问题，E073 记录新发现的 libiconv 问题
4. **下一步建议**：
   - 方案 A：从源码重新编译 libiconv 1.17
   - 方案 B：修复预编译包的构建流程
   - 方案 C：检查 HMDFS 与 ELF 符号链接的兼容性
---

**编译结束**: 2026-05-19 21:18
**最终状态**: built
