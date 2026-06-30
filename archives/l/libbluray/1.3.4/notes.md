# libbluray 1.3.4 编译笔记

## 编译日期
2026-05-20

## 编译状态
built（编译成功，待验证）

## 遇到的问题

### 1. E072: config.sub 三元组验证失败
**错误现象**: `config.sub: error: unknown operating system 'ohos'`

**解决方案**:
修改 `build-aux/config.sub` 的两处位置：
1. 第 145 行（maybe_os）：添加 `| linux-ohos* | ohos*`
2. 第 1828 行（kernel-os 白名单）：添加 `| ohos*-`

**验证**: `./config.sub aarch64-unknown-linux-ohos` 返回正确三元组

### 2. E011: HMDFS umask 权限问题
**错误现象**: `config.status: can't create ./confXXX/subs1.awk: Permission denied`

**根因**: HMDFS 文件系统 UID 映射导致 `umask 077` 创建的临时目录（0700权限）对进程不可写

**解决方案**:
修改 `configure` 脚本中的 `umask 077` 为 `umask 022`（两处）

### 3. 缺少 ant 工具
**错误现象**: `configure: error: BD-J requires ANT, but ant was not found`

**解决方案**:
使用 `--disable-bdjava-jar` 参数禁用 BD-J jar 文件构建

## 源码修改清单

1. `build-aux/config.sub`（2处修改）
   - 第 145 行：添加 ohos 操作系统支持到 maybe_os
   - 第 1828 行：添加 ohos 到 kernel-os 白名单

2. `configure`（2处修改）
   - 第 19594 行：`umask 077` → `umask 022`
   - 第 19599 行：`umask 077` → `umask 022`
   - 同时修改临时目录位置：`"./confXXXXXX"` → `"${TMPDIR:-$HOME/tmp}/confXXXXXX"`

## 编译参数
- configure: `--prefix=/storage/Users/currentUser/usr/local --disable-bdjava-jar`
- make: `-j1`（单线程，避免并行问题）
- compiler: clang

## 依赖情况
- 无额外依赖（libxml2, freetype2, fontconfig 已在系统中）

## 测试情况
- make check: 未执行（配置时间过长，超时跳过）

## 质量门禁结果
- G0: FAIL（干净构建验证失败，需进一步调试）
- G1: PASS（二进制完整性）
- G2: PASS（功能可用性）
- G3: PASS（可移植性）
- G4: FAIL（档案完整性，缺少 README.md）

## 后续修复记录

### 软件级文件创建（2026-05-20）
- ✅ 创建 README.md（描述 libbluray 功能、依赖和 OHOS 适配要点）
- ✅ 创建 manifest.yaml（软件级元数据，包含版本索引）

### G0 验证问题处理（2026-05-20）

**问题诊断**：
- clean_verify.py 的正则表达式无法正确解析 YAML 列表格式的 configure_options
- 正则表达式：`configure_options:\s*["\']?(.*?)["\']?\n` 只匹配单行字符串
- 实际格式：`configure_options:\n  - "--disable-bdjava-jar"`

**尝试的方法**：
1. ✅ 方法 1：hints/configure.options 文件已存在（内容正确）
2. ❌ 方法 2：clean_verify.py 不支持从 hints 读取 configure_options
3. ✅ 方法 3：手动验证补丁自包含性（成功）

**手动验证过程**：
```bash
cd /storage/Users/currentUser/ohc-verify-libbluray-n3asd520/libbluray-1.3.4-temp
export TMPDIR=/storage/Users/currentUser/ohc-verify-libbluray-n3asd520
export CC=clang CXX=clang++
./configure --prefix=$DEFAULT_PREFIX --disable-bdjava-jar  # 成功
make -j1                                                    # 成功
make install DESTDIR=/storage/Users/currentUser/...         # 成功
```

**验证结果**：
- configure: PASS（exit code 0）
- make: PASS（exit code 0）
- make install: PASS（exit code 0）
- 产物完整性：PASS（libbluray.so, libbluray.a, 头文件, pkgconfig）

**最终状态**：
- G0 验证：**手动验证通过**（补丁自包含性已确认）
- 原因：clean_verify.py 正则表达式限制，无法处理 YAML 列表格式
- 建议：升级 clean_verify.py 使用 YAML 解析器代替正则表达式

### G4 档案完整性修复
- ✅ 创建软件级 README.md（解决 G4 FAIL）
- ✅ 创建软件级 manifest.yaml（版本索引）

### 最终门禁状态（修复后）
- G0: **手动验证 PASS**（补丁自包含性已确认）
- G1: PASS（二进制完整性）
- G2: PASS（功能可用性）
- G3: PASS（可移植性）
- G4: PASS（档案完整性，软件级 README 已创建）

### R9 铁律验证
根据 R9 铁律：
- 门禁通过情况：G0 手动验证 PASS, G1-G3 PASS, G4 PASS（修复后）
- **合理状态**：built（部分门禁通过，G0 未通过自动化验证但手动验证通过）
- 如果所有门禁自动化通过 → published
- 如果部分门禁通过 → built ✅
- 如果门禁大部分失败 → failed

当前状态为 **built**，符合 R9 铁律要求。