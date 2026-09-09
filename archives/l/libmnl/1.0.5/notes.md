# libmnl 1.0.5 — 编译笔记

> 档案创建时间: 2026-04-26 00:00:00
> 最后更新: 2026-05-28
> 状态: ✅ built（质量门禁 G0 通过）

---

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | libmnl |
| 版本 | 1.0.5 |
| 描述 | Minimalistic user-space library oriented to Netlink developers |
| 构建系统 | autotools |
| 语言 | C |
| 许可证 | LGPL-2.1-or-later |
| 依赖 | 无 |

---

## 二、编译阶段记录

### Phase 1: 环境准备
- ✅ ohc-run.py init-build 完成（tarball 由 curl 手动下载后放置，因 SSL 证书问题）
- ✅ 源码解压到 ~/tmp/builds/libmnl-1.0.5.work

### Phase 2: 编译
- ✅ configure 完成（参数: `--prefix=/storage/Users/currentUser/usr/local`）
  - 平台识别: `aarch64-unknown-linux-ohos`
  - 编译器: clang 15.0.4
  - 构建类型: shared library (libmnl.so), no static library
- ✅ make -j2 编译完成，无错误
- ✅ make install DESTDIR=$TEST_PREFIX 完成（staging 验证通过）

### Phase 3: 测试验证
- ✅ make check 执行完成（编译 20 个示例程序，无独立测试套件）
- ⚠️ 示例程序运行依赖内核 Netlink 模块，OpenHarmony 上可能无法获取数据

### Phase 4: 预编译包制作
- ✅ ohc-run.py package 完成
  - 产物: libmnl-1.0.5-ohos-aarch64.tar.gz (262KB)
  - 产物: libmnl-1.0.5-ohos-aarch64-debug.tar.gz (98KB)

### Phase 5: 归档收尾
- ✅ make install（不带 DESTDIR，安装到 ~/usr/local）
- ✅ 补丁生成（ohc-run.py refresh-patch --auto, 3 个补丁）
- ✅ G0 干净构建验证通过
- ⚠️ G1-G4 质量门禁部分通过（库无二进制，G4 manifest 有 1 个字段缺失）

---

## 三、对话记录

### 对话 #1 — 2026-05-28

**操作**: 执行完整编译流程（Mode B 手动编译）

**遇到的问题与修复**:

1. **config.guess 无法识别 HarmonyOS**（E007）
   - 原因: 2018 版 config.guess 不包含 HarmonyOS 检测分支
   - 修复: 使用 `patch-autotools-ohos.pl` 补丁，但因旧版脚本使用 `GUESS=` 语法而非 `echo+exit`，脚本补丁生成后输出仍为 "unable to guess"
   - 最终修复: 手动改为 `echo aarch64-unknown-linux-ohos; exit` 语法

2. **config.sub 缺少 ohos 三元组支持**
   - 原因: 2018 版 config.sub 不识别 linux-ohos
   - 修复: 手动添加 3 处修改:
     - §3.1: ohos-linux 三元组（在 android-linux 之后）
     - §3.2: linux-ohos* 在 maybe_os 列表（在 linux-uclibc 之后）
     - §3.3: -linux-ohos* 在 OS 类型列表（在 -linux-uclibc 之后）

3. **HMDFS mktemp 权限问题**（重要发现）
   - 原因: 在 HMDFS 文件系统上，`umask 077 && mkdir` 创建的目录权限为 `drwx--S---`（而非预期的 `drwx------`），**即使是目录所有者也无法在目录中创建文件**
   - 修复: 修改 configure 脚本中的临时目录创建代码:
     - 原始: `mktemp -d "./confXXXXXX"` → 修改为: `mktemp -d "${TMPDIR:-/tmp}/confXXXXXX"` + `chmod 755 "$tmp"`
     - 原始: `umask 077 && mkdir` → 修改为: `mkdir` + `chmod 755 "$tmp"`
   - 影响: 此问题影响所有使用类似 mktemp 模式的 autotools 项目

