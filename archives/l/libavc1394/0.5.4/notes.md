# libavc1394 0.5.4 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-30
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. **初始化编译环境**
   ```bash
   ohc-run.py init-build libavc1394 0.5.4 --url=file://~/tmp/sources/libavc1394_0.5.4.orig.tar.gz
   ```

2. **安装依赖**
   ```bash
   sh ~/tmp/install.sh libraw1394 2.1.2
   export PKG_CONFIG_PATH=$HOME/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
   ```

3. **修改 config.guess 和 config.sub**
   在脚本开头添加 HarmonyOS 平台检测，返回 aarch64-unknown-linux-gnu。

4. **修改 configure 脚本**
   修改临时目录创建路径，使用 `$TMPDIR/confXXXXXX` 而不是 `./confXXXXXX`。

5. **执行 configure**
   ```bash
   ./configure --prefix=/storage/Users/currentUser/usr/local
   ```

6. **修改 Makefile 禁用 panelctl**
   panelctl 依赖 GNU argp 函数（不可用），从 bin_PROGRAMS 中移除。

7. **编译**
   ```bash
   make -j2
   ```

8. **安装**
   ```bash
   make install DESTDIR=/storage/Users/currentUser/tmp/test-install-libavc1394-0.5.4
   make install  # 本地安装验证
   ```

9. **打包**
   ```bash
   ohc-run.py package libavc1394 0.5.4
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别平台 | HarmonyOS 未在 2009 年的 config.guess 中定义 | 在脚本开头添加 HarmonyOS 检测，返回 aarch64-unknown-linux-gnu |
| 2 | 缺少依赖 libraw1394 | configure 检测到依赖缺失 | 安装预编译包 libraw1394/2.1.2 |
| 3 | configure 创建临时文件失败 | config.status 尝试在当前目录创建临时文件，权限问题 | 修改 configure 脚本，使用 `$TMPDIR/confXXXXXX` |
| 4 | panelctl 链接失败 | 缺少 GNU argp 函数 | 从 Makefile 中移除 panelctl 编译目标 |
| 5 | manifest 缺少 build_system 字段 | 脚本期望扁平字段名 | 添加 build_system: autotools |

## 源码修改

| 文件 | 修改内容 |
|------|----------|
| config.guess | 添加 HarmonyOS 平台检测（开头插入） |
| config.sub | 添加 HarmonyOS 平台检测（开头插入） |
| configure | 修改临时目录路径（TMPDIR 支持） |
| test/Makefile | 移除 panelctl 编译目标（编译时修改） |

生成补丁 3 个（仅源文件修改）：
- 0001-config.guess.patch（平台检测）
- 0002-config.status.wrapper.patch（TMPDIR 支持）
- 0003-config.sub.patch（平台检测）

## 依赖版本

- libraw1394/2.1.2（预编译包）

## 功能测试结果

### API 测试 ✅ PASS

测试程序验证了：
- 头文件宏定义正确
- 结构体和枚举定义正确
- 所有 API 函数符号导出
- 编译链接成功

### 硬件测试 ⚠️ SKIP

```bash
~/usr/local/bin/dvcont --help
# 输出：Couldn't get 1394 handle（无硬件，预期行为）

~/usr/local/bin/mkrfc2734 --help
# 输出：couldn't get handle（无硬件，预期行为）
```

### pkg-config ✅ PASS

```bash
pkg-config --modversion libavc1394
# 输出：0.5.4

pkg-config --cflags libavc1394
# 输出：-I~/usr/local/include

pkg-config --libs libavc1394
# 输出：-L~/usr/local/lib -lavc1394 -lrom1394 -lraw1394
```

### 平台兼容性 ✅ PASS

- ELF 格式：arm64 LSB
- 动态链接器：/lib/ld-musl-aarch64.so.1
- libc 依赖：musl libc
- 平台检测：config.guess/config.sub 已适配

### 可用性判定

**该软件可以在鸿蒙平台上正常使用**

前提条件：
1. 目标设备需有 IEEE 1394 (FireWire) 硬件支持
2. 内核需加载 raw1394 模块
3. 安装时需正确配置库路径

详细报告见：reports/functional-test-report.md

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libavc1394-0.5.4-ohos-aarch64.tar.gz | 485KB | 预编译包（主包） |
| libavc1394-0.5.4-ohos-aarch64-debug.tar.gz | 327KB | 调试符号包 |

## 注意事项

1. **硬件依赖**：该库需要 IEEE 1394（FireWire）硬件支持，无硬件时命令行工具会报错（正常现象）。
2. **panelctl 工具缺失**：因 GNU argp 依赖不可用，panelctl 工具未编译。
3. **知识提取**：config.guess/platform detection 已在知识图谱（E007），configure TMPDIR 和 GNU argp 缺失处理已记录在 knowledge_gained。

---
**编译结束**: 2026-05-30 16:41
**最终状态**: published