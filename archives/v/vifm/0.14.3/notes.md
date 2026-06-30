# vifm 0.14.3 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-25
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 应用 autotools 补丁：
   - 使用 `patch-autotools-ohos.pl` 修复 config.guess 和 config.sub
   - 手动添加 linux-ohos* 到 kernel-os 白名单

2. 解决 E011 问题：
   - 修改 configure 中的 `umask 077` 为 `umask 022`

3. 创建 ncurses 头文件软链接：
   - `ln -s ncursesw/curses.h curses.h`
   - `ln -s ncursesw/ncurses.h ncurses.h`
   - `ln -s ncursesw/ncurses_dll.h ncurses_dll.h`

4. 创建 term.h stub 文件（临时方案）

5. 运行 configure：
   ```bash
   export SYSROOT="/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot"
   export CPPFLAGS="-I$SYSROOT/usr/include -I~/usr/local/include -I~/usr/local/include/ncursesw"
   export LDFLAGS="-L~/usr/local/lib"
   ./configure --prefix=~/usr/local
   ```

6. 编译：`make -j4`

7. 安装：`make install DESTDIR=$TEST_PREFIX`

8. 验证：`./vifm --version`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别系统 | E007/E072: HarmonyOS 未被识别 | 使用 patch-autotools-ohos.pl |
| 2 | config.status 权限错误 | E011: HMDFS umask 077 权限问题 | 修改 umask 077 → umask 022 |
| 3 | curses.h 头文件找不到 | ncurses 头文件在 ncursesw 子目录 | 创建软链接到顶层 |
| 4 | term.h 缺失 | ncurses 编译未生成 term.h | 创建 term.h stub |

## 源码修改

### 应用补丁
- build-aux/config.guess: HarmonyOS 系统识别
- build-aux/config.sub: ohos 三元组支持
- configure: umask 077 → umask 022

### 头文件修复（外部依赖）
- ~/usr/local/include: ncurses 头文件软链接
- ~/usr/local/include/term.h: stub 文件

## 依赖版本

- ncurses 6.4 (静态库版本)

## 验证结果

```bash
$ ~/usr/local/bin/vifm --version
Version: 0.14.3
Git info: built out of repository
Compiled at: May 25 2026 18:28:23

Support of extended keys is on
Parsing of .desktop files is enabled
Without GLib2 library
Without magic library
Without X11 library
Without dynamic loading of X11 library
With file program
With -n option for cp and mv
With remote command execution
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| vifm | 2.0M | 主程序 |
| vifm-pause | 小 | 辅助工具 |
| vifm-convert-dircolors | 小 | 转换工具 |

## 注意事项

- E011 修复需要在运行 configure 前应用
- ncurses 头文件软链接需要手动创建
- term.h stub 是临时方案，需要从完整的 ncurses 编译中获取
- GLib2, libmagic, X11 支持可选，不影响基本功能

---

**编译结束**: 2026-05-25 18:28
**最终状态**: published
---

**编译结束**: 2026-05-25 18:31
**最终状态**: built
