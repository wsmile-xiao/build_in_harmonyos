# lm-sensors 3.6.0 — 编译进度

> 档案创建时间: 2026-04-27 00:00:00
> 最后更新: 2026-08-25 (conan 适配完成)

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | lm-sensors |
| 版本 | 3.6.0 |
| 状态 | ✅ success (conan 适配) |
| 构建系统 | makefile (plain Makefile) |
| 源码路径 | https://github.com/lm-sensors/lm-sensors/archive/refs/tags/V3-6-0.tar.gz |

## 二、编译阶段

### Phase 1: 环境准备
- [x] ohc-run.py init-build 完成 / 源码下载解压

### Phase 2: 编译（make + make install）
- [x] make CC=clang AR=llvm-ar BUILD_STATIC_LIB=1 user 完成
- [x] make install-lib install-prog-sensors 完成（跳过 etc/detect/pwm）

### Phase 2.5: 独立目录安装验证
- [x] conan-verify 通过 (G1-G4 + L2/L4/L5)

### Phase 3: 测试验证
- [x] conan create + test_package 通过
- [x] W3 本地 CI 模拟通过

### Phase 5: 归档收尾
- [x] conanfile.py / conandata.yml / test_package/ 生成
- [x] manifest.yaml 更新
- [x] commands.json 声明

## 三、源码修改清单
| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|---------|
| 无 | 源码无需修改 | — | — |

## 四、关键适配点

1. **构建系统**: lm-sensors 使用 plain Makefile（非 autotools/cmake），CC/AR 通过 make 命令行覆盖
2. **ETCDIR 问题**: etc/Module.mk 尝试写入 /etc（OHOS 只读），通过仅调用 install-lib 和 install-prog-sensors 目标跳过
3. **bison/flex**: conf-parse.c 和 conf-lex.c 需要从 .y 和 .l 文件生成，CI 环境通过 build_requirements 声明
4. **库命名**: 库文件为 libsensors.a/libsensors.so，conanfile.py cpp_info.libs = ["sensors"]
5. **头文件**: 安装到 include/sensors/ 目录，includedirs = ["include"]

## 五、结束记录
- **最终状态**: built (conan 适配完成，等待 PR 合入)
- **结束时间**: 2026-08-25
---

**编译结束**: 2026-08-27 01:21
**最终状态**: built
