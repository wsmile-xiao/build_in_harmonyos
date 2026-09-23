# cdb 20251021 适配笔记

## 基本信息

- 上游: https://cdb.cr.yp.to/ （DJB cdb 官方维护版，对应 pkgsrc `databases/cdb`）
- 源码: https://cdb.cr.yp.to/cdb-20251021.tar.gz
- sha256: `8e531d6390bcd7c9a4cbd16fed36326eee78e8b0e5c0783a8158a6a79437e3dd`
  （SHA512 与 pkgsrc distinfo 一致：`dc7b4606...be723`，大小 111952 字节，官方源直连校验）
- 构建系统: djbware（Makefile + conf-cc/conf-ld/conf-home + 生成的 ./compile/./load/./makelib）
- 语言: 纯 C（零外部依赖，仅 libc）
- 状态: 真机验证通过（2026-09-08，10.62.134.118 OHOS aarch64，conan create + test_package 全绿）
- issue: 待补

## W0 依赖发布检查

无任何依赖（requirements 为空），无需检查制品仓。与 tinycdb 同款纯 C 库。

## W0b 历史经验核验

- 本仓库无 cdb 历史归档（首次适配）。
- 同类参照 tinycdb/0.81（已发布）的经验已逐项比对：
  - ld.bfd 替代 lld（`-fuse-ld=bfd`，避免 libxml2.so.16 缺失）→ 配方已内置（OHOS 分支）
  - llvm-ar/llvm-ranlib 交叉归档 → makelib 补丁 + AR/RANLIB 环境变量注入
  - musl 上 ulimit -f 不生效 → tinycdb 曾因此裁剪文件大小限制测试；cdb 的 rts
    注释同样声明依赖 XFSZ 信号（signal 25/31），真机跑 rts 时如遇该项失败属
    平台限制，记录即可
  - 新编译二进制 ELF 签名后方可直接执行：CI test_package 场景与其他已发布包
    一致（如 tinycdb 的 test() 也直接运行新二进制），如真机单跑时弹权限问题
    按知识库 ELF 签名条目处理

## 构建策略（关键决策）

1. **make prog 而非默认 it/setup/install**：DJB 的 `setup` 会运行 `./instcopy`
   （把文件拷进 conf-home）与 `./instcheck`，需要原生执行刚构建的二进制；
   `prog` 目标只构建全部二进制与静态库，交叉安全。产物安装由配方 package()
   用 self.copy 完成。
2. **conf-cc/conf-ld/conf-home 首行注入**：编译器路径取自 Conan conf
   `tools.build:compiler_executables`（R33），flags 固定 `-fPIC -O2`，Linux/OHOS
   加 `-D_XOPEN_SOURCE=500`（pkgsrc 同款，暴露 mmap/lseek 原型）；OHOS 链接
   加 `-fuse-ld=bfd`（可通过 `user.cdb:ld` conf 覆盖）。
3. **单一自包含 libcdb.a**：上游只安装命令，不装库（doc 明说 "the library
   per se is not installed"）。链接 cdb 程序实际需要 `cdb.a buffer.a unix.a
   byte.a` 四个静态库（Makefile 的 load 规则可见），配方将五个归档（含 cdb64.a）
   的成员合并为一个 `lib/libcdb.a`，cdb64 符号由宏重命名（cdb64_*）无冲突。
4. **补丁**（单一职责，unified diff）：
   - `0001-makelib-respect-AR-RANLIB-env.patch`：`ar cr`/`ranlib` 改为
     `${AR:-ar}`/`${RANLIB:-ranlib}`，使交叉 llvm-ar 可注入。CI 上 apply 无
     平台宏、无生成文件修改。
5. **conf-home 指向 package_folder**：生成的 `cdbmake-12`/`cdbmake-sv` 脚本
   内嵌 `<conf-home>/bin/cdbmake` 绝对路径。Conan 缓存包目录稳定，包内脚本
   引用自身 bin 可解析；若消费者迁移包目录则失效（上游行为如此，pkgsrc 同样
   内嵌 /usr/bin）。注意：这两个脚本是 `#!/bin/sh` + awk 脚本，OHOS 内核对
   /bin/sh shebang 有执行限制，且依赖 awk；使用时以 `sh cdbmake-12 ...` 方式
   调用。核心工具 cdbmake/cdbget 等均为 ELF，不受影响。

## 真机验证记录（2026-09-08，10.62.134.118:2222）

conan 2.29.1 + profile `ohos-aarch64-fixed`（clang 15.0.4 /data/service/hnp/bin，
cmake 同目录）。`conan create . --user=ohpcd --channel=stable -pr:h/-pr:b` 全绿：

- 构建：`make prog` 全部 14 个二进制 + 5 个静态库成功
- 打包：bin/ 14 个、include/ 4 个头、lib/libcdb.a（五归档合并，50KB）
- test_package：test_cdb（4 断言）+ test_cdb64（3 断言）+ CLI 回环
  （cdbmake 建库、cdbget 命中×2、未命中 exit 100）全部通过

真机踩坑与修复（已固化到配方/补丁）：

