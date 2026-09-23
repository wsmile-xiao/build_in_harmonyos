# libmwaw 0.3.23 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-09-19
- 编译器: clang 15 (aarch64, OHOS 6.0)
- 状态: built
- 包定位: 库包（libmwaw-0.3 + 头文件）；命令行工具由 libmwaw-tools/0.3.22 单独适配（同上游源码树）

## 编译步骤

1. conan source 下载 libmwaw-0.3.23.tar.xz (SourceForge, sha256 ac3590f6…b399eb)
2. 应用 2 个 OHOS 移植补丁（config.guess HarmonyOS 识别 / configure umask）
3. staging 依赖：从 librevenge/zlib conan 包复制 .a 到 build/depstaging/lib，
   复制头文件，本地生成 prefix 正确的 .pc（zlib / librevenge-0.0 /
   librevenge-generators-0.0 / librevenge-stream-0.0）
4. PKG_CONFIG_PATH=depstaging/lib/pkgconfig ./configure
   --with-docs=no --disable-tools --enable-static --disable-shared
5. make -j4 && make install
6. 打包 lib/(libmwaw-0.3.a) + include/libmwaw-0.3/ + licenses/

## 上游测试清点（R51）

- 源码树无 tests/ 目录；`find . -name Makefile.am | xargs grep -l "check_PROGRAMS\|TESTS"` 无匹配（0.3.23 解压树实测）——上游无自动化测试套件
- 与 libmwaw-tools/0.3.22 的清点结论一致（同上游项目）
- 上游测试计数：0/0（无测试入口；功能验证依赖 test_package 的 C++ API 实质测试）

## 与历史经验（libmwaw-tools/0.3.22, W0b）逐项比对

| 0.3.22 历史坑 | 0.3.23 处理 | 结论 |
|------|------|------|
| config.guess 不识别 HarmonyOS | 补丁 0001 按 2024 版新风格重生成（GUESS= 赋值，case 不带引号） | 沿用，上下文重生成后 dry-run + 实测输出 aarch64-unknown-linux-ohos |
| config.sub 拒绝 linux-ohos 三元组 | 0.3.23 自带 2024 版 config.sub，原生接受 linux-ohos*（sh config.sub aarch64-unknown-linux-ohos 实测通过） | 补丁不再需要，未携带 |
| config.status umask 077 在 HMDFS Permission denied | 补丁 0002（即 0.3.22 的 0003，dry-run 原样适用） | 原样沿用 |
| librevenge .pc prefix=/ 且 .la 失效 | 配方内 staging .a + 本地生成 .pc，PKG_CONFIG_PATH 指向 staging | 原样沿用 |
| zlib/1.3.1 非 PIC 静态链入共享库 R_AARCH64 报错 | requires zlib/1.3.1.1 override=True（同源 -fPIC 变体） | 原样沿用（shared=True 时必需；默认静态构建统一依赖也避免版本冲突） |
| --with-docs=no（CI 无 doxygen） | 沿用 | 原样沿用 |
| 上游无测试套件 | 重新清点确认 | 沿用，0/0 |

## 与 0.3.22 的偏差及理由（W0b 偏离声明）

1. **--disable-tools**：0.3.22 是工具包，必须构建 mwaw* 可执行文件；本包是库包，
   工具由 libmwaw-tools 承载，库包无消费者需要它们。禁用后 make install 只落
   lib/ 与 include/，打包干净且省一轮工具链接。
2. **去掉 config.sub 补丁**：0.3.23 上游更新了 config/config.sub（1992-2024），
   原生支持 linux-ohos*；0.3.22 的 0002 补丁上下文已漂移（Hunk FAILED），且无必要。
3. **shared 选项（默认 False）**：与 librevenge/0.0.5 库包先例一致；默认静态
   （--enable-static --disable-shared），shared=True 时 --disable-static
   --enable-shared 走 0.3.22 同款 staging 链接。

## 遇到的问题与解决方案

