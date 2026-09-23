# zlib 1.3.1.2 — 适配笔记

> 档案创建时间: 2026-04-09
> 最后更新: 2026-07-07
> 状态: built (conan-verify 待重新验证)

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | zlib |
| 版本 | 1.3.1 |
| 构建系统 | Makefile (configure) |
| 源码 | https://zlib.net/fossils/zlib-1.3.1.tar.gz |

## 二、适配修正记录 (2026-07-07)

### 修正 1: 移除 R6 违规补丁
- **问题**: `0001-Makefile.patch` 补丁修改的是 configure 生成的 Makefile（生成文件），且包含硬编码机器路径 `/storage/Users/currentUser/usr/local`
- **问题**: `0002-zconf.h.patch` 补丁修改的是 configure 生成的 zconf.h（生成文件）
- **修复**: 删除两个补丁文件，从 conandata.yml 移除 patches 段
- **原因**: configure 在 build() 中运行，会从 Makefile.in 和 zconf.h.in 重新生成这两个文件，补丁被覆盖，属于无效操作

### 修正 2: R33 编译器获取
- **问题**: conanfile.py 未从 Conan conf 获取编译器路径，依赖 configure 自动检测
- **修复**: 添加 `cc = self.conf.get("tools.build:compiler_executables:c", "clang", check_type=str)`，通过 `env={"CC": cc}` 传递给 configure
- **原因**: CI/release worker 上 shell 环境变量可能未设置，裸用会导致编译静默失败

### 修正 3: CONFIG_SHELL 默认值
- **问题**: 默认值为 `"sh"`，OHOS 上 `/bin/sh` 可能不存在或是 mksh
- **修复**: 改为 `/data/service/hnp/bin/bash`（与 profile [buildenv] 一致）

### 修正 4: test_package 改用 CMake
- **问题**: test_package 使用 `os.environ.get("CC", "clang")` 获取编译器（R33 违规），且 CMakeLists.txt 已存在但未使用
- **修复**: 改用 CMake 方式（CMakeDeps + CMakeToolchain），编译器设置由 CMakeToolchain 自动处理

### 修正 5: manifest 状态修正
- **问题**: 软件级 manifest 标记 `published`，版本级标记 `built`，不一致
- **修复**: 统一为 `built`（未 upload 到制品仓）

## 三、源码修改清单
| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|---------|
| (无) | configure 原生支持 OHOS | 无需修改 | 无补丁 |

## 四、编译命令
```bash
# 探索性编译
source .build-context-zlib-1.3.1
cd $BUILD_SRC_DIR
sh ./configure --static --prefix=/
make -j1
make check
make install DESTDIR=$TEST_PREFIX

# Conan 验证
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify zlib 1.3.1
```

## 五、结束记录
- **最终状态**: built (待 conan-verify 重新验证)
- **结束时间**: 2026-07-07
