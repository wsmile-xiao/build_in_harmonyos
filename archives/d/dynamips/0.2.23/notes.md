# dynamips 0.2.23 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-17
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 安装依赖：libelf 0.8.13（standalone版本，手动编译安装）+ libpcap 1.10.6（已安装）+ argp-standalone 1.5.0（预编译包）+ musl-fts 1.2.7（预编译包）+ musl-obstack 1.2.3（预编译包）
2. cmake configure（在build子目录中）：
   ```
   cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DDYNAMIPS_ARCH=nojit -DANY_COMPILER=1 -DCMAKE_C_COMPILER=clang -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_PREFIX_PATH=$DEFAULT_PREFIX
   ```
3. make -j2
4. make install DESTDIR=$TEST_PREFIX（staging）
5. make install（本地安装）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake_minimum_required VERSION 2.8 与 CMake 4.1.2 不兼容 | CMake 4.x移除了对<3.5版本的兼容 | 添加 -DCMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 2 | 非gcc/clang编译器检查失败 | cmake的compiler check拒绝非标准CC | 添加 -DANY_COMPILER=1 |
| 3 | libelf缺失 | musl系统不自带libelf | 编译standalone libelf 0.8.13手动安装 |
| 4 | aarch64不支持x86/amd64 JIT | 架构检测无x86/amd64 | 设置 -DDYNAMIPS_ARCH=nojit |

## 依赖版本

- libelf 0.8.13（standalone）
- libpcap 1.10.6
- argp-standalone 1.5.0
- musl-fts 1.2.7
- musl-obstack 1.2.3

## 验证结果

```bash
$ dynamips --version
Cisco Router Simulation Platform (version 0.2.23-nojit/HarmonyOS stable)
Copyright (c) 2005-2011 Christophe Fillot.
Build date: Jun 17 2026 04:14:24
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| dynamips | 790K | 主模拟器二进制(nojit模式) |
| nvram_export | 34K | NVRAM配置导出工具 |

## 注意事项

- aarch64平台只能用nojit模式（无JIT重编译），性能较低
- OSNAME自动检测为HarmonyOS

### 对话 #1: 编译问题排查

**时间**: 2026-06-17 04:00–04:30

1. 初始cmake configure失败：CMake 4.x不兼容cmake_minimum_required(VERSION 2.8)
   - 决策：添加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`

2. 编译器检查拒绝clang: cmake的compiler check只认可gcc
   - 决策：添加 `-DANY_COMPILER=1` 跳过检查

3. aarch64架构不支持JIT: 源码只支持x86/amd64 JIT
   - 决策：设置 `-DDYNAMIPS_ARCH=nojit`

4. libelf缺失: elfutils无预编译包
   - 决策：编译standalone libelf 0.8.13

5. argp/fts/obstack缺失: 预编译包安装解决

**结论**: cmake configure + make + make install 全流程完成

### 对话 #2: 测试与归档

**时间**: 2026-06-17 04:15–04:28

1. verify-build → PASS (G1-G4全通过)
2. package → 打包成功 (dynamips-0.2.23-ohos-aarch64.tar.gz + debug.tar.gz)
3. finish → 3次尝试，第3次成功（解决knowledge_gained格式问题）
4. 知识图谱：E081/E082/E083 三条草稿创建并通过检查

**结论**: 归档状态published，编译流程完整结束

### 对话 #3: 测试报告补充

**时间**: 2026-06-17 17:14–17:27

1. 执行10项真实测试：版本信息、ELF完整性、依赖库验证、hypervisor启动等
2. 测试报告从简要版升级为详细中文版（10项测试用例）
3. 补充归档缺失的README.md（软件级）
4. 补充notes.md对话记录

**结论**: 归档完整，缺失项0
---

**编译结束**: 2026-06-17 17:32
**最终状态**: published
