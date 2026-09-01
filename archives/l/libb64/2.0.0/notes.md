# libb64 2.0.0 适配笔记（R01 bootstrap + 首轮 Adapt 本地验证）

## 任务身份
- task_id: libb64-2.0.0-r01-bootstrap-and-adapt-pc3-46-20260830T150543Z
- executor: pc3-46
- worktree: /storage/Users/currentUser/junshi_liu/worktrees/pc3-46-libb64-2.0.0
- 分支: feat/libb64-2.0.0
- HEAD: 06fbabfddc5af709d875c5bcd3390931e945fa92（自 origin/main 创建）
- 阶段: bootstrap + 首轮 Adapt（本地验证）；未进入 W3/finish/submit/PR

## 官方来源核验（三方交叉验证，未猜测）

| 项 | 值 | 来源 |
|----|----|------|
| 官方仓库 | https://github.com/stefantalpalaru/libb64（维护 fork，源出 sourceforge libb64，`libb64` GitHub 项目主页 + CHANGELOG 实证） | GitHub 页面 + FreeBSD ports 切换记录 |
| 正式标签 | v2.0.0 | GitHub stefantalpalaru/libb64/tags 页面 |
| 标签 commit | 293fb02de2c75f662bb9248eb6438b0125fc8ada（"Merge branch 'version2' of github.com:libb64/libb64"，2016-07-19） | GitHub tags 页面 |
| 官方 tarball | https://github.com/stefantalpalaru/libb64/archive/refs/tags/v2.0.0.tar.gz | GitHub archive 直链 |
| sha256 | 28c43c47674409fc50e7145d4c2d26dc1f3d200889c41205e7812c2b67f26382 | 实测下载计算 |
| 大小 | 15204 bytes | 实测 |
| 许可证 | CC-PDDC（公有领域） | 上游 LICENSE + README |

> 说明：分析端未预先确认来源/版本标识，执行端以 GitHub 官方维护仓库 + 正式标签 v2.0.0 为核验结论。
> 备选镜像（Savannah nongnu / waterlan xs4all）存在 libb64-2.0.0.tar.gz，但 GitHub 官方 tag 是权威发行点。

## 源码结构（解压 sha256-verified tarball 实测）

```
libb64-2.0.0/             31 文件
├── AUTHORS  BENCHMARKS  CHANGELOG  INSTALL  LICENSE  README  TODO
├── Makefile             # all: 空（无顶层目标）
├── include/b64/
│   ├── ccommon.h        # 2.0.0 新增公共头（版本宏 BASE64_VER_MAJOR/MINOR，size_t）
│   ├── cencode.h        # C encode API（公开）
│   ├── cdecode.h        # C decode API（公开）
│   ├── encode.h         # C++ 包装
│   └── decode.h         # C++ 包装
├── src/
│   ├── cencode.c        # 唯一 encode 实现
│   ├── cdecode.c        # 唯一 decode 实现
│   └── Makefile
├── base64/              # 独立 base64 命令行工具（base64.cc）
└── examples/
    ├── c-example1.c     # 硬编码 "hello world" encode->decode + strcmp 断言
    ├── c-example2.c     # stdin→3 文件 encode/decode
    └── loremgibson.txt
```

## 2.0.0 API 变化（头文件 + 实测 probe，2026-08-30）

| 项 | 1.2.1 | 2.0.0 |
|----|-------|-------|
| block 返回类型 | int | **size_t** |
| block 入参 | (const char*, int, ...) | **(const void*, size_t, ...) / (const char*, size_t, void*, ...)** |
| 辅助函数 | 无 | 新增 base64_encode_length() / base64_decode_maxlength() |
| 编码器状态 | step/result/stepcount | + chars_per_line（默认 0）+ cflags |
| encode 尾部换行 | blockend 固定输出 '\n' | **chars_per_line=0 时不输出** |
| padded decode | cnt = ptlen+1（多余尾字节 0x3e） | **cnt == ptlen，逐字节精确** |

