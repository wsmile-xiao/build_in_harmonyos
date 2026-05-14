# mecab 0.996 — OpenHarmony 编译记录

## 基本信息
- **软件**: mecab
- **版本**: 0.996
- **构建系统**: autotools
- **目标平台**: ohos-aarch64
- **源码URL**: https://deb.debian.org/debian/pool/main/m/mecab/mecab_0.996.orig.tar.gz

## 软件简介
MeCab 是一款开源的日语文本分词引擎，基于条件概率场（CRF）模型，可生成高质量的日语形态分析结果。

## 编译指导

### 特殊注意事项
1. **构建模式**: 因 HMDFS heredoc 权限限制，需使用 VPATH 构建模式
2. **C++ 库**: 鸿蒙使用 libc++，需替换 Makefile 中的 `-lstdc++` 为 `-lc++`
3. **临时目录**: 需设置 TMPDIR 环境变量，并手动修改 config.status 中的 `ac_tmp`

### 编译命令
```bash
# 创建构建目录
mkdir -p ~/tmp/mecab-build-0.996
cd ~/tmp/mecab-build-0.996

# 设置环境变量
export DEFAULT_PREFIX=~/usr/local
export TMPDIR=~/tmp
export CC=clang
export CXX=clang++

# 应用补丁到源码目录
cd ~/builds/mecab-0.996.work
perl $SKILL_ROOT/scripts/patch-autotools-ohos.pl config.guess config.sub
sed -i 's|mktemp -d "\./confXXXXXX"|mktemp -d "${TMPDIR:-/tmp}/confXXXXXX"|g' configure

# VPATH 构建配置
cd ~/tmp/mecab-build-0.996
~/builds/mecab-0.996.work/configure --prefix=$DEFAULT_PREFIX

# 修复 libstdc++ 问题
sed -i 's/-lstdc++/-lc++/g' src/Makefile

# 编译安装
make -j$(nproc)
make install DESTDIR=$TEST_PREFIX
make install  # 本地安装
```

## 补丁清单
| 补丁文件 | 类型 | 描述 |
|----------|------|------|
| 0001-config.guess.patch | 平台适配 | 添加 HarmonyOS 系统识别 |
| 0002-config.sub.patch | 平台适配 | 添加 linux-ohos 三元组 |
| 0003-configure.patch | 平台适配 | 使用 TMPDIR 创建临时目录 |

## 已知限制
1. **VPATH 构建测试失败**: 测试脚本假设在源码目录内构建，VPATH 模式下路径不匹配
2. **需要字典**: 运行分词功能需要安装 mecab-ipadic 等字典包

## 功能验证
```bash
$ mecab --version
mecab of 0.996
```

## 相关知识
- E007: config.guess 无法识别 HarmonyOS
- E002: /tmp 只读问题（使用 TMPDIR）
- 鸿蒙 C++ 库：libc++ 替代 libstdc++

---
*编译日期: 2026-04-29*