# mobile-broadband-provider-info 20240407 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-09-19
- 编译器: clang 15.0.4（aarch64-unknown-linux-ohos，本机真机原生构建）
- 状态: built
- 环境: 鸿蒙PC 真机（aarch64-linux-ohos），meson 1.9.1 + ninja 1.13.2 + xsltproc（libxslt）+ xmllint（libxml2）

## 编译步骤

上游为纯 XML/XSLT 数据包（serviceproviders.xml + serviceproviders.2.dtd + apns-conf.xsl），
meson.build 声明 `project(..., 'c')` 但无任何 C 产物，唯一构建步骤是 xsltproc 生成 apns-conf.xml：

```bash
# 1. 真机原生 meson 构建（编译器探测坑见下表）
export PATH=$HOME/usr/local/bin:/data/service/hnp/bin:$PATH
CC=/data/service/hnp/bin/clang AR=/data/service/hnp/bin/llvm-ar \
  meson setup _build --prefix=$HOME/usr/local
meson compile -C _build            # xsltproc 生成 _build/apns-conf.xml
# 2. 上游测试（R51，2/2 通过，详见下文验证结果）
meson test -C _build --print-errorlogs
# 3. DESTDIR 试装验证消费布局
meson install -C _build --destdir ~/tmp/mbpi/stage
# 4. conan 化验证
conan create . -tf test_package   # W3 全量验证（见 reports/）
```

Conan 配方要点（参照 iso-codes 4.20.1 数据包先例）：
`package_type="unknown"` + `resdirs=["share"]`，`MesonToolchain` 生成 machine file，
`build()` 内 `meson setup --prefix=/` → `meson build` → `meson test`（上游套件内嵌执行），
`package()` 用 `Meson.install()`（destdir 语义）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `meson setup` 报 Unknown compiler(s)/Unknown linker(s) | 数据包无编译产物，meson 仍按 project(..., 'c') 做编译器+静态链接器探测；探测子进程不走 shell PATH 搜索，本机 PATH 中的 clang/ar（hnp 符号链接）spawn 报 ENOENT | 裸构建：setup 前显式注入 `CC=/data/service/hnp/bin/clang AR=/data/service/hnp/bin/llvm-ar`。conan 化：CC 由 profile `tools.build:compiler_executables` 经 machine file 注入，ar 不在其默认键里——在 generate() 里解析 `shutil.which("llvm-ar") or shutil.which("ar")` 写入 `tc.binaries["ar"]`（machine file `[binaries] ar=绝对路径`）绕开 PATH 搜索 |
| 2 | 数据安装布局 | 数据包必须 `--prefix=/` 配合 Conan destdir 语义，才能得到 `<pkg>/share/...` 平铺布局 | meson setup `--prefix=/`；若用真实前缀会在包内嵌套绝对前缀目录，W2 结构校验失败 |
| 3 | .pc 的 pkgdatadir 固化绝对前缀 | 上游 pc 文件 pkgdatadir 硬编码构建前缀，设备侧 `pkg-config --variable=database` 消费会拿到断链路径 | package() 重写为 `pkgdatadir=${pcfiledir}/../mobile-broadband-provider-info` 相对契约 |
| 4 | `EXPECTEDFAIL: check-blanks` 易误读 | 上游 check-blanks 声明 `should_fail: true`（grep 命中缩进违规才算"失败"）；当前数据无违规 → grep exit 1 → meson 汇总显示 EXPECTEDFAIL | 属通过语义；以 meson test 总退出码 0 为准，勿按 FAILED 判读 |

## 源码修改

无补丁（conandata.yml `patches: {}`）。上游源码零修改，适配全部在配方层完成。

## 依赖版本

无编译期依赖（纯数据包，配方无 requires）。构建/测试工具链（由环境提供，非 conan requires）：
- meson 1.9.1 / ninja 1.13.2
- xsltproc / xmllint（libxslt 1.1.45.2 + libxml2 2.15.3 的命令行工具，制品仓已发布，`conan install --build=never` 验证 binary=Download）

## 验证结果

