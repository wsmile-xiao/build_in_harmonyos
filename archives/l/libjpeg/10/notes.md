# libjpeg 10 编译笔记

## 编译开始
- 时间：2026-05-19
- 软件：libjpeg（IJG 版本）
- 版本：10（release 2026-01-25）

## 平台信息
- 系统：HarmonyOS HongMeng Kernel 1.12.0 aarch64
- 编译器：clang 15.0.4

## 构建系统
- 类型：autotools（configure + make）

## 依赖
- 无依赖（纯 C 实现）

## 编译参数
```bash
# configure 参数
./configure --prefix=$DEFAULT_PREFIX --disable-shared

# 关键参数说明：
# --disable-shared: 禁用动态库，使用静态链接（HMDFS 平台限制应对）
```

## 遇到的问题和解决方案

### 问题 1：config.guess 无法识别 HarmonyOS 系统（E007）
- 症状：`configure: error: cannot guess build type`
- 解决：使用 `patch-autotools-ohos.pl` 补丁修复 config.guess 和 config.sub
- 命令：`perl $SKILL_ROOT/scripts/patch-autotools-ohos.pl config.guess config.sub`

### 问题 2：HMDFS 平台 umask 限制导致 config.status 失败（E011）
- 症状：`./config.status[989]: can't create ./confXXX/subs1.awk: Permission denied`
- 解决：修改 configure 和 config.status 中的 `umask 077` 为 `umask 022`
- 命令：`sed -i 's/umask 077/umask 022/g' configure` 和 `sed -i 's/umask 077/umask 022/g' config.status`

### 问题 3：动态库加载失败（HMDFS 平台限制）
- 症状：`Error loading shared library libjpeg.so.10`
- 解决：重新编译为静态链接模式（--disable-shared）

## 功能测试
- ✅ cjpeg 编码测试通过
- ✅ djpeg 解码测试通过
- ✅ jpegtran 无损转换测试通过
- ✅ libjpeg 库 API 测试通过

## 产物
- cjpeg（166KB，静态链接）
- djpeg（170KB，静态链接）
- jpegtran（170KB，静态链接）
- rdjpgcom（22KB）
- wrjpgcom（27KB）
- libjpeg.a（312KB，静态库）
- 头文件：jconfig.h, jerror.h, jmorecfg.h, jpeglib.h
---

**编译结束**: 2026-05-19 21:35
**最终状态**: built
