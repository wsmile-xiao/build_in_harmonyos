# KDE PIM/KF6 库上游测试数据双注入：iso-codes + tzdata

## 错误特征

KDE PIM/KF6 库（依赖 KF6::I18nLocaleData 的 KCountry、或以命名时区构造 QDateTime 的库）
上游 autotest 在 OHOS 上出现两类数据缺失型 FAIL：

```
# 类型 1：iso-codes 缺失（KCountry 退化）
QWARN  : IcaoVdsParserTest::testVaccinationCertificate() kf.i18n.localeData: Unable to open iso_3166-1.json "" "No file name specified"
FAIL!  : IcaoVdsParserTest::testVaccinationCertificate() Compared values are not the same
   Actual   (vac.country())      : "AUS"
   Expected (QLatin1String("AU")): "AU"

# 类型 2：zoneinfo 缺失（QTimeZone 失效）
QWARN  : NlCoronaCheckParserTest::testCertificate() Unable to determine system time zone: please check your system configuration.
FAIL!  : NlCoronaCheckParserTest::testCertificate() Compared values are not the same
   Actual   (t.certificateIssueDate()) : 2021/07/28 12:00:00.000[CEST]
   Expected (QDateTime(..., QTimeZone("Europe/Amsterdam"))): Invalid QDateTime

# 伴生：KF6 相对 DT_NEEDED
Error loading shared library ../../bin/libKF6I18n.so: (needed by .../libKF6I18nLocaleData.so)
```

## 根因

1. **KCountry 数据链**：KF6 I18nLocaleData 的 `KCountry::fromAlpha3()` 在运行时经
   `QStandardPaths::locate(GenericDataLocation, "iso-codes/json/iso_3166-1.json")`
   定位 ISO 3166-1 表（isocodescache.cpp `isoCodesPath()`）。OHOS 无
   /usr/share/iso-codes，locate 落空后 KCountry 退化返回原始 alpha3 码。
2. **QTimeZone 数据链**：Qt6 TZIF 后端 `openZoneInfo()` 依次查 `$TZDIR` →
   /usr/share/zoneinfo/ → /usr/lib/zoneinfo/（qtimezoneprivate_tz.cpp）。OHOS 三处皆无，
   `QTimeZone("Europe/Amsterdam")` 构造为 invalid，QDateTime 时区比对全 FAIL。
3. **相对 DT_NEEDED**：ohpcd 已发布 KF6 包内 libKF6I18nLocaleData.so 的 NEEDED 是
   build 树相对路径 `../../bin/libKF6I18n.so`；musl 加载器按 LD_LIBRARY_PATH 每个条目
   作前缀解析相对 NEEDED——farm 目录本身必须出现在 LD_LIBRARY_PATH。

## 解法（三件套）

1. `tool_requires("iso-codes/4.20.1")` + 测试环境 `XDG_DATA_DIRS` prepend 包内
   `share/` 树（KCountry 经 GenericDataLocation 命中）
2. `tool_requires("tzdata/2026.3")` + 测试环境 `TZDIR` + `QT_ZONEINFO` 指向包内
   `lib/python3.12/site-packages/tzdata/zoneinfo`（Python tzdata 布局）
3. test_package 的 symlink farm 建在 **`<layout-build>/../bin`**（exe 在
   `<layout-build>/<compiler-id>/` 下，`../../bin` 相对解析点 = `<layout-build>/../bin`），
   并把 farm 目录加进 LD_LIBRARY_PATH

两个数据包都是 tool_requires（测试时数据不进消费图，kfilemetadata shared-mime-info
先例），package_id 保持干净。

## 验证

khealthcertificate 26.04.3（PR #10745）：注入前 icaovds 2 FAIL + nlcoronacheck 1 FAIL；
注入后 5/5 全绿（divoc/eudgc/icaovds/nlcoronacheck/shc）+ test_package 1/1。

## 红线

- iso-codes/tzdata **不得**用 requires()（会污染下游消费图的 package_id）
- XDG_DATA_DIRS 用 prepend_path 不用 define（保留系统默认条目）
- tzdata 包布局是 Python site-packages，版本升级可能漂移——找不到目录时 fallback
  到构建树复制（kfilemetadata staged mime DB 模式）

## 适用范围

所有依赖 KF6::I18nLocaleData/KCountry（kcontacts、kosmindoormap、khealthcertificate、
kopeninghours 等）或以命名时区做断言（kcalendarcore 及下游 PIM 库）的 KDE 件适配。