1. **hmdfs 拒绝 shebang 脚本 exec**：/storage/Users/currentUser（hmdfs 挂载，
   hmmac 标签）上 ELF 可执行，但 `#!` 脚本一律 EACCES（rc=126），即使 mode 755。
   djbware 的 ./compile/./load/./makelib 全是脚本 → 补丁 0002 把 Makefile 中
   68 处调用改为 `sh ./xxx`。`/data/local/tmp` 是 root-only，无处可躲。
2. **/tmp 只读**：clang 默认临时目录 /tmp 不可写（"unable to make temporary
   file: Read-only file system"）→ build() 注入 TMPDIR=build_folder；
   test_package 同理注入 TMPDIR。
3. **`-fuse-ld=bfd` 在 HNP clang 上非法**（invalid linker name）。该设备默认
   linker 与 lld 都能正常出 PIE ELF，无 libxml2 问题。配方改为默认不注入
   -fuse-ld，需要时用 `user.cdb:ld` conf 覆盖（CI worker 若遇 lld/libxml2
   可设）。tinycdb 时代的 bfd 默认值不适用于此设备。
4. **Conan 2.29 API**：`self.run(env=...)` 只接受 env 文件名（如 "conanbuild"），
   不接受 Environment 对象 → `with env.vars(self).apply():`；`self.copy` 已移除
   → `conan.tools.files.copy(self, pattern, src, dst)`；VirtualRunEnv 对
   静态库依赖（require.run=False）不扩展 PATH → test_package 用
   `self.dependencies["cdb"]` 的 package_folder 拼 CLI 绝对路径。

## 上游测试清点（R51 三步法申报）

- 上游测试套件：`rts.tests`（由 `sh rts` 运行，输出与 `rts.exp` 逐字节比对）
- 数量：55 个测试小节（`for SUFFIX in '' 64`，cdb 与 cdb64 各跑一遍）
- 覆盖：cdbmake/cdbmake-12/cdbmake-sv 创建、cdbdump/cdbtest/cdbstats 校验、
  cdbget 命中/未命中(exit 100)/重复键多值、klen 溢出拒绝、错误路径注入
- 构建期不运行（原因：交叉编译产物无法在构建机执行；且 rts 依赖已安装的
  cdbmake-12 脚本路径）
- 真机实测（2026-09-08）：**55 节中 47 节通过（85.5%）**。8 个失败节
  （cdb/cdb64 各 4）全部为错误注入型用例依赖的 OS 机制在 OHOS 不可用：
  hmdfs 禁止 symlink（unwritable tmp / unmovable cdb 两节）、musl ulimit
  -f/-v 不生效（full disk / nomem 两节）。功能行为本身正确（cdbmake 在
  无法注入失败的场景下正常成功）。运行方式：上游 rts.tests 字节级原样
  执行，#! 脚本工具（cdbmake-12/-sv）以 ELF shim 包装（shim exec /system/bin/sh
  真脚本），仅 PATH 层适配
- test_package 已覆盖等价的 API 与 CLI 回环断言（11 项）

## 本机已完成验证

- 源码 URL/sha256：官方源直连下载，SHA512 与 pkgsrc distinfo 完全一致，sha256 已算出
- 构建系统识别：djbware（无 configure 探测、无 config.guess）
- 补丁：对干净解包源码做过字节级应用验证（纯净 LF，无 CRLF 污染）
- 配方与 test_package 语法检查（python compile / yaml 解析）
- 真机 conan create + test_package 全绿（见上节）
- shadow CI（zsh build_and_test.sh）尚未跑，提 PR 前建议跑一次

## 真机 / shadow CI 下一步命令

单包 shadow CI（首选）：

```sh
CI_PACKAGES="archives/c/cdb/20251021" zsh ci/conan/build_and_test.sh
```

或独立运行器：

```sh
/path/to/run-ohos-shadow-ci.sh archives/c/cdb/20251021
```

手动 Conan 验证（OHOS worker，uid 一致）：

```sh
cd archives/c/cdb/20251021
conan create . --user=ohpcd --channel=stable \
  -pr:h=$HOME/.conan2/profiles/ohos-aarch64 \
  -pr:b=$HOME/.conan2/profiles/ohos-aarch64 \
  --build=missing
```

上游 rts 套件（真机，已实测 2026-09-08，47/55 通过，8 个失败为平台限制
详见"上游测试清点"节）。运行要点：需用**成功构建目录**（其 conf-home 指向
的包 bin 有全部工具）；#! 脚本工具用 ELF shim 包装后 rts.tests 原样执行：

```sh
cd <src>/cdb-20251021 && sh rts > rts.out && diff rts.exp rts.out
```

已知风险：
- CI L1d 门禁（fake test 检测）用行级正则匹配 test_package/conanfile.py 的
  `self.run(...echo|print|true)`——shell `printf` 因含 "print" 子串被误判为假
  测试；CLI 测试的 stdin 记录须用 Python 写文件再 `<` 重定向（已修复，CI #42231）
- lld/libxml2：默认不注入 -fuse-ld；若某 CI worker 的 lld 因缺 libxml2.so.16
  失败，在 profile 设 `user.cdb:ld`（名称或绝对路径）切换
- /bin/sh shebang 限制：cdbmake-12/cdbmake-sv/cdb64make-12/cdb64make-sv 四个
  脚本受影响，用 `sh <script>` 调用；test_package 不依赖它们
- musl ulimit -f：XFSZ 相关测试（如有）在 OHOS 不生效，属平台限制
