# tass64 1.60.3243 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-06-08
- 编译器: clang/clang++
- 状态: published

## 编译步骤

### Step 1: 初始化
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build tass64 1.60.3243 --url=https://downloads.sourceforge.net/project/tass64/source/64tass-1.60.3243-src.zip
```

**输出**:
- 源码下载并解压到 `~/tmp/builds/tass64-1.60.3243.work`
- 归档目录创建于 `archives/t/tass64/1.60.3243/`
- 基线指纹: 183 个文件

### Step 2: 编译

tass64 使用纯 Makefile 构建系统（不是 autotools），直接使用 make 编译。

**重要**: 鸿蒙系统不支持 GNU make 的 jobserver FIFO 机制（E074），必须使用单线程编译。

```bash
cd /storage/Users/currentUser/tmp/builds/tass64-1.60.3243.work
make CC=clang CFLAGS="-fPIC -O2" prefix=$DEFAULT_PREFIX
```

**编译输出**: 无错误，成功生成 64tass 二进制

### Step 3: Staging 安装（DESTDIR 模式）

```bash
mkdir -p $TEST_PREFIX
make install DESTDIR=$TEST_PREFIX prefix=$DEFAULT_PREFIX
```

**安装位置**: `$TEST_PREFIX/$DEFAULT_PREFIX/bin/64tass`

**验证**:
```bash
ls -lh $TEST_PREFIX/$DEFAULT_PREFIX/bin/
# Output: -rwxrwx--- 1 ... 690K ... 64tass
```

### Step 4: 本地安装

模拟用户通过 cmd-pkgs 公共安装脚本部署后的状态：

```bash
make install prefix=$DEFAULT_PREFIX
```

**安装位置**: `~/usr/local/bin/64tass`

### Step 5: 功能验证

```bash
/storage/Users/currentUser/usr/local/bin/64tass --version
# Output: 64tass Turbo Assembler Macro V1.60.3243
```

**实际测试**: 创建 6502 汇编程序并编译，验证功能完整性。详见 `test-report.md`。

### Step 6: 打包

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py package tass64 1.60.3243
```

**打包流程**（9步）:
1. 创建打包目录
2. 复制文件
3. 替换符号链接
4. 收集外部依赖
5. 设置 RPATH
6. Strip 调试符号
7. ELF 签名（鸿蒙必需）
8. 修复执行权限
9. 打包 tar.gz

**生成文件**:
- `tass64-1.60.3243-ohos-aarch64.tar.gz`: 1.3M（主包）
- `tass64-1.60.3243-ohos-aarch64-debug.tar.gz`: 90K（调试符号）

### Step 7: 归档收尾

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py finish tass64 1.60.3243 published
```

**收尾流程**（6步）:
1. 补丁生成（无变更）
2. 归档关闭（manifest → published）
3. 质量门禁验证
4. 归档校验
5. 知识完整性检查
6. 生成 SUMMARY.md

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 知识图谱 |
|---|------|------|----------|----------|
| 1 | make -j2 FIFO 创建失败 | 鸿蒙 SELinux 禁止创建 FIFO（E074） | 使用单线程编译（不使用 -j 参数） | E074 已匹配 |
| 2 | tar_format 错误 | 源码是 zip 格式，manifest 默认 tar.gz | 修改 manifest.yaml 的 tar_format 为 zip | - |
| 3 | build.system 错误 | tass64 使用纯 Makefile，非 autotools | 修改 manifest.yaml 的 build.system 为 makefile | - |

**关键技术点**:
- **E074**: GNU make jobserver 在鸿蒙上不可用，所有使用 `make -j` 的项目需改用单线程
- **DESTDIR 模式**: 使用 `--prefix=$DEFAULT_PREFIX` + `DESTDIR=$TEST_PREFIX` 分离编译和部署路径

## 源码修改

**无补丁，无源码修改**。

源码直接可用，无需任何适配修改。183 个源文件全部保持原样。

## 依赖版本

**无依赖**。

tass64 是独立的 C 程序，仅依赖标准数学库（-lm），无需任何第三方库。

## 验证结果

### 基本验证
```bash
$ 64tass --version
64tass Turbo Assembler Macro V1.60.3243
```

### 功能测试

完整功能测试详见 `reports/test-report.md`，主要测试项：

1. **版本查询**: ✅ PASS
2. **基本汇编**: ✅ PASS（编译 6502 指令集）
3. **列表文件生成**: ✅ PASS
4. **标签文件生成**: ✅ PASS
5. **错误处理**: ✅ PASS（精确定位错误行/列）
6. **命令行选项**: ✅ PASS

**测试覆盖率**: 7/7（100%）

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| tass64-1.60.3243-ohos-aarch64.tar.gz | 1.3M | 预编译包（ELF 签名，可执行） |
| tass64-1.60.3243-ohos-aarch64-debug.tar.gz | 90K | 调试符号包 |

**预编译包内容**:
```
bin/64tass                  # 主二进制
lib/external/               # 外部依赖目录（空）
share/man/man1/64tass.1.gz  # man 手册
share/doc/64tass/           # 文档目录
```

## 归档文件清单

### 软件级（archives/t/tass64/）
- `README.md`: 软件描述
- `manifest.yaml`: 软件元数据索引

### 版本级（archives/t/tass64/1.60.3243/）
- `manifest.yaml`: 编译元数据
- `notes.md`: 适配笔记（本文件）
- `packaging/`: 预编译包（2个）
- `reports/`: 编译报告（2个）
  - `quality-report.md`: 质量门禁报告
  - `test-report.md`: 功能测试报告

## 注意事项

1. **构建系统**: 纯 Makefile，非 autotools。manifest.yaml 的 `build.system` 必须设置为 `"makefile"`
2. **源码格式**: zip 格式，manifest.yaml 的 `tar_format` 必须设置为 `"zip"`
3. **并行编译**: 鸦蒙不支持 make jobserver（E074），禁止使用 `-j` 参数
4. **测试套件**: 无自动化测试（无 make check），需手动功能验证
5. **依赖**: 无任何依赖，编译简单快速
6. **ELF 签名**: 预编译包必须经过 ELF 签名才能在鸿蒙上执行

---

**编译结束**: 2026-06-08 16:55
**最终状态**: published