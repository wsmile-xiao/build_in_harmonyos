# DRAFT: KIO HTTP 传输层替换为 Qt6::Network（kio 未发布平台映射方案）

## 错误特征

- `find_package(KF6 ... COMPONENTS KIO)` → `Could NOT find KF6 (missing: KIO)`
- `#include <KIO/TransferJob>` → `fatal error: 'KIO/TransferJob' file not found`
- 直连替换后：`static assertion failed: The slot requires more arguments than the signal provides`
- 异步路径运行期：reply 悬空崩溃 / 段错误（栈上 manager 析构）

## 根因

KDE Gear/KF6 库普遍依赖 KIO 做网络传输，ohpcd 制品仓未发布 kio
（连带 kcmutils/solid 均缺）。但多数库只用 KIO 的纯 HTTP 子集
（get/http_post/TransferJob::data），该子集与 KIO 平台机制无关，
Qt6::Network（qtbase 自带）可完全等价。替换时三个确定性陷阱：

1. **信号槽 arity**：`KJob::result` 携带 job 指针，`QNetworkReply::finished`
   零参——带参槽直连触发 Qt 的
   `static_assert(ArgumentCount >= ArgumentCount)` 编译失败。解法：槽改
   零参 + `qobject_cast<QNetworkReply*>(sender())`。
2. **manager 生命周期**：`QNetworkAccessManager` 栈对象在创建 reply 的
   函数返回后析构，异步 reply 成悬空指针。解法：
   `new QNetworkAccessManager(this)`（QObject 父子链）。
3. **同步等待**：`KJob::exec()` 无 Qt 等价物。解法：
   `QEventLoop` + `connect(reply, &QNetworkReply::finished, &loop, &QEventLoop::quit)`
   + `loop.exec()`（先查 `isFinished()` 防已完成的死等）。

## 解法（映射表）

| upstream (KIO) | replacement (Qt6::Network) |
|---|---|
| `KIO::get(url, NoReload, HideProgressInfo)` | `nam->get(QNetworkRequest(url))` |
| `KIO::http_post(url, data, HideProgressInfo)` | `nam->post(request, body)` |
| `addMetaData("content-type", ...)` | `request.setHeader(ContentTypeHeader, ...)` |
| `addMetaData("customHTTPHeader", hdr)` | `request.setRawHeader(...)` 逐头 |
| `TransferJob::data` 分块信号 → slotData 累积 | 删除 slotData，finished 后 `readAll()` 一次取全 |
| `KJob::result` → slotResult(KJob*) | `QNetworkReply::finished` → slotResult() + sender() 取回 |
| `job->exec()` 同步 | QEventLoop + finished/quit + exec |
| `job->error()` | `job->error() != QNetworkReply::NoError` |

CMake 侧：`find_package(KF6 ... KIO)` 从 REQUIRED 组件里移除，
`target_link_libraries` 的 `KF6::KIOCore` 换 `Qt6::Network`（qtbase
Network 组件）。

## 降级方案（超出纯 HTTP 子集时）

- KCM 设置面板类子模块（还依赖 KCMUtils/Solid）：option 化 +
  BUILD_KCM=OFF 整块禁用（libkcddb kcmcddb 先例）
- 核心功能依赖 KIO ioslave 机制：按 R36 先适配发布 kio，或
  env_unsupported 止损

## 关联陷阱（同场景常并发）

- **KCoreAddons 隐藏依赖**：上游靠 KIO 传递引入 KCoreAddons
  （KStringHandler 等），去掉 KIO 后需显式
  `find_package(KF6 COMPONENTS CoreAddons)` + `KF6::CoreAddons`
  （PRIVATE）。注意 FindKF6 组件名 `CoreAddons` ↔ target `KF6::CoreAddons`
  （不是 KF6KCoreAddons/KF6::KCoreAddons）。
- **kconfig 相对 NEEDED**：链接 KF6::ConfigGui 时 kconfig 包的
  libKF6ConfigGui.so 带 `../../bin/libKF6ConfigCore.so` 相对 DT_NEEDED，
  测试运行需 `<exe-dir>/../../bin` 软链 workaround（kconfig 6.26.0
  先例 `_prepare_ctest_runtime_links`）。

## 重写传输代码的零外网验证方案（AI review 实战采纳）

替换完成后"传输层在 CI 零执行"是验证盲区（网络类测试全豁免时）。
闭合方案：test_package 起 QTcpServer 监听 127.0.0.1 模拟协议端点，
用公开 API 驱动完整传输路径断言三态 + 捕获出站请求核验协议格式：

```
Success:      应答 "200 rock <discid>"  → 断言 Success + 出站 CGI 参数
ServerError:  HTTP 500 状态行           → 断言 ServerError（状态码映射）
NoRecordFound: 应答 "202 ..."           → 断言 NoRecordFound
submit:       应答 "320 ..."            → 断言 POST 路径 + 逐头 setRawHeader + Content-Type
```

libkcddb PR #9143 实证：该 loopback 测试随 conan create 门禁执行，
AI review 的 Medium 级"传输层零运行时覆盖"意见由此闭合（复审"未发现问题"）。

## 实证

- libkcddb 26.04.3（KDE Gear，平台任务 #6853，audiocd #3888 依赖前置）：
  7 文件替换，conan create 上游离线测试 2/2（cdinfotest/cachetest），
  test_package 33 断言（含 loopback 传输/submit 覆盖）全过，四轮 CI 绿
  （#42915/#42935/#42946/#42955），AI review 复审清零。
  补丁：archives/l/libkcddb/26.04.3/patches/0001-ohos-adaptation.patch
  测试：archives/l/libkcddb/26.04.3/test_package/test_package.cpp

## 红线

- 公开 API（Lookup/Submit/Sites 类签名）不得改变——只换内部传输
- 异步路径禁止栈上 QNetworkAccessManager
- 槽签名必须与 QNetworkReply::finished 的零参匹配
