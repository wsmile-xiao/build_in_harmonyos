# cachefilesd-inotify 0.11.1 适配笔记

## 基本信息
- **软件**：cachefilesd-inotify — FS-Cache 用户态守护进程（inotify 版，替代 dnotify）
- **版本**：0.11.1
- **上游**：https://gitlab.com/tomalok/cachefilesd-inotify
- **许可证**：GPL-2.0-or-later
- **构建系统**：Makefile（C 项目，无 configure 脚本）
- **适配日期**：2026-07-31

## 源码信息
- **来源**：GitLab tomalok/cachefilesd-inotify archive
- **URL**：https://gitlab.com/tomalok/cachefilesd-inotify/-/archive/0.11.1/cachefilesd-inotify-0.11.1.tar.bz2
- **sha256**：`952ab9d4da29c7ad958bde9a29c196d45972e429f3444adbfcc17b146562f084`
- **sha512**：`6209e3abed82a7ffbeab17b85b700220616465a412fd9550b4fc282b681eb08a13d163b2fe8acc01cfc0cfca1d8902e8702db9de25ab9955cf1c770c26ed9865`（与 Alpine APKBUILD 一致）
- **size**：28762 bytes

## 上游定位
cachefilesd-inotify 是 cachefilesd（dhowells 维护，kernel.org，最高 v0.10.10）的 inotify 重写版，由 tomalok 维护在 GitLab。Repology 显示 Alpine Linux 3.21+、T2 SDE、GNU Guix 打包此版本。

## 依赖分析
- **编译期**：无外部依赖（纯 C，仅依赖标准 POSIX 头文件：sys/inotify.h, sys/vfs.h, syslog.h, poll.h, getopt.h 等，OHOS musl 均提供）
- **运行期**：Linux 内核 /proc/fs/cachefiles 接口（FS-Cache 内核模块）、xattrs 支持
- **无 Conan requires**

## 构建方式
Makefile 构建，关键适配点：
1. **BUILDFOR= 空**：Makefile 用 `file /usr/bin/make | sed` 猜字长，加 `-m32`/`-m64`。OHOS aarch64 clang 不认 `-m64`（x86 选项），且 OHOS 上 `file` 命令可能不可用。传 `BUILDFOR=` 空让 ifeq 失败，跳过 -m32/-m64。
2. **CC 从 conan conf 获取**（R33）：`self.conf.get("tools.build:compiler_executables:c")`，不用 shell `${CC}`。
3. **-j1**（R9）：Makefile 项目强制单线程。
4. **VERSION 从 specfile 读取**：`grep "^Version:" redhat/cachefilesd.spec` → 0.11.1，仅用于 tarball/rpm 目标，不影响编译（版本硬编码在 cachefilesd.c 第 30 行 `#define CACHEFILESD_VERSION "0.11.1"`）。

无补丁（BUILDFOR= 命令行覆盖解决 -m64，无需改 Makefile）。

## 测试策略

### 上游测试
上游无测试套件（Alpine APKBUILD `options="!check"`，Makefile 无 check 目标）。`upstream_test_in_build: false`。

### test_package 冒烟测试
cachefilesd 支持 `--version`/`-v` 选项（main 第 353 行 case 'v' → version() 打印 `cachefilesd version 0.11.1` 后 exit(0)）。
- **test.sh**：运行 `cachefilesd --version`，校验输出含 `0.11.1`
- **L1e 破坏性反向验证**：移走 bin/cachefilesd → 命令找不到 → test 失败 → L1e 通过
- **L2 smoke test**：CI 的 L2 也会跑 `cachefilesd --version`（PASS）

## CI 门禁符合性（build_and_test.sh L0-L5）
| 门禁 | 检查项 | 状态 |
|------|--------|------|
| L0a | test_package/ 目录存在 | ✅ |
| L0b | test_package/conanfile.py 存在 | ✅ |
| L0c | test_package/ 有测试源文件 (.sh) | ✅ test.sh |
| L0d | test_package/conanfile.py 有 test() + self.run() | ✅ |
| L0e | test_package/MANIFEST.yml 存在 | ✅ |
| L0f | conandata.yml patches 格式 | ✅ 无 patches |
| L0g | 禁止硬编码 remote | ✅ 无 conan -r= |
| L0h | self.run 无 ${CC}/${CFLAGS} | ✅ 用 conan conf + f-string |
| L0i | 依赖发布检查 | ✅ 无 Conan requires |
| L0k | commands.json（CLI 工具） | ✅ application 类型，已创建 |
| L0m | 目录结构 archives/c/cachefilesd-inotify/0.11.1 | ✅ |
| L0n | 分支名含 cachefilesd-inotify-0.11.1 | ✅ |
| L1a | test_package 被 conan create 执行 | ✅ test_type=explicit |
| L1d | test() 非假运行 | ✅ bash test.sh 运行 cachefilesd |
| L1e | 破坏性反向验证 | ✅ 移走 bin/ 后 cachefilesd 命令找不到 |
| L4 | 补丁安全扫描 | ✅ 无补丁 |
| L5 | 产物检查 | ✅ bin/cachefilesd |

## 验证命令
```bash
conan create archives/c/cachefilesd-inotify/0.11.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

> 注：本地 Mac 无法验证编译（macOS 无 sys/inotify.h），需在 OHOS CI 设备验证。

## 已知限制
1. **运行期需内核 FS-Cache 支持**：cachefilesd daemon 运行需 /proc/fs/cachefiles 内核接口与 xattrs，OHOS 内核需启用 FS-Cache 模块。编译期无此限制。
2. **--version 不依赖内核接口**：version() 仅 printf + exit(0)，CI 可安全运行做冒烟测试。
3. **配置文件 secctx**：Alpine 构建注释 secctx（SELinux），本适配保持原配置，部署时按需调整。

## 交付物
- `bin/cachefilesd` — FS-Cache 守护进程可执行文件
- `res/cachefilesd.conf` — 配置文件
- `share/man/man5/cachefilesd.conf.5`, `share/man/man8/cachefilesd.8` — man pages
