# aseqjoy 0.0.2 适配笔记

## 编译环境
- 构建系统: autotools (pre-generated configure)
- 编译日期: 2026-08-24
- 编译器: clang/clang++
- 状态: built

## 编译步骤
1. 源码获取：从 GitHub 下载 master 分支 tarball
2. 补丁应用：0001-configure.patch（E011 umask 077 → 022）
3. configure：使用 AutotoolsToolchain + AutotoolsDeps 注入 ALSA 依赖
4. make -j1：HMDFS 不支持 mkfifo，使用 -j1
5. make install：安装到 DESTDIR

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status Permission denied | E011: HMDFS umask 077 创建不可写目录 | 补丁：configure 中 umask 077 → 022 |
| 2 | make jobserver mkfifo 失败 | HMDFS 不支持 mkfifo | 使用 make -j1 |
| 3 | lld 找不到 libxml2.so.16 | 只有 libxml2.so.2 | 在 $TMPDIR/lib 创建符号链接 |
| 4 | configure 找不到 ALSA | AutotoolsDeps 未生成 | 添加 AutotoolsDeps 到 generate() |
| 5 | configure AC_RUN_IFELSE 失败 | LD_LIBRARY_PATH 未设置 | 从依赖 package_folder 设置 LD_LIBRARY_PATH |

## 源码修改
- 0001-configure.patch：E011 HMDFS umask 077 → 022 权限修复

## 依赖版本
| 依赖 | 版本 | 用途 |
|------|------|------|
| alsa-lib | 1.2.16 | ALSA sequencer API |

## 验证结果
- conan create: 通过
- conan-verify: 8/8 门禁通过
- test_package: aseqjoy -h 输出版本信息

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（AutotoolsToolchain + AutotoolsDeps） |
| conandata.yml | 源码 URL + sha256 + 补丁声明 |
| patches/0001-configure.patch | E011 umask 修复 |
| test_package/ | Conan L1 测试 |

---

**编译结束**: 2026-08-24
**最终状态**: built
