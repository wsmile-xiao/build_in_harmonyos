# 适配笔记 — convlit 1.8 (ConvertLIT，.LIT → OEBPS/HTML)

## 库信息
- **软件**: convlit (clit)
- **版本**: 1.8
- **上游**: https://www.kyzer.me.uk/pack/convlit/ (ConvertLIT, Dan A. Jackson)
- **源码镜像**: Debian orig tarball（与上游 open_c-lit-1.8.tar.gz 字节一致，SHA256 相同）
- **许可证**: GPL-2.0-or-later（主体）；lib/newlzx 部分 LGPL-2.1+；des/sha 公有领域
- **构建系统**: Makefile（lib/ 静态库 openclit.a + clit18/clit 工具）
- **依赖**: libtommath

## 上游核验
- 原始 upstream https://www.kyzer.me.uk/pack/convlit/ 仍在线，页面提供 open_c-lit-1.8.tar.gz。
- 本机到 kyzer.me.uk 的 HTTPS 传输被重置；改为从 Debian 官方归档下载
  `convlit_1.8.orig.tar.gz`（unpatched orig），SHA256 = 上游 tarball 相同。
- salsa VCS: https://salsa.debian.org/debian/convlit.git（打包用，非运行时依赖）。

## 版本身份
- 源码顶层 README 明示 "This is the source code package of ConvertLIT 1.8"。
- clit 运行时打印 `+---[ ConvertLIT (Version 1.8) ]...`。

## OHOS 适配要点
1. **换行符**：2004 年 Windows 源码包为 CRLF。source() 先将 .c/.h/Makefile 统一为 LF，否则
   GNU make / patch 无法可靠处理。
2. **Makefile 硬编码**：`clit18/Makefile` 原写 `gcc ... ../libtommath-0.30/libtommath.a`，
   `lib/Makefile` 用 `ar`。改为 `$(CC)`/`$(AR)`，链接 `-ltommath`，include/lib 由 conan
   环境 CFLAGS/LDFLAGS 注入（libtommath/1.3.0 依赖包）。
3. **源码修正**：
   - `clit.c` 的 `dir_program[MAX_PATH]` / `dir_lit_file[MAX_PATH]` 改为 strdup（避免固定缓冲
     与 PATH_MAX 依赖），并释放内存。
   - 补充缺失头文件 string.h / sys/stat.h / ctype.h，消除隐式函数声明。
4. **构建顺序**：先 `make -C lib`（openclit.a），后 `make -C clit18`（clit 可执行文件）。
5. **无上游测试套件**：以 clit 无参数运行输出 "ConvertLIT (Version 1.8)" 标题与使用说明作为
   运行冒烟（同 multitail --help 先例，输出非空即 PASS，忽略其返回码 255）。

## 真机验证（Harmony PC aarch64 OHOS 6.0, clang 15）
- `conan create . --build=missing` → **PASS**（lib/ openclit.a + clit18/clit 均编译成功）
- test_package：`test_convlit` 以 popen 调用 `clit`，输出 "ConvertLIT (Version 1.8)" 标题与使用说明 → **PASS**（`convlit run: OK (output 100 bytes)`）
- 备注：clit 无参数运行打印标题后返回 -1（shell 层 255），与 multitail --help 处理方式一致，
  测试只校验输出非空（含版本标识），不依赖退出码。

## 已知限制
- 不处理 DRM5 私钥场景（需用户提供 keys.txt），仅验证二进制可执行与版本输出。
