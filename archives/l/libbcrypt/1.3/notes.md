# libbcrypt 1.3 — 适配笔记

> 档案创建时间: 2026-07-15
> 最后更新: 2026-07-17

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | libbcrypt |
| 版本 | 1.3 |
| 状态 | ✅ built (conan-verify passed) |
| 构建系统 | makefile |
| 源码路径 | https://www.openwall.com/crypt/crypt_blowfish-1.3.tar.gz |

## 二、编译阶段

### Phase 1: 环境准备
- [x] ohc-run.py init-build 完成 / 源码下载解压

### Phase 2: 编译
- [x] make 编译完成 (BLOWFISH_OBJS="crypt_blowfish.o" — excluded x86.o)
- [x] libbcrypt.a 创建完成 (llvm-ar rcs)
- [x] make install 完成 (手动安装到 test prefix)

### Phase 3: 测试验证
- [x] make check 结果: PASS (331.9 c/s real, 334.6 c/s virtual)
- [x] conan-verify G1-G4 + L2/L4/L5: ALL PASS
- [x] 本地 CI 模拟 (W3): PASS

## 三、关键适配决策

### x86.S 排除
- 原因: x86.S 是 x86 专用汇编，在 aarch64 上 BF_ASM=0
- 方案: 从 BLOWFISH_OBJS 中移除 x86.o，使用 crypt_blowfish.c 中的 C 实现
- 验证: crypt_test 通过，crypt_rn() 和 crypt_gensalt_rn() 功能正常

### 静态库创建
- 原因: 上游 Makefile 没有库目标，只有目标文件
- 方案: 使用 llvm-ar rcs libbcrypt.a 创建静态库

## 四、源码修改清单
| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|---------|
| 无 | 无需修改源码 | Makefile 命令行覆盖 | N/A |

## 五、二次校准记录 (2026-07-17)

### 检视意见响应

| # | 意见 | 处理 |
|---|------|------|
| 1 | build_type 未生效，CFLAGS 硬编码 -O2 | 添加条件 CFLAGS：Debug → -O0 -g，Release → -O2 |
| 2 | shared 选项未实现，shared=True 仍得静态库 | 移除 shared 选项和 package_type="library"（该库仅支持静态链接） |

### 变更文件
- conanfile.py: 移除 options/default_options/package_type，添加 build_type 条件 CFLAGS

## 六、结束记录
- **最终状态**: built (conan-verify passed, ready for PR)
- **结束时间**: 2026-07-17
