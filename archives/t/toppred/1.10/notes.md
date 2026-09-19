# toppred 1.10 适配笔记

## 编译环境
- 构建系统: autotools（上游 tag 归档自带 2014 年预生成 configure）
- 编译日期: 2026-09-19
- 编译器: clang/clang++（OHOS aarch64 交叉，clang 15.0.4）
- 状态: built

## 编译步骤

1. `conan create` 驱动：`source()` 下载 GitHub tag 1.10 tarball（官方 URL，sha256 校验）。
2. `build()`：
   - 构建期删除 configure 中 `umask 077` 包裹（E114，HMDFS setgid 目录导致 config.status 临时目录不可写）；
   - 聚合 env 脚本（generators_folder/**/*.sh）内 `/data/service/hnp/bin/bash` 文本替换为 `/bin/sh`（E386/经验汇总 §12.70①：profile [buildenv] 钉死 hnp bash 在 HMDFS 构建目录 getcwd 挂）；
   - `configure --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu --prefix=<package_folder>`（2014 config.guess/sub 不识别 ohos triplet 且无法解析 `-linux-ohos`；显式 gnu 双 triplet 使 config.guess 探测不运行——本包 AC_CANONICAL_HOST 结果仅用于 OSF/1 特例，无功能影响；a52dec/0.7.4 同年代同方案先例）；
   - `make -j1`；`make check -j1`（上游测试套件，顶层 SUBDIRS 含 test）。
3. `package()`：`make install` → `bin/toppred` + `share/toppred/`（GES/GVH/KD/CYTEXT 刻度与 DTD）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess/sub（2014-10-17）不识别 OHOS，`-linux-ohos` triplet 会被老 config.sub 拒绝 | 归档早于 aarch64-ohos triplet 支持 | 显式传 `--build/--host=aarch64-unknown-linux-gnu`，configure 不再运行 config.guess 探测（无 automake 自举需求，不引入 tool_requires） |
| 2 | configure 含 2 处 `umask 077` 临时目录包裹 | E114：HMDFS 强制 setgid，drwx--S--- 目录属主不可写 | 构建期文本替换移除（abiword-plugin 系同款 `_drop_umask_077`） |
| 3 | profile [buildenv] 将 SHELL/CONFIG_SHELL 钉死 hnp bash | E386：hnp bash 在 HMDFS 构建目录 getcwd 必挂（automake 测试驱动继承） | §12.70①：generators_folder 聚合脚本文本替换为 /bin/sh（禁同名二次 save_script） |
| 4 | libgd/gnuplot 缺失 | 上游可选依赖：configure 降级为警告（图形拓扑不可用），全部测试以 `-g none -t none` 运行 | 不引入依赖，走上游默认降级路径 |

## 源码修改

无补丁文件（patches 为空）。仅构建期对生成物 configure 做 E114 替换（不进源码树 diff）。

## 依赖版本

无外部依赖（仅 libm：pow/sqrt；libgd/gnuplot 为可选图形依赖，走上游降级）。

## 验证结果

### 上游测试五维账本（R51/§10.1 口径）

- `N_static` = 7：test/Makefile.am `TESTS` 注册口径（toppred/hydro/detect_segments/seqlen/construct_topos/naming/math）；`float.test` 被上游注释未注册，不计入
- `N_registered` = 7（automake 简单测试驱动）
- `N_executed` = 6（make check 实际运行）
- 未执行 = 1：math.test——脚本首行 `(gnuplot --version) || exit 77`，OHOS 无 gnuplot，上游自带守卫跳过（automake 计 SKIP）；且其 `-g png` 路径另需 libgd
- `N_consumer` = 1（test_package/test.sh：min_seqlen 场景端到端 + 3 刻度加载，断言 5 处）

```bash
# make check 结果（conan create 内真实执行，日志见 .ci_logs/）
# PASS=6 SKIP=1（math.test 上游 exit-77 守卫）
```

### 消费者测试

test_package/test.sh（conanrun 环境）：打包后二进制 + 编译期 pkgdatadir 指向的包内刻度文件
- 断言 1：`Found: 1 segments`（min_seqlen 序列）
- 断言 2：`TRANSMEM 1 21 21`（跨膜区段位置）
- 断言 3-5：GES/GVH/KD 刻度逐一 `-H` 加载并校验输出

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/toppred | ~150KB | 膜蛋白拓扑预测 CLI |
| share/toppred/ | 4 刻度 + DTD | 运行时数据（编译期 pkgdatadir 或 TOPPREDDATA 解析） |

## 注意事项

- 包内刻度文件由 conan DESTDIR 暂存安装，编译期 pkgdatadir 指向失效的暂存路径——运行 toppred 必须设置 `TOPPREDDATA=<包>/share/toppred`（上游官方机制，test_package 已按此验证）。
- math.test 在提供 gnuplot+libgd 的环境下才会真正执行；OHOS 环境跳过属上游设计，非本次适配导致。
- commands.json（软件级）声明 toppred 为 tool 类型。
---

**编译结束**: 2026-09-19 03:51
**最终状态**: built
