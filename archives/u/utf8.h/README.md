# utf8.h

`utf8.h` 是一个单头文件 UTF-8 字符串处理库（Unlicense，公有领域），提供按码点
计数的长度、码点解码/编码、拼接比较、合法性校验与复制等函数，C89 起可用并支持
C++ 各标准版本（含 constexpr 路径）。

```c
#include <utf8.h>
const utf8_int8_t *s = "h\xc3\xa9llo";   /* héllo：6 字节 / 5 码点 */
size_t n = utf8len(s);                   /* -> 5（码点数，非字节数） */
utf8_int32_t cp;
s = utf8codepoint(s, &cp);               /* -> 'h'，s 指向下一个码点 */
```

- 上游仓库：https://github.com/sheredom/utf8.h
- 版本：0.0-git20260825.7e403ccc3f（commit 7e403ccc，2026-08-25，上游无 release tag）
- 许可证：Unlicense（公有领域）
- 构建系统：header-only（上游无库构建；test/ 目录为自包含 CMake+CTest 测试工程）
- 类型：头文件库（无库产物）

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.0-git20260825.7e403ccc3f | built | 首次适配 HarmonyOS PC (aarch64) |