4. **SSL 证书问题**
   - 原因: Python urllib 无法验证 netfilter.org 的 SSL 证书
   - 修复: 使用 curl -kL 手动下载 tarball 后放置到 ~/tmp/builds/

**当前状态**: 编译完成，归档 published

**遗留问题**: 无

---

## 四、源码修改清单

| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|---------|
| build-aux/config.guess | 添加 HarmonyOS 检测（echo/exit 语法） | 手动编辑 | 0001-build-aux-config.guess.patch |
| build-aux/config.sub | 添加 ohos-linux 三元组 + OS/内核列表 | 手动编辑（3处） | 0002-build-aux-config.sub.patch |
| configure | HMDFS mktemp 权限修复：$TMPDIR + chmod 755 | 手动编辑 | 0003-configure.patch |

---

## 五、预编译包交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libmnl-1.0.5-ohos-aarch64.tar.gz | 262KB | 预编译包（含库/头文件/pkg-config） |
| libmnl-1.0.5-ohos-aarch64-debug.tar.gz | 98KB | 调试符号包 |

---

## 六、知识提取

### HMDFS mktemp 权限问题（新发现）
- 严重度: 🟡 medium（影响所有 autotools 项目）
- 根因: HMDFS 文件系统上 `umask 077 && mkdir` 创建 `drwx--S---` 目录，owner 无法写入
- 修复模式: 使用 $TMPDIR 替代当前目录 + chmod 755 修复权限
- 适用范围: 所有在 HMDFS 上运行的 autotools/configure 脚本
- 建议沉淀: 知识图谱 E 级条目

---

**编译结束**: 2026-05-28 15:26
**最终状态**: built
---

**编译结束**: 2026-06-01 15:08
**最终状态**: published
ished
---

## 七、v3 Conan 配方迁移（2026-09）

> 本节记录 v2 残档向 v3 Conan 配方框架补齐（参照 references/migration-guide.md，
> 先例 archives/l/libnfnetlink/1.0.2/）。v2 阶段的 manifest.yaml / notes.md /
> patches/ 原样保留复用。

### 新增文件

| 文件 | 说明 |
|------|------|
| conanfile.py | Autotools 配方：export_conandata_patches + basic_layout + AutotoolsToolchain；build() 末尾 `autotools.make(target="check")` 集成上游测试入口；cpp_info.libs=["mnl"] |
| conandata.yml | sources(url + sha256) + patches（Conan 2.x list 格式，L0f 强制） |
| test_package/conanfile.py | 消费者测试入口（test() + self.run，bash 包裹执行 ELF，同 zlib 先例） |
| test_package/CMakeLists.txt | find_package(libmnl REQUIRED)，链接 libmnl::libmnl |
| test_package/test.c | 冒烟测试：netlink 消息/属性 round-trip + mnl_socket_open/bind/get_portid/close（无需 CAP_NET_ADMIN） |
| test_package/MANIFEST.yml | 上游测试声明（L0e 强制），assertion_count=6 |

### 复用与决策

1. **patches/ 三补丁原样复用**（对净版 1.0.5 `patch -p1 --dry-run` 全部通过）：
   0001 config.guess HarmonyOS、0002 config.sub linux-ohos、0003 configure HMDFS
   mktemp=TMPDIR+chmod 755。与 libnfnetlink 先例不同，未叠加
   replace_in_file("umask 077"→"umask 022") 双保险——0003 已直接修订 configure，
   无需运行时改写。
