# bcal 2.5 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 configure 脚本）
- 编译日期: 2026-06-16
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤

### 1. 初始化
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build bcal 2.5 \
  --url=https://github.com/jarun/bcal/archive/refs/tags/v2.5.tar.gz
```

### 2. 安装依赖
readline 8.2 预编译包（首次安装仅有共享库，缺少头文件，需重装以获取完整头文件和静态库）:
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- readline 8.2
```

### 3. 编译
bcal 是纯 Makefile 项目，使用 PREFIX 和 DESTDIR 参数:
```bash
cd $BUILD_SRC_DIR
make PREFIX=$DEFAULT_PREFIX -j1       # 编译（含 -Werror，clang 下无警告）
make PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX install  # DESTDIR 隔离安装
```

### 4. 本地部署与验证
```bash
make PREFIX=$DEFAULT_PREFIX install    # 不带 DESTDIR，部署到 $DEFAULT_PREFIX
$DEFAULT_PREFIX/bin/bcal -h            # 确认版本 2.5
```

### 5. 打包
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py package bcal 2.5
# 产物: bcal-2.5-ohos-aarch64.tar.gz (585KB)
```

### 6. 收尾
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py finish bcal 2.5 built
# 注意: finish 在 Step 2.5 (G0 clean verify) 因 ImportError 崩溃
# 手动完成了 finalize-archive 和 summary 生成
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | readline 头文件缺失 | readline 8.2 预编译包仅安装了共享库（.so），缺少头文件（readline.h）和静态库（.a） | 重装 readline 8.2 预编译包（`curl install.sh | sh -s -- readline 8.2`） |
| 2 | finish.py ImportError | `from .clean_verify import clean_verify` 导入失败，clean_verify.py 模块不含此函数 | 记录为 skill-feedback F001，手动完成后续步骤 |
| 3 | verify-build 查找路径不一致 | verify-build 默认使用 TEST_PREFIX 查找二进制，但 DESTDIR 模式下二进制在 TEST_PREFIX/DEFAULT_PREFIX 下 | 传入 `--install-prefix=$STAGING_PREFIX` 参数 |

## 源码修改

无。bcal 2.5 原始 Makefile 在 clang 15 下编译通过（含 -Werror），无需任何源码修改或补丁。

## 依赖版本

- readline 8.2（预编译包，提供 libreadline.so.8 + libreadline.a + readline.h）
- ncurses（readline 的间接依赖，已安装静态库版本）

## 验证结果

### 功能验证（22 项全部 PASS）

| 类别 | 测试数 | 结果 |
|------|--------|------|
| 字节单位计算 | 6 | ✅ 全通过 |
| 基数转换 | 3 | ✅ 全通过 |
| 位运算 | 4 | ✅ 全通过 |
| 通用表达式 | 2 | ✅ 全通过 |
| REPL 交互 | 3 | ✅ 全通过 |
| 错误处理 | 4 | ✅ 全通过 |

### 二进制特性

```
文件类型: ELF shared object, 64-bit LSB arm64, dynamic
动态链接器: /lib/ld-musl-aarch64.so.1
NEEEDED: libreadline.so.8, libc.so
文件大小: 113152 字节
版本: 2.5 (通过 bcal -h 确认)
```

### 质量门禁

```
verify-build --install-prefix=$STAGING_PREFIX
G1 二进制完整性: ✅1  (1 个 ELF 二进制)
G2 功能可用性: ⚠️1  (bcal 不支持 --version，仅支持 -h)
G3 可移植性: ⚠️2  (无 RPATH、需 ELF 签名)
G4 档案完整性: ✅  (manifest.yaml 包含 build_system 字段)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bcal-2.5-ohos-aarch64.tar.gz | 585KB | 预编译包（含 ELF 签名、strip、RPATH） |
| bcal-2.5-ohos-aarch64-debug.tar.gz | 153KB | 调试符号包 |

## 注意事项

- bcal 不支持 `--version` 参数（返回 exit 255），仅 `-h` 显示版本（这是程序正常行为）
- bcal 运行时依赖 libreadline.so.8，需确保 readline 预编译包已安装
- Makefile 项目无 configure 脚本，编译使用 `make PREFIX=$DEFAULT_PREFIX`
- finish.py 存在 ImportError 脚本缺陷（F001），导致 G0 步骤无法自动完成

---

**编译结束**: 2026-06-16 03:41
**最终状态**: built
