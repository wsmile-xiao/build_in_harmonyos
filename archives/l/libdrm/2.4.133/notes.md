# libdrm 2.4.133 适配笔记（HarmonyOS PC）

## 编译环境
- 构建系统: meson
- 编译日期: 2026-09-05
- 编译器: clang/clang++（OHOS aarch64 工具链 15.0.4）
- 状态: published（conan-verify 通过 + W3 本地 CI 模拟通过，finish 已确认）
- 适配目的: 为 mesa GLX/EGL 变体提供依赖（R36 拓扑序首包，服务于 f3d 3.5.0 全量测试链）

## 编译步骤

```bash
# 探索期构建（宿主同架构，交叉变量由环境提供）
meson setup build -Dbuildtype=release
ninja -C build -j2
meson test -C build          # 上游测试，见下
meson install -C build --destdir <staging>   # staging 验证
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 6 个 `*-symbols-check` 测试在 OHOS 上全 SKIP（exit 77），报 `unknown symbol exported: _init/_fini`（探索期 shared 构建） | `symbols-check.py` 用 `platform.system()` 判定平台，OHOS 返回 `HarmonyOS`，既不命中 Linux 白名单分支 | 补丁 1：平台判定加入 `in ('Linux', 'HarmonyOS')`（与 mesa 24.3.4 归档 0001 补丁同口径） |
| 2 | conan create（静态库）下 6 个 symbols-check 全部 exit-77 静默跳过，比对从未执行（W4 独立审计发现） | `nm -gP <静态库>` 输出 GNU 归档成员头行 `/path/libdrm.a[xf86drm.c.o]:`，单字段触发 `fields[1]` IndexError → 裸 except exit(77) | 补丁 2：跳过单字段归档头行；配方改为在共享配置下运行全量上游测试（symbols-check 白名单比对只对共享库有意义——静态库向 nm 暴露全部内部全局符号，比对必然失真），测试后恢复静态配置打包（R26） |
| 3 | `/tmp` 写入失败 | OHOS `/tmp` 只读（E002） | meson/构建临时目录放在工作区 `$TMPDIR`/`.build-cache` |
| 4 | `check_env` 探测 automake 时 NameError 崩溃 | automake shebang 指向悬空 perl 链接，spawn 失败；框架脚本 except 分支引用未绑定 `e` | `rm -f && ln -s` 修复 perl 链接（R5）；automake 对 meson 工程无用，残余 `Automake::Config` 缺失告警不阻塞 |
| 5 | finish 的 W3 被 junk_check 拦截 `util-linux-login/.ci-trigger` | HEAD==origin/main（无本地提交）→ junk_check 落 full 全仓扫描，扫出 main 里其他任务遗留的标记文件 | 先把本包改动 commit 成提交（只 add 自己的 archives 目录），junk_check 走 incremental diff 模式即通过；`.ci-trigger` 本身已用 `git checkout --` 恢复 |

## 源码修改

- `patches/0001-symbols-check.py.patch`（+8/-2，仅测试脚本，不改动被编译的库代码）：
  1. 平台判定 `platform.system()` 加入 `HarmonyOS`（+1/-1）。
  2. `nm -gP` 输出解析跳过单字段归档成员头行（静态库下上游脚本崩溃点），
     使符号比对真实执行而非 exit-77 静默跳过。

## 依赖版本

- 无强制外部依赖（libdrm 2.4.133 为依赖链底层）

## 验证结果

conan create（共享配置测试树，最终 meson test 段，见 reports/conan-create.log）：

- 10 项上游测试全部按原样执行：6 个 symbols-check（真实比对 472 项白名单符号）+ threaded/hash/drmsl/drmdevice。
- Ok: 8 / Fail: 0 / Skipped: 2（threaded、drmdevice 按 exit-77 上游约定环境跳过：无 DRM 设备；未关闭、未删减）。
- test_package 消费测试 6 项断言全 PASS（xf86drm 错误路径契约，CI 无 DRM 设备可确定性通过）。
- 打包验证（R26 默认静态）：6 个 .a + pkgconfig + 头文件两层布局（include/、include/libdrm/）。

## 注意事项

- `conan tools.meson.Meson` 无 `compile()` 方法（正确 API `build()`），`configure()` 也不接受
  `-D` 参数（重配置需 `meson configure <builddir> -D...`，模板缺陷均已修正）。
- symbols-check 类测试设计面向共享库；静态打包的配方若要保留全量上游测试，
  需在共享配置下运行测试后再恢复静态打包（本配方的做法）。
- test_package 消费测试走非 DRM fd 的错误路径（drmGetVersion/drmGetCap）。
- 配方默认静态库（R26 系统同名库隔离），shared 选项保留。

---

**编译结束**: 2026-09-05 22:39
**最终状态**: published