关键实证：对 `SGVsbG8sIGxpYmI2NCE=` 直接（不 strip '='）解码，2.0.0 返回 14 字节且与明文逐字节一致；
分块（chunk=7）streaming decode 同样 total=14 精确。1.2.1 记录的 +1 尾字节缺陷在 2.0.0 已修正。

## 上游测试核验（严格审计）

- test/ tests/ 目录：不存在
- make check / make test 目标：4 个 Makefile 全部不含
- CMake/CTest / meson / autotools：不存在
- 文件名含 test 的源文件：不存在
- **上游正式自动化测试 = 0**。仅 examples/ 下 2 个示例程序（非正式测试套件）。

## 编译方式

上游 `src/Makefile` 硬编码 `LINK.o = gcc`、`CFLAGS += -Werror -pedantic`，不适合 OpenHarmony
交叉编译。**本次不打补丁、不修改任何上游源码**。conanfile.py 的 `build()` 直接：
1. 从 `tools.build:compiler_executables` 读取 OHOS clang（R33：不从 shell env 取）；
2. 用该 clang 编译 src/cencode.c、src/cdecode.c（`-Iinclude -O2 -fPIC`）；
3. 用 llvm-ar 归档为 libb64.a。

`package()` 拷贝 lib/libb64.a 与 include/b64/*.h（ccommon.h/cencode.h/cdecode.h + C++ 包装）。

## 首轮 Adapt 本地验证（实际执行证据）

| 命令 | 结果 |
|------|------|
| `clang -Iinclude -O2 -c src/cencode.c src/cdecode.c` | ✅ OK（ccommon.h `#elseif` 产生非致命 warning） |
| `llvm-ar rcs libb64.a cencode.o cdecode.o` | ✅ OK |
| `clang -Iinclude probe.c libb64.a -o probe` + 运行 | ✅ OK（encode=SGVsbG8sIGxpYmI2NCE= / padded cnt=14 / stripped match=1 / maxlength=17 / encodelength=20） |
| `clang -Iinclude probe2.c libb64.a -o probe2` + 运行 | ✅ OK（enc 无尾部换行 / padded cnt=14 match=1 字节精确 / streaming total=14 match=1） |

test_package/test_b64.c 6 项断言：encode 期望值 / 无尾部换行 / padded decode 精确 / streaming decode / 4 倍数长度 / 长度辅助函数。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | /tmp 只读 | E002 平台限制 | 全部用 $HOME/tmp 构建与探针 |
| 2 | 上游 Makefile 不适合交叉编译 | 硬编码 gcc/ar + -Werror -pedantic | 不打补丁，conanfile.py 直接调用 OHOS toolchain 编译真实 C 源文件 |
| 3 | ccommon.h 的 `#elseif` 非标准拼写 | 上游源码拼写（合法预处理指令应为 #elif） | 不修改上游；clang warning 非致命，编译通过 |
| 4 | 1.2.1 时代测试的 strip '=' 路径不再需要 | 2.0.0 padded decode 已修正为 cnt==ptlen | 2.0.0 test_b64.c 采用直接 padded + streaming 精确断言 |

## 依赖版本

无外部依赖。libb64 是纯 ANSI C 库，仅依赖 musl libc + clang 15（OHOS toolchain）+ llvm-ar。

## 交付物（bootstrap 骨架 + 首轮 Adapt）

| 文件 | 说明 |
|------|------|
| conandata.yml | 官方 URL + sha256（无 patches） |
| conanfile.py | 直接调用 OHOS toolchain 编译，零补丁 |
| test_package/conanfile.py | 编译并运行 test_b64 |
| test_package/test_b64.c | 真实 encode/decode 功能测试（6 项断言） |
| test_package/MANIFEST.yml | 上游测试声明（上游无自动化测试套件） |
| manifest.yaml | 版本级编译元数据（status: archived） |
| notes.md | 本笔记 |

## 未完成项 / 后续

- 本 task_id 完成 bootstrap + 首轮 Adapt 本地验证；未进入 finish/W3/submit/PR（analysis_approved_remote_ci: false，任务边界禁止远端写操作）。
- 待分析端下发后续轮次后：conan-verify（G1-G4 + L2/L4/L5）、finish、submit 流程。
