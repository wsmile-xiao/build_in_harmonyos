# minicom 2.10 — OpenHarmony 编译记录

## 基本信息
- **软件**: minicom
- **版本**: 2.10
- **构建系统**: autotools
- **目标平台**: OpenHarmony aarch64
- **编译器**: clang 15.0.4
- **编译日期**: 2026-05-16
- **状态**: ✅ 成功 (所有程序已完成)

## 编译产物

| 程序 | 大小 | 说明 |
|------|------|------|
| minicom | 530KB | 串口终端主程序 |
| ascii-xfr | 35KB | ASCII文件传输 |
| minicom_keyserv | 55KB | 键盘服务进程 |
| runscript | 76KB | 脚本执行器 |

## 编译指导

### 配置命令
```bash
./configure --prefix=/usr/local \
    --build=aarch64-linux-gnu \
    --enable-lock-dir=/var/lock
```

### 编译注意事项

1. **config.guess 适配**: OpenHarmony 系统类型未被识别，需显式指定 `--build=aarch64-linux-gnu`

2. **锁目录配置**: 默认锁目录检测失败，需通过 `--enable-lock-dir` 指定路径

3. **临时目录权限**: config.status 创建临时目录时存在权限问题，需修改脚本使用固定临时目录

4. **termcap 库**: 使用系统 libtinfo.so.6 替代 ncurses，需在 config.h 中启用 `HAVE_TERMCAP_H`

5. **termcap.h 模板变量**: `@NCURSES_OSPEED@` 需替换为 `short`

6. **全局变量定义**: 
   - minicom 主程序: 在 main.c 定义 LINES, COLS, program_name
   - keyserv: 定义 program_name, _tptr，使用 EXTERN 宏
   - runscript: 定义 program_name

7. **libport.h 路径**: 需修正 minicom.h 中的引用路径为 `../lib/libport.h`

## 补丁清单

| 补丁文件 | 类型 | 说明 |
|----------|------|------|
| 0001-patch-ai-review.txt.patch | 审核 | AI 审核记录 |
| 0002-main.c.patch | 源码修改 | main.c 源码调整 |
| 0003-po-Makefile.in.patch | 构建修复 | po 目录构建文件修复 |
| 0004-src-keyserv.c.patch | 全局变量 | keyserv 全局变量定义 |
| 0005-src-main.c.patch | 全局变量 | 添加 LINES, COLS, program_name |
| 0006-src-script.c.patch | 全局变量 | 添加 program_name |
| 0007-minicom.spec.patch | 打包 | spec 文件更新 |
| 0008-missing-aclocal.patch | 构建修复 | aclocal 缺失处理 |
| 0009-po-POTFILES.patch | 构建修复 | POTFILES 更新 |
| 0010-src-minicom.h.patch | 路径修复 | libport.h 引用路径修正 |

## 功能验证

### 版本检查
```bash
$ minicom --version
minicom version 2.10 (compiled May 16 2026)
```

### 帮助信息
```bash
$ minicom --help
Usage: minicom [OPTION]...
```

### 二进制检查
```bash
$ file minicom minicom_keyserv runscript ascii-xfr
minicom: ELF 64-bit LSB pie executable, ARM aarch64
minicom_keyserv: ELF 64-bit LSB pie executable, ARM aarch64  
runscript: ELF 64-bit LSB pie executable, ARM aarch64
ascii-xfr: ELF 64-bit LSB pie executable, ARM aarch64
```

## 依赖信息

- **运行时**: libtinfo.so.6 (已打包在发布包中)
- **编译时**: clang 15.0.4, make 4.4.1, autoconf 2.72, automake 1.16.5