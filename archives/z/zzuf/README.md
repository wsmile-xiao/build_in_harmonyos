# zzuf

**透明应用输入模糊测试工具** — 通过 LD_PRELOAD 拦截程序的文件读取操作，在输入流中随机翻转位，实现可复现的确定性模糊测试。

- 上游仓库：https://github.com/samhocevar/zzuf
- 许可证：WTFPL
- 版本：0.15（autotools 构建）

## 产物

| 产物 | 说明 |
|------|------|
| `bin/zzuf` | 模糊测试驱动（`zzuf -r 0.01 ./prog file`） |
| `bin/zzat` | 可拦截函数/工具列表与统计 |
| `lib/zzuf/libzzuf.so` | LD_PRELOAD 拦截库（`zzuf -O preload` 时注入子进程） |

## OHOS 适配要点

- tarball 未含 `configure`，配方先执行 `./bootstrap`（autoreconf）生成。
- OHOS（musl 派生）libc 的 fortify `__fread_chk`/`__fgets_chk` 与 glibc 参数顺序
  不同且声明受 `__FORTIFY_COMPILATION` 门控：配方注入
  `ac_cv_func___fread_chk=no ac_cv_func___fgets_chk=no` 禁用 streambuf fortify 拦截
  （知识 E235 同类）。`fseeko64/fsetpos64/fpos64_t` 为宏别名，LP64 下禁用无损。
  `__read_chk/__recv_chk/__recvfrom_chk` 参数顺序与 glibc 一致且 libc.so 实际导出，
  保留启用 → 子进程（cat/dd）读文件被正确拦截（check-utils 522/553 通过）。
- HMDFS setgid 目录按组权限判定写入：autoconf 以 `umask 077` 创建的临时目录
  config.status 无法写入（Permission denied），配方统一以 `umask 022` 运行
  bootstrap/configure/make/install（R49 平台限制，非源码补丁）。
- OHOS FILE 结构不透明（`bits/alltypes.h: struct _IO_FILE { char __x; }`）：
  zzuf 的 glibc/FreeBSD/Solaris streambuf 探测在编译期即不可用，上游 check-utils
  中 ungetc/streambuf 类回归断言（31/553）与本机参考 md5 不一致，属真实平台
  限制；鸿蒙专项 `check-ohos`（确定性/有效性/子进程拦截/xor 比率 4 项）全部通过。

## 测试统计（双口径）

- source_declared_total = 12（11 注册 TESTS + check-zzuf-s-seed 未注册）
- configured_executable_total = 11（automake TESTS 注册）
- executed_passed_total = 10（check-utils 部分断言失败即脚本级 1 项失败）
- 全量通过率：10/12（83.3%）；check-utils 553 断言通过率 522/553（94.4%）
- 详情见 `0.15/reports/` 与 `0.15/manifest.yaml`