# 编译笔记 — gnu-time 1.9

## 基本信息
- **软件**: GNU Time 1.9
- **版本**: 1.9
- **构建系统**: autotools
- **编译器**: clang 15.0.4
- **日期**: 2026-06-01

## 编译过程

### 1. init-build
- URL: https://ftp.gnu.org/gnu/time/time-1.9.tar.gz
- 自动下载并解压成功

### 2. configure
- 问题1: lld链接器因libxml2缺失不可用 → 使用 `-fuse-ld=bfd -B/data/service/hnp/bin/`
- 问题2: configure测试程序需要ELF签名才能执行 → 创建clang-wrapper自动签名
- 问题3: config.guess无法识别HarmonyOS → 添加 `aarch64:HarmonyOS:*:*` 映射到 `linux-gnu`
- 问题4: config.sub不认识HarmonyOS → 添加 `harmonyos*` 到OS检测列表

### 3. make
- 编译成功，7个警告（旧式C函数定义，非阻塞）
- 使用clang-wrapper作为CC，自动处理ELF签名

### 4. make install DESTDIR
- R20 DESTDIR模式: `--prefix=$DEFAULT_PREFIX` + `DESTDIR=$TEST_PREFIX`
- 安装产物: bin/time, share/info/time.info

### 5. 本地验证
- `~/usr/local/bin/time --version` → "time (GNU Time) 1.9"
- `time ls` 功能正常

### 6. 补丁
- 0001-build-aux-config.guess.patch: 添加HarmonyOS识别
- 0002-build-aux-config.sub.patch: 添加HarmonyOS OS映射

## 知识沉淀
- config.guess/config.sub需要添加HarmonyOS映射（E007模式）
- lld链接器在HarmonyOS上因libxml2缺失不可用，需要bfd linker
- configure期间编译的测试程序需要ELF签名才能执行
---

**编译结束**: 2026-06-01 20:21
**最终状态**: built
