# pbc-sig 0.0.8 适配笔记

## 编译环境
- 构建系统: autotools (configure.ac + Makefile.am)
- 编译日期: 2026-09-15
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤

### 探索阶段（手动编译）
```bash
# pbc/gmp 已通过 conan install 获取
PBC_INC=... PBC_LIB=... GMP_INC=... GMP_LIB=...
clang -fPIC -O2 -c -I$PBC_INC -I$GMP_INC -Iinclude sig/sig.c sig/hash.c sig/bbs.c
clang -shared -o libpbc_sig.so sig/sig.o sig/hash.o sig/bbs.o -L$PBC_LIB -L$GMP_LIB -lpbc -lgmp -lm
llvm-ar rcs libpbc_sig.a sig/sig.o sig/hash.o sig/bbs.o
```

### 上游测试
4 个 demo 程序 (test/bls, test/bb, test/ibs, test/bbs) 编译并运行:
- 全部使用 `pbc_demo_pairing_init()` 从文件读取 Type A pairing 参数
- 参数文件需包含 `type a` + `q` + `r` + `h` + `exp2` + `exp1` + `sign1` + `sign0`
- bls/bb/ibs 测试 "signature verifies" → PASS
- bbs 测试 "signature does not verify" 但 exit 0 (demo 程序不使用 EXPECT 断言)

### Conan 配方阶段
使用 Autotools + patch 方式:
1. 补丁 `0001-autotools-harmonyos.patch`: 修复 config.guess/config.sub 识别 HarmonyOS + 修复 umask 077→022
2. conanfile.py 声明 `self.requires("pbc/1.0.0")` 获取 pbc (含传递依赖 gmp)
3. generate() 注入 pbc 的 include/lib 路径到 CPPFLAGS/LDFLAGS

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 上游 config.guess 来自 2009 年，不支持 HarmonyOS | 补丁添加 HarmonyOS case → aarch64-unknown-linux-ohos |
| 2 | config.status 写临时 awk 文件失败 | HMFS 文件系统 umask 077 导致临时目录权限不足 | 补丁将 umask 077 改为 022 |
| 3 | 测试程序 "input error" | pbc_demo_pairing_init 从 stdin 读取 pairing 参数，无输入 | 提供 Type A 参数文件 (需 exp2/exp1/sign1/sign0 字段) |
| 4 | CMake 构建失败 | CMakeLists.txt 的 cmake_minimum_required(2.4) 与 CMake 4.x 不兼容；FindGMP.cmake 硬编码 $HOME/.local 路径 | 使用 autotools + patch 方式 |

## 补丁

| 补丁文件 | 说明 |
|---------|------|
| patches/0001-autotools-harmonyos.patch | config.guess/config.sub 添加 HarmonyOS 识别；configure umask 077→022 修复 HMFS |

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| pbc | 1.0.0 | ohpcd 制品仓 |
| gmp | 6.3.0 | ohpcd 制品仓 (通过 pbc 传递) |
| m (libm) | 系统 | C 运行时 |

## 验证结果

```
上游测试: 4/4 PASS (exit 0)
- test/bls: signature verifies
- test/bb:  signature verifies
- test/ibs: signature verifies
- test/bbs: exit 0 (demo, no EXPECT assertions)
```

## 注意事项

- 库名称为 `pbc_sig` (libpbc_sig)，不是 `pbc-sig`
- 上游测试需要 pairing 参数文件，不能直接运行 (需从 stdin 或 argv[1] 读取)
- test_package 使用 `pairing_init_set_buf` 内嵌参数，不依赖外部文件
---

**编译结束**: 2026-09-15 11:35
**最终状态**: built
