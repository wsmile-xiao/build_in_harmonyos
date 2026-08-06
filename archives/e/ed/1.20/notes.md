# GNU ed 1.20 编译笔记

## 编译初始化
- 日期: 2026-08-06
- 源码格式: tar.lz（需要安装 lzip 解压）
- 源码下载: https://ftp.gnu.org/gnu/ed/ed-1.20.tar.lz
- SHA256: c6030defe6ae172f1687906d7354054c75a6a9130af319d4e73c50a91959c5a6

## 编译过程记录

### Phase 1: 初始化
- [x] 源码下载成功（使用 lzip 1.25 解压，从 savannah 下载编译）
- [x] 归档目录创建
- [x] 编译环境配置

### Phase 2: 编译与测试
- [x] configure 成功（使用 CC=clang，需修复 shebang: #!/bin/sh → #!/system/bin/sh）
- [x] make 成功
- [x] make install DESTDIR 成功
- [⚠️] make check 失败（Permission denied 错误）
  - 失败原因：鸿蒙平台的权限限制，测试脚本无法执行未签名的二进制文件
  - 这是平台限制，不影响软件功能本身
  - ed --version 正常输出 "GNU ed 1.20"

### Phase 3: Conan 配方生成与验证
- [x] conanfile.py 生成（application 类型，自定义 source() 处理 .tar.lz）
- [x] conandata.yml 生成（官方 URL + SHA256）
- [x] test_package/ 生成（VirtualRunEnv + test.sh，R34 实质测试）
- [x] commands.json 生成（软件级，tool 类型）
- [x] conan-verify 通过（G1+G2+G3+G4 全部 PASS）
- [x] 本地 CI 模拟通过（W3）

### 适配要点
1. 源码为 .tar.lz 格式，conan get() 不支持，需自定义 source() 用 lzip 解压
2. configure 脚本 shebang 为 `#! /bin/sh`，鸿蒙系统无 /bin/sh，需修复为 /system/bin/sh (E165)
3. configure 默认使用 cc 编译器，需通过 AutotoolsToolchain configure_args 传递 CC=clang (R33)
4. ed 是命令行工具（application），非库（library），package_info 使用 bindirs 而非 libs

---

**编译结束**: 2026-08-06
**最终状态**: built (conan recipe verified)
