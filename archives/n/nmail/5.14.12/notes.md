# nmail 5.14.12 适配笔记

## 决策记录

### 1. 依赖情报大修正（实证优先）
任务情报称依赖含 libetpan/1.9.4、notmuch/0.38.3。实测：
- **notmuch 零引用**：`grep -ri notmuch` 全源码无命中。CMakeLists.txt 无
  find_package(Notmuch)，src/ 无 include/链接。情报作废，非依赖。
- **libetpan 走 vendored**：CMakeLists.txt 默认 `HAS_CUSTOM_LIBETPAN=ON`，
  编译内嵌 `ext/libetpan` 源码（LIBETPAN_STATIC=ON → etpan-nmail 静态库）。
  ohpcd 实测 0 匹配 libetpan/1.9.4，无需该包。
- **真实依赖**（CMakeLists.txt + ext/libetpan/CMakeLists.txt 实证）：
  ncursesw（CURSES_NEED_WIDE）、openssl、xapian-core、sqlite3、cyrus-sasl、
  libmagic、libuuid、curl、expat、zlib。

### 2. 版本选择
| 依赖 | 选版 | 理由 |
|------|------|------|
| cyrus-sasl | 2.1.28.1 | 2.1.28 钉 openssl/3.5.6（--with-openssl）与 curl/8.15.0.1 钉 3.5.6.1 冲突；2.1.28.1 默认 --without-openssl 无该硬依赖 |
| openssl | 3.5.6.1 | curl/8.15.0.1 钉此版本，图内对齐 |
| xapian-core | 1.4.26 | 任务指令指定（ohpcd 有 1.4.22/1.4.26/2.0.0） |
| zlib | 1.3.1.1 | xapian-core 图内钉此版本，防冲突 |
| ncurses | 6.6 | ohpcd 最新，nmh 同款 |

### 3. CMake 变量注入（关键绕坑）
nmail CMakeLists.txt 用大写变量（XAPIAN_INCLUDE_DIR、CURSES_LIBRARIES、
SQLite3_LIBRARIES、CYRUS_SASL_LIBRARY、MAGIC_LIBRARY、LIBUUID_LIBRARIES、
OPENSSL_SSL_LIBRARY、OPENSSL_CRYPTO_LIBRARY、LIBETPAN_LIBRARY），
conan CMakeDeps 生成的是小写（xapian_INCLUDE_DIRS 等）→ 大小写不匹配。
**方案**：conanfile.py generate() 用 CMakeToolchain.variables 注入绝对路径
（vendored 静态 + XXX_LIBS 显式绝对路径手法，参考 ncview 日志）。

### 4. 测试入口
上游无测试（make.sh: `true # currently this project has no tests`）。
test_package 冒烟：nmail -v/--version（版本 banner + 退出 0）、-h/--help
（帮助 + 退出 0）、未知参数（退出 1）。全为纯 IO 路径，不启动 TUI。

## 编译过程
（编译日志见 learninglog/26.09.10nmail-5.14.12/，逐轮记录）

## 踩坑记录
- .opendesk-tmp 会被系统清理 → 源码工作副本迁移到
  /storage/Users/currentUser/Hawkninja/work/nmail-src/nmail-5.14.12.orig
- cyrus-sasl/2.1.28 直接版本冲突（openssl 3.5.6 vs 3.5.6.1）→ 换 2.1.28.1
- conan download 对未缓存包报 "system acceleration policy not enabled" 是
  正常提示（包已从 cache path 拿到配方），非失败