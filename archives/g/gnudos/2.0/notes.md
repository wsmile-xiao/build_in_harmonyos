# gnudos 2.0 适配笔记

## 编译环境
- 构建系统: autotools（release tarball 自带 configure）
- 编译日期: 2026-09-14（GLM-19 初稿构建）；2026-09-19 GLM-56 接管后在新基线（upstream/main 1326b73f4e）重建闭环
- 编译器: clang（OHOS aarch64 交叉工具链）
- 状态: built
- worktree: ~/qzy/GLM-56-gnudos-2.0（GLM-19 死 worktree 移除，其未提交配方草稿已备份 ~/tmp/uc2/GLM-56-gnudos-2.0/glm19-gnudos-salvage.tar.gz 并全部吸收）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cannot guess build type 风险 | 老年版 config.guess/sub | os==OHOS 时追加 `--build=aarch64-unknown-linux-gnu`（jwhois 先例） |
| 2 | E011 umask 077 风险 | HMDFS 上 config.status 临时文件不可写 | build() 内替换 022（gsl 同款） |
| 3 | configure 报 working directory cannot be determined（E386 家族，getcwd 风暴 287+ 条） | ①profile buildenv 的 CONFIG_SHELL 指向 hnp bash，其对 HMDFS 目录 getcwd() 必挂；②conan 缓存 build-release 子目录本身在 HMDFS 触发 getcwd 风暴（与 shell 无关） | ①tc.generate(env=env) 注入 CONFIG_SHELL=/bin/sh、SHELL=/bin/sh（覆盖 profile buildenv）；②build()/package() 改为源码目录内原地 configure/make——self.run 不传 cwd（子进程从健康 worktree cwd 启动），命令内 `cd <src> &&` 由 shell 内部 PWD 路径进入（§12.38①②） |
| 4 | ld.lld: undefined symbol: fcloseall | glibc 扩展函数，musl 无 | 补丁 0001：4 处语句式调用改 fflush(NULL)（刷所有输出流，流在进程退出时自然关闭） |
| 5 | error: unknown type name '__mode_t' | glibc 内部类型别名，musl sysroot 只有 mode_t | 补丁 0002：prime/edit.c 参数类型 __mode_t → mode_t |
| 6 | make install 试图写 /lib（Read-only file system） | toolchain 默认参数 `--libdir=${prefix}/lib` 未加引号，shell 在命令构造期把 ${prefix} 展开为空 | 含 ${...} 的 configure 参数加单引号原样传递（akku 同款），make 阶段才用真实 --prefix 展开 |
| 7 | configure 报 Unable to find ncursesw or ncurses | 配方未生成依赖标志 | generate() 补 AutotoolsDeps(self).generate()（CPPFLAGS/LDFLAGS/LIBS 进 conanbuild 环境） |

## 依赖

- ncurses/6.6（制品仓已发布；mino/prime 为 TUI 程序，运行时经 conanrun 环境解析动态库）

## 上游测试清点（R51 第一步）

- 各 Makefile.am 无 TESTS/check_PROGRAMS；tarball 无 tests/ harness
- **上游静态测试数 N_static = 0**（如实申报）

## 消费者测试（test_package，N_consumer = 1）

`test.sh`：经 conanrun 环境运行真实 mino/prime 二进制（同时验证打包的 ncurses 依赖可解析）：

1. `mino --version` 输出含 `2.1`（程序内部版本号），退出码 0
2. `prime --version` 输出含 `2.1`，退出码 0

注：包版本 2.0，程序自报版本 2.1（上游内部常量），断言以实际输出为准。

## 四维测试账本

| 维度 | 数值 | 来源 |
|---|---|---|
| 上游静态声明 N_static | 0 | tarball 清点 |
| 构建系统注册 N_registered | 0 | 无 check 目标 |
| 实际执行 N_executed | 0 | 无上游套件 |
| 未执行分类 | 0 | — |
| 消费者测试 N_consumer | 1（2 断言） | test_package/test.sh |

## 源码修改

两个 portability 补丁（详见 patches/ 与 conandata.yml，strip: 1）：

1. `patches/0001-musl-fcloseall-to-fflush.patch`——src/prime/main.c、src/mino/file.c、src/mino/main.c（×2）共 4 处 `fcloseall()` → `fflush(NULL)`；原因：musl 无该 glibc 扩展；结果：链接通过、行为等价（退出路径刷缓冲）。
2. `patches/0002-musl-mode_t-type-name.patch`——src/prime/edit.c 参数类型 `__mode_t` → `mode_t`；原因：musl sysroot 无 glibc 内部别名；结果：编译通过。

## 路径 B 判断

- 本任务踩到的 E386 双层修法（CONFIG_SHELL 路由 + 原地 configure）与 ${...} 引号问题均为已沉淀知识（经验汇总 §12.38 等），知识库查重命中既有条目，无新增可复用知识；fcloseall/mode_t 为常规 musl 移植，无独立错误签名。
- 结论：**纯路径 A，不申报路径 B**。

## 验证结果

- conan-verify（2026-09-19 GLM-56，基线 1326b73f4e）：**Verdict PASS**（G0-G4），conan create + 消费者测试全过（`ALL CONSUMER TESTS PASSED`）。
- W3 本地 CI：见 reports/w3-local-ci.log。
- conandata.yml 官方 URL 保持标量形态（E017 注入恢复后核对，ghfast 计数 0）。
---

**编译结束**: 2026-09-19 02:44
**最终状态**: built
