# python 3.9.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-03-26
- 编译器: clang
- 状态: partial

## 编译步骤
```bash
./configure --prefix=$HOME/usr/local --disable-ipv6 \
  ac_cv_file__dev_ptmx=no ac_cv_file__dev_ptc=no \
  --with-openssl=$HOME/usr/local
make -j$(nproc)
make install
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 缺少 __OHOS__ 检测分支 | 补丁 0001-0003 添加平台识别 |
| 2 | HMDFS 不支持 symlink/hardlink | 文件系统限制 | Makefile 中 cp 替代 ln -f |
| 3 | threading.get_native_id() 不工作 | PY_HAVE_THREAD_NATIVE_ID 缺 __OHOS__ | 补丁 0006-0007 添加条件 |
| 4 | subprocess /bin/sh 路径不对 | 硬编码 /bin/sh | 改用 /system/bin/sh |
| 5 | ctypes closure 分配 W^X EINVAL | 鸿蒙禁止 mmap(RWX) | libffi 3.5.2 补丁修复 |

## 源码修改
- 78 个补丁（核心源码修复 + 测试适配）
- 新增文件: Lib/_harmonyos_compat.py（子进程兼容层）

## 依赖版本
- zlib, openssl, ncurses, readline, gdbm (可选)

## 验证结果
- regrtest V6 Final: 425 测试, 383 passed, 28 failed (90.1%)
- 204 个扩展模块编译成功
- pip install 正常工作
- ctypes 通过 libffi 3.5.2 修复后 0 ERROR 0 FAIL

## 交付物
- python3.9 解释器 + libpython3.9.so
- 204 个 .so 扩展模块

## 注意事项
- HMDFS chmod/umask 不遵循 POSIX 语义
- PTY 功能不可用（Hmmac MAC 策略限制）
- fork 可用但默认使用 spawn 模式
