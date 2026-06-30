# libvo-aacenc 0.1.3 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-03
- 编译器: clang (通过 clang-wrapper)
- 目标平台: aarch64-unknown-linux-ohos
- 状态: built

## 编译步骤

1. **源码解压**：`mkdir -p ~/tmp/builds/libvo-aacenc-0.1.3.orig && tar xf ~/tmp/libvo-aacenc-0.1.3.tar.gz -C ~/tmp/builds/libvo-aacenc-0.1.3.orig --strip-components=1 && cp -a .orig .work`

2. **初始化编译上下文**：`python3 $SKILL_ROOT/scripts/ohc-run.py init-build libvo-aacenc 0.1.3 --url=... --no-download`

3. **平台修复（3处源码修改）**：
   - 替换 config.guess/config.sub 为 OHOS-aware 版本
   - sed 修复 configure 中 umask 077→022
   - 创建 gcc→clang-wrapper 符号链接

4. **Configure**：`CC=~/tmp/bin/clang-wrapper ./configure --prefix=$DEFAULT_PREFIX`
   - 正确识别平台为 aarch64-unknown-linux-ohos
   - 自动检测到不支持共享库，仅编译静态库

5. **Make**：`make -j1` → 29 个 .lo 文件 → libvo-aacenc.a (154KB)
   - 2 条非阻塞警告：__inline 宏重定义、多余括号比较

6. **Staging 安装**：`make install DESTDIR=$TEST_PREFIX`
   - 静态库 libvo-aacenc.a、7 个头文件、pkg-config 文件

7. **本地安装**：`make install`（模拟用户部署状态）

8. **打包**：`ohc-run.py package` → libvo-aacenc-0.1.3-ohos-aarch64.tar.gz (195KB)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure conftest 无法执行 | E064: OHOS 要求 ELF 签名后才能执行二进制 | 使用 clang-wrapper 作为 CC，绕过 conftest 执行限制 |
| 2 | config.guess/sub 不识别 OHOS | E007: 原始脚本无法识别 aarch64-unknown-linux-ohos | 从已成功编译的 mcpp 归档复制 OHOS-aware 版本替换 |
| 3 | configure 中 umask 077 导致文件不可读 | E011: umask 077 创建 0600 权限文件 | sed 将 umask 077 替换为 umask 022 |
| 4 | configure 检查 gcc 失败 | E064: 部分 configure 硬编码检测 gcc | 创建 gcc→clang-wrapper 符号链接 + 加入 PATH |

## 源码修改

| 文件 | 补丁 | 修改内容 |
|------|------|----------|
| config.guess | 0001-config.guess.patch (+290/-306) | 替换为 OHOS-aware 版本，识别 aarch64-unknown-linux-ohos |
| config.sub | 0002-config.sub.patch (+78/-252) | 替换为 OHOS-aware 版本，支持 ohos 目标系统 |
| configure | 0003-configure.patch (+2/-2) | 第 12786、12791 行 umask 077→022 |

## 依赖版本

无外部编译依赖（纯 C 库，仅需 clang 编译器）。

## 验证结果

```bash
# pkg-config 验证
pkg-config --modversion vo-aacenc  # → 0.1.3（预期）
pkg-config --libs vo-aacenc        # → -L/usr/local/lib -lvo-aacenc
pkg-config --cflags vo-aacenc      # → -I/usr/local/include

# 静态库验证
llvm-nm /storage/Users/currentUser/usr/local/lib/libvo-aacenc.a | head
# → 显示 AAC 编码相关符号（cmnMemory、voAACEncInit 等）

# 质量门禁
G1-G4: PASS
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libvo-aacenc-0.1.3-ohos-aarch64.tar.gz | 195KB | 预编译包（静态库+头文件+pkg-config） |
| 0001-config.guess.patch | 42KB | OHOS 平台识别补丁 |
| 0002-config.sub.patch | 29KB | OHOS 平台识别补丁 |
| 0003-configure.patch | 889B | umask 权限修复补丁 |

## 注意事项

- 该库仅编译为静态库（OHOS linker 不支持共享库生成）
- 需使用 clang-wrapper 作为 CC，不能直接使用 clang
- 需创建 gcc→clang-wrapper 符号链接并加入 PATH
- pkg-config 文件路径为 `/storage/Users/currentUser/usr/local/lib/pkgconfig/vo-aacenc.pc`

---
---

**编译结束**: 2026-06-03 14:42
**最终状态**: built