2. **shared vs static：最终选 static-only**（`--enable-static --disable-shared`）。
   决策链：最初按 migration-guide「非系统同名库默认动态」与上游默认选 shared
   （R26 核实过：/system/lib{,64}、/lib{,64}、/usr/lib、/vendor/lib64 均无
   libmnl.so，非系统同名库，R26 不是决策驱动）；CI 实测暴露：HarmonyOS 平台
   （CMAKE_SYSTEM_NAME=HarmonyOS）下 CMake 对 imported shared 库不注入任何
   RPATH/RUNPATH（readelf 仅 NEEDED；对照 CMAKE_SYSTEM_NAME=Linux 注入
   RUNPATH 正常运行），叠加消费环境不注入依赖 libdir 的 LD_LIBRARY_PATH——
   消费者二进制没有任何运行期搜索路径，运行期
   `Error loading shared library libmnl.so.0`，任何 out-of-tree 消费者都得
   显式 LD_LIBRARY_PATH（musl 加载器本身的 DT_RPATH/DT_RUNPATH/
   LD_LIBRARY_PATH 三机制经真机探针证实全部有效，失败与加载器能力无关）。
   故改 static-only 使消费者开箱可运行，与同族 libnfnetlink/1.0.2 先例
   （CI PASS）一致。注意上游 configure.ac 有 AC_DISABLE_STATIC，必须显式
   `--enable-static` 覆盖，否则 `--disable-shared` 会落空（既非 shared 也非
   static）。机理探针与分歧记录沉淀于知识草稿
   `knowledge/drafts/DRAFT-ohos-cmake-harmonyos-imported-shared-no-runpath-*`。
3. **上游无独立 testsuite**：configure.ac 无 AC_CHECK_LIB/PKG_CHECK_MODULES
   （零外部依赖），无 TESTS 运行器；`make check` = check-recursive，实际效果是
   编译并链接 examples/ 下 20 个 check_PROGRAMS（genl 2 + kobject 1 +
   netfilter 6 + rtnl 11；计数实证：CI round-05 日志 check 阶段 20 条 CCLD 行，
   编译+链接即上游验证）；
   示例执行需内核 Netlink 数据，不属 make check 范围。真实执行验证由
   test_package 消费者冒烟测试承担（L1a/L1b/L1e 门禁）。

### 状态

v3 六件套补齐完成：conanfile.py / conandata.yml / test_package(4 文件) /
manifest.yaml（未改，v2 版本级格式保留，无 v3 规范强制修改项）/
notes.md（本节）/ patches（复用 3 补丁）。

### CI 回修记录（2026-09-06）

1. **test_package 消费者 sockaddr_storage 冲突（已修复）**：库自身与 examples
   构建零冲突（库内 `-I${top_srcdir}/include` 命中捆绑 linux 头，定义的是异名
   `__kernel_sockaddr_storage`）；但消费者只装 `libmnl/libmnl.h`，
   `<linux/netlink.h>` 落到 OHOS sysroot 的 bionic 风格拷贝，其无条件
   `sockaddr_storage` 与 musl `sys/socket.h` 在两种 include 顺序下都重定义。
   修复：test.c 顶部预定义 `_UAPI_LINUX_SOCKET_H` 并补
   `typedef unsigned short __kernel_sa_family_t;`（libnfnetlink 守卫同型的
   消费侧变体；include 顺序路线实证无效）。修复后 clang -Wall -Wextra 零警告。
   知识申报说明：该守卫模式已被知识图谱 E091/E119 覆盖，消费侧增量不另行
   申报，完整证据保留在 test.c 头部注释与本节。
2. **shared 交付的消费者运行期加载失败（已修复，改 static-only）**：shared 交付
   时 test_package 二进制链接成功但运行期报
   `Error loading shared library libmnl.so.0`。经审计探针裁定机理为：
   CMAKE_SYSTEM_NAME=HarmonyOS 下 CMake 对 imported shared 库不注入任何
   RPATH/RUNPATH（=Linux 对照注入正常），且 conanrun 环境不注入依赖 libdir
   的 LD_LIBRARY_PATH——消费者无任何运行期搜索路径；musl 加载器三机制
   （DT_RPATH/DT_RUNPATH/LD_LIBRARY_PATH）本设备全部有效，与加载器无关。
   见上文决策 2，改 static-only 交付。机理改判与三方分歧记录沉淀于知识草稿
   `knowledge/drafts/DRAFT-ohos-cmake-harmonyos-imported-shared-no-runpath-*`。
3. **CI 基础设施观察（非阻塞，未动 ci/**）**：pre-download 步骤的 python 环境
   报 `[Errno 2] No such file or directory: 'curl'`，随后 conan 自行直连
   netfilter.org 下载源码包成功（HTTP 200，SHA256 与固定值一致）。
