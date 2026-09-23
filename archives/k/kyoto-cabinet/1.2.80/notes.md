# kyoto-cabinet 1.2.80 适配笔记

## 基本信息

- 上游：Kyoto Cabinet 1.2.80（fallabs 的 QDBM 后继）
- 官方站 `https://fallabs.com/kyotocabinet/` 当前 404，源码改用官方镜像
  `https://dbmx.net/kyotocabinet/pkg/kyotocabinet-1.2.80.tar.gz`（SHA256 不变）
- SHA256：`4c85d736668d82920bfdbdb92ac3d66b7db1108f09581a769dd9160a02def349`
- License：GPL-3.0-or-later（含 FOSS/LINK 例外条款，见 tarball 内 COPYING 与 FOSSEXCEPTION）
- 构建系统：autotools（configure.in + Makefile.in，后缀规则，无 VPATH）
- 数据库后端：StashDB（内存）、CacheDB（内存，带缓存）、GrassDB（内存+临时文件）、
  HashDB（文件哈希）、TreeDB（文件 B+树）、DirDB（目录）、ForestDB（文件多树）；
  ProtoDB（内存原型，仅原型接口）。配方和 test_package 使用 HashDB（文件数据库），
  未用任何内存数据库替代。

## 补丁

1. `0001-configure-umask-hmdfs.patch`：configure 在检测临时目录可写性时
   `mkdir "$mytmpdir"` + `umask 077`。HMDFS（鸿蒙 PC 用户态文件系统）上
   umask 077 的目录创建/探测组合失败，导致 configure 报 "cannot create
   temporary directory"。改为 umask 022。基于纯净 1.2.80 tarball 重制
   （旧骨架补丁包含大量二进制噪音，不可复用）。

## 构建要点

- 上游 Makefile 只有后缀规则（.cc.o），无 VPATH/`srcdir` 引用 → 必须源内构建。
  conanfile 里 `autotools.configure(build_folder=self.source_folder)`。
- `make -j1`：上游 check 目标共享 `casket*` 测试库文件且无目标间依赖声明，
  并行会竞争。
- zlib 压缩开启（上游默认，`--enable-zlib`），lzma/lzo 关闭（上游默认，仓库无
  已发布依赖）。
- configure 参数追加 `--enable-static --disable-shared`（默认 static）。
- CI_PACKAGES 定向构建：`CI_PACKAGES=kyoto-cabinet python3 scripts/gitcode_pr.py ...`

## 上游测试审计（L1）

`make check` 展开为 11 个子目标、512 条 RUNENV 测试命令：

| 子目标 | 命令数 |
|---|---|
| check-util | 38 |
| check-proto | 16 |
| check-stash | 9 |
| check-cache | 9 |
| check-grass | 9 |
| check-hash | 77 |
| check-tree | 77 |
| check-dir | 76 |
| check-forest | 70 |
| check-forest: extra | 6 |
| check-poly | 111 |
| check-langc | 14 |
| **合计** | **512** |

（另有 check-heavy 60 条与 check-segv 1 条不在 `make check` 内，不运行。）

17 个测试/管理可执行：kcutiltest/kcutilmgr/kcprototest/kcstashtest/kccachetest/
kcgrasstest/kchashtest/kchashmgr/kctreetest/kctreemgr/kcdirtest/kcdirmgr/
kcforesttest/kcforestmgr/kcpolytest/kcpolymgr/kclangctest。

## 平台行为验证（不掩盖兼容问题）

- 文件锁：kcfile.cc 使用 fcntl(F_SETLK/F_SETLKW) POSIX 记录锁（非 flock），
  真机验证通过。
- mmap：kchashdb.cc 使用 mmap(MAP_SHARED) 映射数据文件，真机验证通过。
- 原子替换：kchashdb 写入用 write + ftruncate 原子更新头部字段（非 rename），
  真机验证通过。
- 线程：kcthread.cc 用 pthread 全家桶（create/mutex/cond/TSD），真机验证通过。
- 原子操作：myconf.h 定义 _KC_GCCATOMIC（`__sync_*` 内建），真机验证通过。
- 持久化：test_package 显式 synchronize(true) 落盘 + 关闭后重开复验，
  真机验证通过。

## test_package（27 项断言）

create / write / read / overwrite / remove / iterate / close+reopen /
persistence / synchronize(fsync) / invalid path / corrupted header /
truncated file / cleanup removal。全部真机运行，DB 文件只放测试构建目录。

## 知识库查重结论

- 正式条目无 kyoto-cabinet 相关。
- 草稿：`knowledge/drafts/DRAFT-ghc-filesystem-1.5.14-ohos-filesystem-privilege-semantics.md`
  （umask 077→022 的 HMDFS 语义差异，含 E085 无关）。本配方的 umask 补丁与该草稿
  的"HMDFS 上 umask 077 目录创建失败"属于同一平台差异，但 kyoto-cabinet 的解法
  是上游 configure 补丁而非文件系统库适配，形成不了可复用方案（每个 autotools
  上游各打各的补丁），故不新建 draft，在 notes 中记录。

## 遗留

- kclangctest 需要管理端口环境，上游在 check-langc 中运行（14 条），已含在
  make check 内。
