# notcurses 3.0.17 — OpenHarmony 编译记录

## 基本信息
- 软件: notcurses
- 版本: 3.0.17
- 构建系统: CMake
- 目标: ohos-aarch64
- 编译器: `/data/service/hnp/bin/clang++` (Clang 15)
- 安装前缀: `~/usr/local/`

## 编译指导

### CMake 配置
```bash
cmake .. \
  -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
  -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang \
  -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++ \
  -DUSE_MULTIMEDIA=none \
  -DCMAKE_BUILD_TYPE=Release
```

### 依赖库（链接顺序）
```
-lnotcurses++ -lnotcurses -lnotcurses-core -ldeflate -lncursesw -lunistring -lm
```

### 链接其他程序的示例
```bash
/data/service/hnp/bin/clang++ -std=c++20 -I ~/usr/local/include test.cpp \
  ~/usr/local/lib/libnotcurses++.a ~/usr/local/lib/libnotcurses.a \
  ~/usr/local/lib/libnotcurses-core.a ~/usr/local/lib/libdeflate.a \
  ~/usr/local/lib/libncursesw.a ~/usr/local/lib/libunistring.a -lm -o test
```

## 补丁清单

| # | 文件 | 说明 |
|---|------|------|
| 0001 | CMakeLists.txt | 禁用多媒体、设置 OHOS 兼容选项 |
| 0002 | src/demo/input.c | OHOS 兼容：跳过 ncplane_cursor_move_yx |
| 0003 | src/demo/reel.c | OHOS 兼容：平板上下文清理 |
| 0004 | src/lib/fbuf.h | 使用 `writev` 替代不支持的 `pwritev` |
| 0005 | src/lib/fd.c | OHOS：ncfdplane 线程取消兼容 |
| 0006 | src/lib/in.c | OHOS：使用 `poll()` 替代不支持的 `ppoll()`；`stop_inputlayer` 用 `pthread_detach` 替代被禁用的 `pthread_cancel` |
| 0007 | src/lib/internal.h | OHOS：禁用 `pthread_cancel`（内核不支持） |
| 0008 | src/lib/termdesc.c | **OHOS 核心补丁**：选择性跳过终端查询（保留 SMCUP+KKBDENTER，跳过 DA1/DA2 等需要响应的查询）；跳过 `handle_responses` 等待 |

### 补丁 0008 详解（终端查询问题修复）

**根因**：`notcurses_init()` 内部发送终端查询 escape 序列（DA1 `\x1b[0c`、DA2 `\x1b>c`、XTVERSION 等），然后 `inputlayer_get_responses()` 用 `pthread_cond_wait` **无限等待**终端响应。OHOS 终端不响应这些查询，导致永远阻塞。

**修改内容**（3处 `#ifdef __OHOS__`）：

1. **`send_initial_queries()`** — 选择性跳过：
   - ✅ 发送 `SMCUP`（进入备选屏幕，不需要响应）
   - ✅ 发送 `KKBDENTER`（键盘协议推入，不需要响应）
   - ❌ 跳过 `DSRCPR`（光标位置报告，需要响应）
   - ❌ 跳过 `IDQUERIES`（XTVERSION/TDA，需要响应）
   - ❌ 跳过 `send_initial_directives`（DA1/DA2/DA3，需要响应）

2. **`interrogate_terminfo()` 中 `handle_responses`** — 跳过等待终端响应，手动设置 `ti->kbdlevel = 0`

3. **`interrogate_terminfo()` 中清除 `initdata`** — 通过 `inputlayer_clear_initdata()` 释放 `ictx->initdata`，防止输入线程将键盘输入误路由为查询响应

4. **`stop_inputlayer()`** — OHOS 上用 `pthread_detach()` 替代 `cancel_and_join()`（因为补丁 0007 中禁用了 `pthread_cancel`）

### 补丁 0009 详解（Enter 键修复）

**根因**：`load_ncinput` 将 `\r` 映射为 `NCKEY_ENTER`（id=0x0d），但 `eff_text[0]` 仍为 `\r`。`ncreader_offer_input` 的 for 循环将 `\r` 写入 ncreader_write_egc。虽然 `utf8_egc_len` 对 `iswspace('\r')` 返回成功（colcount=1），但 `\r` 被写成1列宽的不可见字符，导致：
- 按 Enter 无换行效果
- 光标因不可见字符占位而偏移（"光标离输入字符很远"）

**修复**：在 `ncreader_offer_input` 中，`NCKEY_DOWN` 检查之后、`nckey_synthesized_p` 之后，添加 `#ifdef __OHOS__` 块处理 `NCKEY_ENTER`：直接调用 `ncplane_cursor_move_yx` 移到下一行行首。

### 补丁 0006 详解（poll 和线程停止）

1. **`block_on_input()`** — OHOS 不支持 `ppoll()`，用 `poll()` 替代
2. **`stop_inputlayer()`** — `pthread_cancel` 被 OHOS 禁用，改用 `pthread_detach` 避免阻塞

## 已知限制

1. **无终端查询功能**：无法自动检测终端类型、支持的特性（颜色数、六像素等），依赖 terminfo 数据库
2. **无光标位置报告**：`locate_cursor()` 不可用
3. **无 Kitty 键盘协议**：`kbdlevel` 固定为 0
4. **输入线程资源泄漏**：`stop_inputlayer` 使用 `pthread_detach`，不释放 `ictx` 内存（进程退出时自动回收）
5. **terminfo 必须可用**：需要 `TERMINFO=/path/to/terminfo` 或已安装的 terminfo 数据库

## 功能验证

```bash
# 设置 terminfo（如果不在默认路径）
export TERMINFO=/storage/Users/currentUser/usr/local/share/terminfo

# 编译测试程序
/data/service/hnp/bin/clang++ -std=c++20 -I ~/usr/local/include test.cpp \
  ~/usr/local/lib/libnotcurses++.a ~/usr/local/lib/libnotcurses.a \
  ~/usr/local/lib/libnotcurses-core.a ~/usr/local/lib/libdeflate.a \
  ~/usr/local/lib/libncursesw.a ~/usr/local/lib/libunistring.a -lm -o test

# 运行（3秒超时验证不卡住）
timeout 5 ./test

# 验证 nc_verify.log：nc=非空, render=0, OK
```

## 编译器预定义宏
- `__OHOS__` — 由 Clang 15 自动预定义，用于所有 OHOS 条件编译

## CodeCapsule 集成
- CodeCapsule 使用 `nc.get(false, &ni)` 非阻塞获取键盘输入
- 普通 Enter 在 ncreader 中换行，Ctrl+Enter 发送消息
- 编译命令: `cd /storage/Users/currentUser/renshang/agent/codecapsule && make clean && make tui`
