# python 3.9.25 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-03-28
- 编译器: clang
- 状态: tested

## 编译步骤
```bash
./configure --prefix=$HOME/usr/local --disable-ipv6 --enable-shared \
  ac_cv_file__dev_ptmx=no ac_cv_file__dev_ptc=no
make -j$(nproc)
make install
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 基于 3.9.0 补丁集升级适配 | 源码差异 | 104 个补丁重新生成 |
| 2 | HMDFS symlink 问题 | 文件系统限制 | cp 替代 ln -sf |
| 3 | HAVE_LIBUUID 检测失败 | configure 宏检测问题 | 强制定义 |

## 源码修改
- 104 个补丁（三目录 diff 法生成）
- 核心源码 14 个、库文件 16 个、测试文件 49 个、测试数据 24 个、生成文件 1 个

## 依赖版本
- zlib, openssl, ncurses, readline, gdbm (可选)

## 验证结果
- regrtest: 425 测试, 380 passed, 12 failed (89.4%)
- 72 个 .so 扩展模块编译成功

## 交付物
- python3.9 解释器 + libpython3.9.so

## 注意事项
- 不能使用 --enable-optimizations（PGO 在 HarmonyOS 上不工作）
- 必须 make clean 后重新 make
- patch -p1 在 HMDFS 上有 fstat 问题，exit code 不可靠
