# libmp3splt 0.9.3.1518 编译笔记

## 编译状态
✅ 编译成功

## 编译时间
2026-05-28

## 编译环境
- 目标平台: aarch64-unknown-linux-ohos
- 编译器: clang 15
- 构建系统: Autotools

## 依赖安装
所有依赖均从 cmd-pkgs 预编译包安装：
- libtool 2.4.7 ✅
- automake 1.17 ✅
- perl 5.42.2 ✅
- pcre 8.45 ✅
- flac 1.4.3 ✅
- libogg 1.3.5 ✅
- libvorbis 1.3.7 ✅
- libmad 0.15.1b ✅
- libid3tag 0.16.3 ✅

## 编译过程关键步骤

### 1. 源码准备
- 从 GitHub 下载源码: https://github.com/mp3splt/mp3splt
- 进入 libmp3splt 子目录进行编译

### 2. Autogen 阶段问题
- `aclocal` 需要 AUTOM4TE 环境变量
- 解决: `export AUTOM4TE=/data/service/hnp/bin/autom4te`

### 3. Configure 阶段问题
- config.status 无法创建临时目录（HMDFS 限制）
- 解决: 修改 config.status 脚本使用固定临时目录
```bash
sed -i 's|tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&|tmp=./conftmp; mkdir -p $tmp;|' config.status
```

### 4. 编译阶段问题
- libltdl 内嵌版本缺少源文件（预编译包问题）
- 解决: 使用系统 libltdl，复制头文件到 ~/usr/local/include/libltdl/
- Makefile 依赖规则导致重复 autogen
- 解决: 注释掉 ACLOCAL_M4 规则，设置时间戳

### 5. 安装阶段
- DESTDIR 模式安装成功

## 产物清单
```
lib/libmp3splt.so.0.0.9     # 主库（共享）
lib/libmp3splt.a            # 主库（静态）
lib/libmp3splt0/            # 插件目录
  ├── libsplt_mp3.so        # MP3 插件
  ├── libsplt_ogg.so        # OGG/Vorbis 插件
  ├── libsplt_flac.so       # FLAC 插件
include/libmp3splt/
  ├── mp3splt.h             # 公共头文件
  ├── version.h             # 版本信息
lib/pkgconfig/libmp3splt.pc # pkg-config 文件
```

## 功能验证
- libmp3splt 主库编译成功
- 三个插件（mp3, ogg, flac）编译成功
- 所有插件都链接到主库

## 待解决问题
1. 预编译包制作需要处理长路径问题（HMDFS tar 限制）
2. 完整的质量门禁测试（G0-G4）待执行

## 知识条目建议
- E073: HMDFS 文件系统临时目录创建问题
- E074: 预编译 automake/aclocal 的 AUTOM4TE 占位符问题
- E075: 预编译 libtool 包缺少 libltdl 源文件问题
---

**编译结束**: 2026-05-28 14:24
**最终状态**: built
