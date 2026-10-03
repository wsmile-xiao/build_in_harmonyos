# merecat 2.31-git20260330 测试报告

> **项目**: merecat，thttpd 系轻量 HTTP/HTTPS 服务器
> **测试日期**: 2026-09-29
> **测试环境**: HarmonyOS PC / HongMeng Kernel 1.12.0 aarch64，clang 15.0.4
> **测试类型**: 官方测试套件（make check）+ 补充消费者用例

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 14 | 100% |
| 通过 (PASS) | 13 | 92.9% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 1 | 7.1% |

**核心功能通过率**: ✅ **100%（13/13，跳过的 1 项不参与计算）**

`make check` 汇总（`tests/test-suite.log`）：

```
# TOTAL: 14
# PASS:  13
# SKIP:  1
# XFAIL: 0
# FAIL:  0
# ERROR: 0
```

---

## 二、测试结论

### 2.1 总体评价

✅ **可在鸿蒙 PC 上正常构建、打包并提供 HTTP 服务**

唯一的 SKIP 是 php.sh：测试环境未安装 php-cgi，脚本按约定 `exit 77`，Automake 记为 skip，
与适配本身无关。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| HMDFS 权限位缺失导致 403 | 静态文件/目录列表/CGI | 🟡 已修复（patches/0002，按文件系统能力决定是否回退） |
| `/tmp` 只读导致目录列表 500 | 目录列表 | 🟡 已修复（patches/0001） |
| config.guess 不识别 HarmonyOS | configure 阶段 | 🟡 已修复（POSIX 兼容方案） |

### 2.3 可用功能清单

```
✅ 静态文件服务：MIME、目录索引、Last-Modified
✅ 目录列表：自动索引目录
✅ CGI：/cgi-bin/*，含 setenv
✅ SSI：cgi-bin/ssi
✅ gzip 压缩：zlib mod_deflate
✅ .htpasswd Basic 认证
✅ .htaccess 访问控制
✅ location / redirect / proxy-pass 配置
✅ 配置文件 /etc/merecat.conf（libconfuse）
✅ HTTPS（OpenSSL）
✅ htpasswd 密码文件工具
⚠️ PHP CGI：需要 php-cgi，未安装
```

### 2.4 已知限制

1. `merecat -V` 的版本号来自 `configure.ac`，上游已升到 `3.00-rc1`，与 git 快照的日期
   版本 `2.31-git20260330` 不同，Debian 打包同样如此。
2. HMDFS 不暴露 POSIX "other" 权限位，无法沿用上游的 world-readable 判定；本适配对这类文件系统
   改走 `access()` 回退。回退只在**确实隐藏 other 位**的文件系统上生效：普通 Linux 等能表达
   other 位的平台保留上游判定原样（`0600` 文件、服务器进程可读仍返回 403），回归用例见 3.4。

---

## 三、测试详情

### 3.1 通过的测试（13 项）

| 测试项 | 功能 | 结果 |
|--------|------|------|
| start.sh | 基本启动与请求 | ✅ PASS |
| cgi.sh | CGI 执行 | ✅ PASS |
| setenv.sh | CGI 环境变量传递 | ✅ PASS |
| gzip.sh | gzip 压缩传输 | ✅ PASS |
| redirect.sh | 301 重定向 | ✅ PASS |
| location.sh | URL 映射 | ✅ PASS |
| proxy.sh | 反向代理（5 个用例） | ✅ PASS |
| dirlisting.sh | 目录列表 | ✅ PASS |
| htpasswd.sh | Basic 认证 | ✅ PASS |
| htaccess.sh | 访问控制 | ✅ PASS |
| ssi.sh | Server Side Includes | ✅ PASS |
| index-order.sh | index 优先级 | ✅ PASS |
| stop.sh | 优雅停止 | ✅ PASS |

### 3.2 失败的测试

无

### 3.3 跳过的测试

| 测试项 | 跳过原因 |
|--------|----------|
| php.sh | 环境缺少 php-cgi，脚本以 `exit 77` 退出，Automake 记为 skip |

### 3.4 消费者用例与回归用例（test_package/test.sh）

| 用例 | 断言 | 结果 |
|------|------|------|
| 打包产物可用性 | `merecat -V` 可用；环回 HTTP GET `/` 返回文档内容 | ✅ PASS |
| world-readable 契约（回归） | `0600` 文件：文件系统能表达 other 位时必须返回 403；隐藏 other 位时按 `access(2)` 回退返回 200 | ✅ PASS |

回归用例先探测文档根所在文件系统的能力（`chmod 0666` 后读回 other 位），再据此断言，
因此在 HMDFS 上验证回退路径、在普通 POSIX 文件系统上验证「不因服务器进程可读就放行」。

---

## 四、关键问题分析

### 问题1：静态文件访问返回 403

**现象**：
```
merecat: URL "/main.css" resolves to a non world-readable file
::1: - "HEAD /main.css HTTP/1.1" 403 0
```

**根因分析**：上游用 `hc->sb.st_mode & (S_IROTH | S_IXOTH)` 判断 world-readable/
world-executable，而 HMDFS 不暴露 POSIX other 位——目录即使是 `chmod 777` 也表现为 `750`，
`S_IROTH/S_IXOTH` 恒为 0，于是静态文件、目录列表、CGI 一律 403。

**解决方案**：patches/0002 新增 `httpd_other_bits_hidden()`，在 `$TMPDIR` 建一个 0777 文件并读回
other 位，结果按 `st_dev` 缓存（只在临时目录与目标文件同设备时采信）。`httpd_accessible()` /
`httpd_executable()` 的 6 处判定据此改为——能表达 other 位时保留上游判定，确实隐藏 other 位
（如 HMDFS）时才回退到 `access(path, R_OK/X_OK)`（POSIX 兼容，符合参考规范 R8）。

### 问题2：目录列表访问返回 500

**现象**：
```
merecat: tmpfile: Read-only file system
::1: - "GET /gallery/ HTTP/1.1" 500 0
```

**根因分析**：`lib/tempfile.c` 固定使用 `_PATH_TMP`（`/tmp`）配合 O_TMPFILE/mkstemp，
而鸿蒙 PC 的 `/tmp` 只读（E002）。

**解决方案**：patches/0001 让 `tempfile()` 优先使用 `$TMPDIR`，POSIX 兼容地在 O_TMPFILE
不可用时回退 mkstemp，并在 TMPDIR 为空时回退到默认路径。

### 问题3：config.guess 无法识别 HarmonyOS

**现象**：
```
config.guess: unable to guess system type
configure: error: working directory cannot be determined
```

**根因分析**：上游 config.guess 不认识 HarmonyOS（`uname -s` 返回 "HarmonyOS"），
探测失败后又落到依赖 mktemp 的临时目录逻辑上，而 HMDFS 下新建的 mktemp 目录不可写。

**解决方案**：扩展 `aux/config.guess` 增加 `*:HarmonyOS:*:*)` 分支，返回
`aarch64-unknown-linux-ohos`；同时扩展 config.sub 接受 `ohos*`/`ohos-linux`/`linux-ohos`，
并且 configure 不传 `--build/--host`，保持原生编译路径。

---

## 五、测试环境

```
merecat 2.31-git20260330（上游 commit 57a2ce7c0cca / 版本 3.00-rc1）
configure: --enable-builtin-icons --enable-htaccess --enable-htpasswd --without-symlinks
依赖: libconfuse/3.3, openssl/3.5.6.1, zlib/1.3.1；构建期 automake/1.18
工具链: clang 15.0.4, target aarch64-unknown-linux-ohos
```

---

*报告生成时间: 2026-09-29*
