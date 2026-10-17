# libtermkey

## 简介

libtermkey 是一个抽象终端键盘输入库，提供统一的 API 来处理各种终端的键盘输入事件。它支持：
- 普通按键
- 功能键
- 鼠标事件
- 终端位置报告
- CSI/DCS 控制序列

## 版本

- 0.22 (2019-03-14)

## 构建系统

- makefile（使用 libtool）

## 依赖

- unibilium >= 2.0（终端数据库）
- libtool >= 2.4（构建工具）

## 编译选项

```bash
make PREFIX=/usr/local PKG_CONFIG_PATH=/usr/local/lib/pkgconfig
make test
make install PREFIX=/usr/local DESTDIR=/path/to/staging
```

## 产物

- libtermkey.so（动态库）
- libtermkey.a（静态库）
- termkey.h（头文件）
- termkey.pc（pkg-config 文件）

## API

主要函数：
- `termkey_new()` - 创建 TermKey 实例
- `termkey_getkey()` - 获取按键事件
- `termkey_waitkey()` - 等待按键事件
- `termkey_destroy()` - 销毁实例

## 注意事项

- 使用 unibilium 作为终端数据库（优于 ncurses）
- 需要设置 PKG_CONFIG_PATH 以找到 unibilium
- 无可执行二进制文件（纯库）

## 参考资料

- 官方网站：https://www.leonerd.org.uk/code/libtermkey/
- GitHub：https://github.com/neovim/libtermkey（已归档）
