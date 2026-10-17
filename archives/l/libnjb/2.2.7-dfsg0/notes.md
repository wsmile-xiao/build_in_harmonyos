# libnjb 2.2.7 — HarmonyOS PC 适配说明

## 概况

libnjb 是 Creative Nomad Jukebox 系列播放器的用户态库：通过 libusb（0.1 API）
读取磁盘占用、上传位图/固件、查询电池，并提供内存中的 songid 标签结构。

- 上游：https://libnjb.sourceforge.net/ （源码来源为 Debian orig tarball）
- 构建：autotools，**tarball 自带 configure/Makefile.in**
- 依赖：libusb-compat/0.1.7（提供 `<usb.h>`；制品仓已发布）
- 许可证：BSD-3-Clause

## 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | libusb 0.1 API | 配方 `requires("libusb-compat/0.1.7")`（其提供 `<usb.h>` 与 `libusb` 兼容符号） |
| 2 | config.sub 不认 OHOS | 最小补丁补 `linux-ohos*` 组合（`archives/a/aalib`、`archives/l/libirman` 同法） |
| 3 | E007 | 显式 `--build/--host=aarch64-unknown-linux-ohos`，不让 config.guess 在 HMDFS 上探测 |
| 4 | E011 | `build()` 把 configure 里的 `umask 077` 就地改为 `022`（HMDFS 不支持 0700 临时目录） |
| 5 | 可选依赖 | `--disable-cursesplay --disable-samples`：避免 curses/zlib 的可选探测影响构建确定性 |
| 6 | 安装布局 | `make install`（DESTDIR 暂存）后删除 libtool `.la`；保留 `libnjb.{so,a}` 与头文件 |
| 7 | **随包 libtool 2.4 生成的脚本语法错** | 设备 `/bin/sh` 有 `print` 内建 → libtool 的 `_LT_CMD_ECHO` 选中 `ECHO='print -r --'`；`config.status` 用它转义 export-symbols 命令块时 `print` 不处理反斜杠 → 生成的 `libtool` 引号不闭合（`line ~350: syntax error near unexpected token '}'`）。`build()` 在 configure 前把该探测赋值改为 `printf` 分支 |
| 8 | **依赖的 `-I/-L` 未注入 configure** | `AutotoolsToolchain` 只发编译器/三元组标志；另加 `AutotoolsDeps(self).generate()` 才会带上 libusb-compat/libusb 的头与库路径 |
| 9 | **build==host 时 configure 运行探测** | 依赖标志让探测二进制定位 `libusb-1.0.so` 失败 → `cannot run C compiled programs`；传 `cross_compiling=yes` 跳过运行探测 |
| 10 | **`AC_FUNC_*` 在交叉下判"坏"** | 会引入上游未实现的 `rpl_malloc`/`rpl_memcmp`/`rpl_lstat`/`rpl_stat`，链接报 `undefined reference to rpl_malloc`；用 `ac_cv_func_malloc_0_nonnull=yes`、`ac_cv_func_memcmp_working=yes`、`ac_cv_func_lstat_dereferences_slashed_symlink=yes`、`ac_cv_func_stat_empty_string_bug=no` 覆盖 |
| 11 | **`libnjb.h` 需要 `<usb.h>`** | Conan 2 不把传递依赖 libusb-compat 的 include 交给 libnjb 的消费者（生成的 CMakeDeps data 为空）→ 在 `package_info` 把 compat 的 `include` 绝对路径并入 `cpp_info.includedirs` |

## 测试

### 上游

上游无测试套件（`examples/` 需要真实播放器）。硬件路径无法在沙箱验证。

### 消费者测试（test_package，CMake）

`test_package/test_libnjb.c` 共 10 条断言，覆盖**无需硬件**的纯内存 API：

- `NJB_Set_Debug()`/`NJB_Set_Unicode()` 可调用
- `NJB_Songid_New()` 分配成功；新对象迭代器为空
- `NJB_Songid_Frame_New_String()` 建帧、`Addframe` 后可被迭代器取到
- `NJB_Songid_Findframe()` 按标签命中与未命中
- `NJB_Songid_Reset_Getframe()` 重置迭代
- 追加第二帧后可再次命中
- `NJB_Songid_Destroy()` 释放

## 已知限制

- `NJB_Discover`/`NJB_Open`/固件上传等硬件路径未验证。
- 未修改上游源码与测试；唯一的补丁只改构建辅助脚本 `config.sub`。
