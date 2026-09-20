# mobile-broadband-provider-info 20240407 测试报告

> **测试日期**：2026-09-19  
> **构建目标**：OpenHarmony PC aarch64 (`os=OHOS`, `arch=armv8`)  
> **包引用**：`mobile-broadband-provider-info/20240407@ohpcd/stable#375c16fea1000f484afc6123d3a436b2:6b129b068851896169fae42d399fa922d239ce8a#7876ff934aa8aa77bdfaec9728204038`

## 测试摘要

| 测试集合 | 用例 | 结果 | 补充计数 |
|----------|-----:|------|----------|
| 上游 meson test（check-blanks + xmllint DTD） | 2/2 | PASS | Ok: 1 + Expected Fail: 1, Fail: 0 |
| conan test_package 消费者校验 | 1/1 | PASS | MBPI_VALIDATION_PASS assertions=19 |
| 安装树 xmllint DTD 重放 | 1/1 | PASS | serviceproviders.xml（694 providers / 154 countries） |

唯一测试用例数为 4（上游 2 项 + 消费者 1 项 + DTD 重放 1 项），全部通过；
消费者内部的 19 项检查是断言数，不重复计作 19 个测试用例。
`check-blanks` 在上游声明 `should_fail: true`（grep 命中缩进违规才算失败），
当前数据无违规 → grep 退出码 1 → meson 记为 EXPECTEDFAIL，属通过语义，
meson test 总退出码为 0。

## 上游测试清单（R51 清点）

上游 `test/` 目录在根 `meson.build` 注册 2 个 `test()`，无 ctest/pytest 体系：

1. `check-blanks`（`should_fail: true`，探测数据文件缩进违规）
2. `xmllint`（`--noout --valid serviceproviders.xml`，DTD 校验）

构建期另有 `xsltproc` 由 serviceproviders.xsl 生成 `apns-conf.xml`，属构建步骤
而非测试用例。未发现被条件跳过或未注册的测试。

## W3 conan create 全量验证证据

- 配方构建内嵌执行 `meson test`（build() 中调用），原始日志：
  `Ok: 1, Expected Fail: 1, Fail: 0`，meson test 总退出码 0。
- meson testlog.txt（conan cache 构建目录 build-release/meson-logs/）
  SHA-256：`dc796cf48915a78c6bf42c94e26e980145c71a1e5c940477f95250d6f022cacb`。
- W3 完整日志 `reports/conan-create.log`（首次构建 197 行版）SHA-256：
  `a5cd2fe6e8e3dfbcd210586f747a46c481b3b9dde2465a556491b625e28fc77f`；
  conan cache 二次命中时 conan_verify.py 会以短日志覆写该文件，当前归档
  93 行短版哈希 `5f752f404cb3988980ec47e81191c4cdf8afe3f1d03b657d8e117f0b4a4da63b`，
  `reports/w3-local-ci.log` 哈希 `9f59c60f187ece8655c70d7d73001e3c4c3afc0310145190d43c28e423884536`。

## 消费者与目标验证

`test_package/test_verify.py` 以包根安装布局为输入，共 19 项断言全部通过
（`MBPI_VALIDATION_PASS assertions=19`）：

- 数据契约：root=serviceproviders、format=2.0、DTD 三要素
  （country/provider/name/gsm/cdma）、694 providers、154 countries；
- 生成物：apns-conf.xml root=apns、version=8（xsltproc 产物）、
  与 serviceproviders.xml 的 provider 数一致；
- 消费契约：`mobile-broadband-provider-info.pc` 的 pkgdatadir 已重写为
  `${pcfiledir}/../mobile-broadband-provider-info` 相对路径，
  `pkg-config --variable=database` 在安装树上解析为真实存在的 XML 文件。

另对安装树执行 `xmllint --noout --valid` 重放 DTD 校验通过。