上游测试（R51 三步法，真机实测 2026-09-19）：

```text
$ meson test -C _build --print-errorlogs
1/1 upstream:check-blanks  OK      0.02s    ← EXPECTEDFAIL（should_fail 语义，见问题 #4）
1/1 upstream:xmllint       OK      0.05s    ← xmllint --valid 按 DTD 校验通过
Ok: 1  Expected Fail: 1  Fail: 0  Skipped: 0    退出码 0
```

- 上游测试用例总数：2（meson.build 中 `test()` 清点：xmllint + check-blanks）
- 通过：2/2（100%，其中 check-blanks 为 EXPECTEDFAIL 即上游设计的预期失败=通过）
- 测试日志存证：`_build/meson-logs/testlog.txt`，SHA256
  `359c65fabb917c725a44fb5661374d30283e684490f4b1cf12b88e6559f39b76`
- test_package 消费者校验：`test_verify.py` 19/19 断言 PASS（数据契约 + pkgdatadir 解析），
  另对安装树执行 `xmllint --noout --valid serviceproviders.xml` 重放通过。
- W3 conan create 全量验证（conan-verify G0-G4 全 PASS，真机 2026-09-19）：
  conan create 内嵌执行 meson test——
  `1/2 check-blanks EXPECTEDFAIL 0.04s` + `2/2 xmllint OK 0.06s`
  （Ok: 1, Expected Fail: 1, Fail: 0，退出码 0，2/2 通过语义）；
  test_package 在包根消费布局下运行 test_verify.py 全断言 PASS +
  xmllint DTD 重放 PASS（安装到包根后按 pcfiledir 相对路径定位数据库）。
  报告：`reports/conan-verify-report.md`、`reports/conan-create.log`。
- 试装布局：`share/mobile-broadband-provider-info/{serviceproviders.xml,serviceproviders.2.dtd,apns-conf.xml}` +
  `share/pkgconfig/mobile-broadband-provider-info.pc`（694 providers / 154 countries，
  apns-conf.xml root=apns version=8 由 xsltproc 生成）。

## 注意事项

- 本包为架构无关数据包：无二进制产物、无库文件，`cpp_info` 四目录均置空仅保留 resdirs=share；
  消费方（ModemManager/NetworkManager 类）通过 pkg-config 变量 `database`/`pkgdatadir` 定位 XML。
- 源 URL 为 GNOME 官方 https 下载源（R39/PF7），sha256 与上游清单一致。
- 上游 LICENSE 为 PUBLIC DOMAIN（COPYING：certification of public domain，LTS 版本仓库自 2019 起声明），
  配方 `license = "public-domain"`。
---

## 对话记录

### 对话 #1：init-build + 真机探索性编译（2026-09-19）
- W0/W1 依赖预检：纯数据包无 requires()，基线同步 origin/main。
- R47 lang-preflight：C（构建系统 meson），与适配要求匹配。
- meson setup/compile/test：注入 `CC=/data/service/hnp/bin/clang`、
  `AR=/data/service/hnp/bin/llvm-ar` 后通过；apns-conf.xml 生成成功
  （694 providers / 154 countries）。
- 上游测试 2/2 实测：check-blanks（EXPECTEDFAIL，通过语义）+ xmllint OK。

### 对话 #2：conan 配方与验证闭环（2026-09-19）
- 配方以 iso-codes/4.20.1 数据包先例为模板；`--prefix=/` + resdirs=["share"]。
- conan-verify G2 根因：meson 静态链接器探测 Popen PATH 搜索对 hnp 符号链接
  报 ENOENT → generate() 写 `tc.binaries["ar"]` 绝对路径修复，G0-G4 全 PASS。
- W3 本地 CI 全绿；finish 三重门禁通过，`.ci-result.json` 自动写入。
- configure 参数：meson setup `--prefix=/`（约 1s）；编译耗时 <5s（纯数据转换）；
  测试耗时约 0.1s。

**编译结束**: 2026-09-19 22:46
**最终状态**: built
---

**编译结束**: 2026-09-19 22:50
**最终状态**: built
