# cdrtools 3.02a09 适配笔记

## 编译环境
- 构建系统: makefile (Schily makefilesystem)
- 编译日期: 2026-05-28
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 下载源码: https://downloads.sourceforge.net/project/cdrtools/alpha/cdrtools-3.02a09.tar.bz2
2. 删除 configure 文件（cdrtools 不使用 configure，直接运行 make）
3. 创建 HarmonyOS 适配文件:
   - RULES/os-harmonyos.id
   - RULES/os-harmonyos.def
   - DEFAULTS/Defaults.harmonyos
4. 运行: `make -j1 GMAKE_NOWARN=true INS_BASE=$HOME/usr/local`
5. 安装: `make install INS_BASE=$HOME/usr.local DESTDIR=$HOME/test-install-cdrtools-3.02a09`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 脚本只打印信息不执行 | cdrtools 不使用 configure，使用 Schily makefilesystem | 删除 configure 文件，让构建系统识别为 makefile |
| 2 | 缺少 os-harmonyos.id 文件 | cdrtools 构建系统需要操作系统识别文件 | 创建 RULES/os-harmonyos.id |
| 3 | 缺少 os-harmonyos.def 文件 | 需要操作系统定义文件 | 创建 RULES/os-harmonyos.def |
| 4 | 缺少 Defaults.harmonyos 文件 | 需要默认配置文件 | 创建 DEFAULTS/Defaults.harmonyos |
| 5 | avoffset.h 文件不完整 | 自动生成程序在 HarmonyOS 上运行失败导致输出不完整 | 手动修复添加 #endif |
| 6 | install-sh 使用 /tmp | R10: HarmonyOS /tmp 只读 | 修改为 ${TMPDIR-/tmp} |

## 源码修改

### 补丁文件
- 0001-DEFAULTS-Defaults.harmonyos.patch: HarmonyOS 默认配置
- 0002-RULES-os-harmonyos.def.patch: 操作系统定义
- 0003-RULES-os-harmonyos.id.patch: 操作系统识别
- 0004-conf-install-sh.patch: 使用 TMPDIR 替代 /tmp (R10)
- 0005-incs-aarch64-linux-clang-avoffset.h.patch: 修复生成的头文件

## 依赖版本

无外部依赖。

## 验证结果

```bash
# 验证安装产物
ls ~/test-install-cdrtools-3.02a09/$HOME/usr/local/bin/
# 输出: btcflash cdda2mp3 cdda2ogg cdda2wav cdrecord devdump isodebug isodump isoinfo isovfy mkhybrid mkisofs readcd scgcheck scgskeleton
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| cdrtools-3.02a09-ohos-aarch64.tar.gz | ~2.1MB | 预编译包（包含所有工具和库） |

## 注意事项

1. cdrtools 使用特殊的 Schily makefilesystem，不使用标准的 autotools
2. 构建系统会自动检测操作系统和编译器（基于 uname）
3. HMDFS 不支持某些软链接操作，tar 解压可能有警告但不影响编译
4. 生成的 avoffset.h 可能不完整，需要手动修复
---