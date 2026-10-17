# zeroc 3.7.10 适配笔记

## 编译环境
- 构建系统: makefile（Ice 自研 Makefile 系统，无 configure 脚本）
- 编译日期: 2026-09-20
- 编译器: clang/clang++（OHOS SDK clang 15，aarch64-linux-ohos）
- 状态: published
- conan: 2.29.1（OHOS 适配版），profile `ci/conan/profiles/ohos-aarch64`

## 编译步骤

1. 下载 ice v3.7.10 tarball（sha256 见 manifest）；下载 ZeroC mcpp fork v2.7.2.20（第二源，`conandata.yml:mcpp_source`）
2. 构建 vendored mcpp：`make CC=<cc> CFLAGS=-O2` → `lib/libmcpp.a` + `mcpp_lib.h`/`mcpp_out.h`/`config.h` 安入合并前缀 `<prefix>/{include,lib}`
3. 将全部 conan 依赖（直接+传递，含 ncurses）的 include/lib 合并入 `<prefix>`（真实文件拷贝，无符号链接）
4. 构建 Ice C++：
```bash
cd cpp && make os=Linux CC=<cc> CXX=<cxx> lib-suffix= \
  MCPP_HOME=<prefix> BZ2_HOME=<prefix> EXPAT_HOME=<prefix> LMDB_HOME=<prefix> \
  CONFIGS=shared \
  CPPFLAGS="-I<prefix>/include -Wno-deprecated-declarations -Wno-deprecated-copy-with-user-provided-dtor" \
  LDFLAGS="-L<prefix>/lib" \
  icegridadmin_system_libs="-ledit -lncursesw" \
  icestormadmin_system_libs="-ledit -lncursesw" \
  -j8 srcs
```
   ⚠️ 两个 `*_system_libs` 覆盖缺一不可：否则 icegridadmin/icestormadmin 链接缺 tgetent 等符号（readline 替代物 libedit/ncursesw 不在 Ice 默认 system_libs 列表）
5. `make ... install prefix=<包目录>`（同一变量集，保证库名推导一致）
6. 包内保真：无符号链接（HMDFS）；签名探测式处理（见问题 #7）
7. test_package：`clang++ -std=c++17 -stdlib=libc++ -lIce` 编译最小客户端并实际运行，输出 `Ice version: 3.7.10`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `<sys/poll.h>` 编译失败 | musl/OHOS 无该 glibc 转发头 | Network.h/Selector.h 无条件改 `<poll.h>`（补丁 0003/0004，无平台宏） |
| 2 | mcpp 编译报循环 include | 制品仓原版 mcpp/2.7.2 的已知缺陷 | vendor ZeroC 官方 fork v2.7.2.20（第二源，仿 aamath 双源格式） |
| 3 | 运行时 so 加载 Permission denied | HMDFS 不支持符号链接加载库/硬链接 | Make.project.rules 中 mksoname/mkshlibname 及 install 路径 4 处 `ln -s` → `cp`（补丁 0001）；包内 0 符号链接 |
| 4 | Glacier2/application 测试 PermissionDenied | musl 无 `__GLIBC__` 落入 DES-only 兜底，sha512-crypt 哈希(106字符)≠13字符被拒；且 OHOS SDK 无 `<crypt.h>` | 补丁 0002：include 守卫扩 `__linux__`，musl 分支手写 `extern "C" char* crypt(const char*, const char*);` + `IceUtil::Mutex` 保护（musl crypt 非重入）；glibc crypt_r 路径不变 |
| 5 | IceStorm/repgrid、IceGrid 全套 "unknown user id 20020100" | OHOS 应用沙箱 uid 无 /etc/passwd 记录，`getpwuid_r` pw==0 即抛错 | 补丁 0005：`pw==0` 且 uid 为进程自身 uid/euid 时跳过 passwd 库解析（服务器与 node 同 uid 无需降权）；groups/getgrouplist 块包 `if(pw != 0)` |
| 6 | 测试框架报 unknown platform | `scripts/Util.py` 平台识别不含 ohos | 补丁 0006：`sys.platform == "ohos"` 归入 Linux 平台分支 |
| 7 | 包内库被 loader 拒载（Error loading shared library，errno 为空） | 配方签名步骤 `objcopy --remove-section .codesign` + 本机 selfSign 失败（"not trust command"）→ 库失去签名段；musl dlopen 对无 .codesign 的 so 静默拒载 | 签名改探测式：先在临时副本上 strip+selfSign，全部成功才动真身；失败则保留 SDK 链接器自带的合法 .codesign |
| 8 | conan 报 "package type is 'library', but no 'shared' option" | package_type=library 须声明 shared 选项 | conanfile 增加 options/shared |
| 9 | conanbuild 环境下 make 调 `cc`/`g++` 失败 | Ice Makefile 用 make 内建 CC/CXX；conan 的 compiler_executables 不进 buildenv | 命令行显式 `CC=<cc> CXX=<cxx>`（从 conf 读取） |