| 问题 | 根因 | 解决方案 |
|------|------|----------|
| 2024 版 config.guess 无 HarmonyOS 分支，原生运行 "unable to guess" | uname -s = HarmonyOS，主 case 无匹配 | 补丁 0001 插入首分支，输出 aarch64-unknown-linux-ohos（TMPDIR 可写时实测 rc=0） |
| 0.3.22 的 config.guess/config.sub 补丁 Hunk FAILED | 0.3.23 带 2024 版 autotools 脚本，上下文漂移 | 0001 按新上下文重生成；0002（config.sub）确认不再需要后移除 |
| 补丁重生成后 conan W3 仍报 "Failed to parse patch"（0001） | conan 底层 patch_ng 对 hunk 计数严格（GNU patch 容忍计数偏差）；0001 首版声明 4/8 实为 3/7 | 修正为精确计数 -199,3 +199,7，本地无 conan 时用设备 patch_ng.fromfile 预验 |
| 0002 patch_ng apply 返回 False（GNU dry-run 却通过） | patch_ng 按声明行号匹配、搜索范围小；0002 沿用 0.3.22 行号 22788，0.3.23 实际在 24582 | 按 0.3.23 实际行号重生成（GNU dry-run 通过≠patch_ng 可应用，需以 patch_ng 实测为准） |
| conan create 编译成功但 package_info() 报 "cpp_info.requires includes package 'zlib::', but such package is not a direct requirement" | override=True 只统一版本、不产生直接依赖边；cpp_info.requires 只能引用直接依赖 | 改用 force=True：保持 zlib/1.3.1.1 直接依赖边的同时替换 librevenge 传递链的 1.3.1（plain+override 双声明会被 "Duplicated requirement" 拒绝，实测） |
| make install 后包 bin/ 出现 mwawFile/mwawZip | 0.3.23 的 --disable-tools 只关 src/conv 转换工具，src/tools 检查工具无条件构建 | package() 内删除 bin/（库包交付物不含工具；工具由 libmwaw-tools 承载） |
| L5 基线对比报 lib/libmwaw-0.3.la 逐轮漂移 | .la 是文本文件，dependency_libs 内嵌每轮随机命名的私有 CONAN_HOME/staging 绝对路径（同 libserial .pc prefix 抖动家族，副本归一化未覆盖 .la） | package() 内删除 *.la（conan 下游走 CMakeDeps 元数据，.la 只会像 librevenge 的 .la 一样带 prefix 污染），并按提示删除 reports/baseline.json 重立基线 |
| 包内 lib/pkgconfig/libmwaw-0.3.pc 内嵌每轮随机前缀（W4 审计 P3：两次运行 package revision 不同） | autotools 安装的 .pc 以构建期 prefix 硬编码，与 .la 同族 | package() 内删除安装的 pkgconfig/ 目录（下游走 cpp_info/CMakeDeps 元数据；配方自生成的 staging .pc 不受影响），同步重立基线 |
| 设备 patch(1) 二进制 apply 报 rc=0 但文件 sha256 不变 | HMDFS 上就地改写静默丢失（设备工具异常，已记反馈） | 验证改用 dry-run（hunk 比对）+ Python 应用后实测；conan 构建走 Python 补丁应用不受影响 |

## 源码修改

2 个 OHOS 移植补丁（见 patches/）：
- 0001: config.guess 增加 HarmonyOS 识别（GUESS=$UNAME_MACHINE-unknown-linux-ohos）
- 0002: configure/config.status umask 077→022（HMDFS 兼容，沿自 0.3.22 补丁 0003）

未修改上游测试用例（上游无测试套件）。

## 依赖版本

- librevenge/0.0.5 (conan, W0 实测 available)
- zlib/1.3.1.1 (conan force 直接依赖, W0 实测 available；同源 -fPIC 静态变体)

## 验证结果

- W3 本地 CI（finish 内嵌，conan create + test_package）：PASS
  - conan create libmwaw/0.3.23（ohos-aarch64，静态默认）成功
  - mwaw_api_test 三项 PASS（4 个 CHECK 断言全过）
- conan-verify 门禁：G0/G1/G2/G3/G4/L2/L4/L5 全部 passed（verdict=PASS）
- 上游测试：0/0（无测试入口，清点证据见 reports/test-report.md）
- 新增消费者用例：1/1 通过（断言 4/4，口径为 CHECK() 调用次数）
- 逐轮证据文件见 reports/（conan-verify-report.json、conan-create.log、w3-local-ci.log）与 .ci-result.json

## 注意事项

- 库包默认静态；下游若构建 .so 并链接本包，依赖本包静态产物的 PIC 属性与
  librevenge/0.0.5 相同（libmwaw-tools/0.3.22 已实证 librevenge .a 可链入 .so）
- commands.json 不适用（纯库包，无 bin/ 产物）
- cpp_info.requires 已声明 librevenge/zlib，下游 CMakeDeps 链接顺序由 conan 保证
