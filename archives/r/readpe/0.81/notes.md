# readpe 0.81 编译笔记

## 编译信息
- 软件名称: readpe (pev 工具包的一部分)
- 版本: 0.81
- 编译日期: 2026-06-16
- 编译状态: built (主程序编译成功，plugins 未编译)

## 构建系统
- 类型: 纯 Makefile
- 无 configure 脚本
- 直接使用 make 编译

## 依赖
- OpenSSL (libssl, libcrypto): 已安装于 ~/usr/local
- 无其他必需依赖

## 编译过程

### 1. 源码获取
- URL: https://downloads.sourceforge.net/project/pev/pev-0.81/pev-0.81.tar.gz
- 手动下载后使用 file:// URL 初始化

### 2. 源码修复

#### error.c - strerror_r 兼容性修复
**问题**: OpenHarmony 使用 XSI-compliant strerror_r（返回 int），但代码因定义 `_GNU_SOURCE` 而期望 GNU 版本（返回 char*）。

**修复**: 在 `lib/libpe/error.c` 第 99 行添加 OpenHarmony 检测：
```c
#if defined(__DARWIN_C_LEVEL) || defined(__OHOS__) // XSI-compliant
```

**追踪**: 已通过 `track-edit add` 记录

#### src/Makefile - 链接方式修复
**问题**: 原始 Makefile 使用 `-lpe` 链接动态库，但 libpe 在 OpenHarmony 上未正确生成 .so 文件。

**修复**:
1. 手动创建静态库 `libpe.a`（排除 libudis86 避免 pedis 重复定义）
2. 修改 LDFLAGS: `-lpe` → `$(LIBPE)/libpe.a`
3. 使用 `-fuse-ld=bfd` 避免 lld 的 libxml2 依赖问题

### 3. 编译命令
```bash
export PKG_CONFIG_PATH="$HOME/usr/local/lib/pkgconfig:$HOME/usr/local/lib/external/pkgconfig"
export LD_LIBRARY_PATH="$HOME/usr/local/lib:$HOME/usr/local/lib/external:/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
export CFLAGS="-I$HOME/usr/local/include -I$HOME/usr/local/include/external"
export LDFLAGS="-L$HOME/usr/local/lib -L$HOME/usr/local/lib/external -fuse-ld=bfd"
cd lib/libpe && llvm-ar rcs libpe.a build/*.o build/libfuzzy/*.o && llvm-ranlib libpe.a
cd src && make -j1
```

### 4. ELF 签名
所有二进制文件需要 ELF 签名才能在 OpenHarmony 上执行：
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf readpe
```

### 5. 安装（DESTDIR 模式）
由于 OpenHarmony 缺少 `install` 命令，手动复制：
```bash
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/bin $TEST_PREFIX/$DEFAULT_PREFIX/share/pev
cp src/build/readpe src/build/rva2ofs src/build/ofs2rva ... $TEST_PREFIX/$DEFAULT_PREFIX/bin/
cp src/userdb.txt $TEST_PREFIX/$DEFAULT_PREFIX/share/pev/
```

## 编译产物
- readpe: 247K
- rva2ofs: 235K
- ofs2rva: 235K
- pehash: 243K
- pesec: 243K
- pescan: 247K
- pepack: 239K
- pestr: 239K
- pedis: 451K
- peres: 247K
- peldd: 243K

## 未完成项
- **plugins**: 未编译（需要共享库支持，Makefile 不正确处理 HarmonyOS）
- **manpages**: 未安装（gzip 命令失败）

## 测试结果
- readpe 可执行，输出 plugins 警告（预期，因为 plugins 目录不存在）
- 未提供示例 PE 文件进行完整功能测试

## 知识提取
- **E编号候选**: strerror_r 兼容性问题 → 需添加到知识图谱
- **平台真理**: OpenHarmony 使用 XSI-compliant strerror_r
- **构建模式**: 简单 Makefile 项目需要手动创建静态库

---
**编译结束**: 2026-06-16 10:17
**最终状态**: built
---

**编译结束**: 2026-06-16 10:32
**最终状态**: built