## 源码修改

6 个补丁（refresh-patch --auto 生成，逐文件 diff）：
- `0001-config-Make.project.rules.patch`：SONAME/链接名及 install 路径 4 处 `ln -s` → `cp`（HMDFS 真实文件要求）
- `0002-...CryptPermissionsVerifierI.cpp.patch`：musl crypt 支持（`__linux__` 守卫 + 手写声明 + 互斥锁）
- `0003/0004-...h.patch`：`<sys/poll.h>` → `<poll.h>`
- `0005-...Activator.cpp.patch`：自身 uid 免查 passwd 库
- `0006-scripts-Util.py.patch`：测试框架识别 ohos 平台

## 依赖版本

- bzip2/1.0.8、expat/2.8.2、openssl/3.5.6（静态嵌入 libIceSSL）、lmdb/0.9.35、libedit/20240817（+传递依赖 ncurses/6.4，供 icegridadmin/icestormadmin readline 交互）
- mcpp 为 vendored 第二源（链接进 slice2cpp），不作为 conan 依赖

## 验证结果

### conan 配方闭环（W3 预演）
```bash
conan create archives/z/zeroc/3.7.10 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# EXIT=0：15 共享库 + 25 个 bin 工具 + include 全量安装；包内 0 符号链接；
# test_package 编译并实际运行输出 "Ice version: 3.7.10"
```

### 上游 C++ 测试套件（R51 全矩阵，93 个权威套件）

在源码工作树上执行上游 `cpp/allTests.py`（测试框架子进程继承 MAKEFLAGS/LD_LIBRARY_PATH），共 93 个权威测试套件：

| 结果 | 数量 | 明细 |
|------|------|------|
| ✅ 通过 | 88 | 含 Glacier2/application、IceStorm/repgrid、IceGrid 12 套（均由补丁 0002/0005 恢复） |
| ⚠️ 平台/数据限制 | 4 | 见下表 |
| ⏭️ 上游跳过 | 1 | Ice/echo（上游 LocalDriver.py:425 对该套件硬编码 continue，非 OHOS 特有） |

4 项限制（均为测试环境因素，非库功能缺陷）：
- **Slice/headers**：测试用 `os.symlink` 创建头文件别名 → HMDFS 上 EACCES
- **Ice/logger**：测试断言 chmod 权限位 → HMDFS 忽略 chmod
- **IceSSL/configuration、Glacier2/ssl**：测试证书 2024-10-21 过期，设备时钟为 2026-09

非缺陷澄清（不在权威清单中）：Ice/impl、Slice/parser 无 test.py；IceUtil/ctrlCHandler 仅手动；Ice/threadPoolPriority、IceUtil/priority 上游要求 root。

### 运行时二进制体检
- libIce.so.37 NEEDED 仅 libc++_shared.so + libc.so（openssl/bzip2 静态嵌入）
- 包内全部 .so.37/.so 为真实文件（HMDFS 合规）；SDK 链接器自带 .codesign 签名段保留

## 三、对话记录（断点续传核心）

### 对话 #1 — 2026-09-20
**操作**: 源码构建、R51 测试矩阵 93 套闭环、6 补丁生成、conanfile.py/test_package 编写、conan create 全链路验证
**结果**: 成功——配方构建 + test_package 输出 "Ice version: 3.7.10"；R51 88 通过 + 4 限制 + 1 上游跳过
**发现的问题**: ① conan2 tools.build:compiler_executables 不进 buildenv → 命令行显式 CC=/CXX=；② 包内库剥离 .codesign 后 loader 静默拒载 → 探测式签名策略；③ HMDFS ln -s 失败 → Make.project.rules 改 cp；④ musl 无 crypt.h、沙箱 uid 无 passwd 记录 → 补丁 0002/0005
**当前状态**: finish 流水线完成（W3 本地 CI 通过），待提交 PR
**遗留问题**: 无
---

**编译结束**: 2026-09-20 02:48
**最终状态**: built
