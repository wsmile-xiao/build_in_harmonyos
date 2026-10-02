# qmlrunner 1.0.2 测试报告

> **项目**: qmlrunner 1.0.2（Qt5 QML 应用启动器）
> **测试日期**: 2026-10-01
> **测试环境**: HarmonyOS HongMeng Kernel 1.12.0 aarch64（HAD-W32 设备，clang 15.0.4，Conan 2.29.1 OHOS-adapted）
> **测试类型**: 消费者语义测试（真实 QML 窗口加载 + CLI 契约负例对照）

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游自动化测试（发布包内） | 0 | —（无测试套件，说明见下） |
| 消费者测试断言 | 13 | 100% |
| 通过 (PASS) | 13 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**核心功能通过率**: ✅ **100%（13/13 断言）**

> 上游测试说明：qmlrunner 1.0.2 发布包仅含 `.gitignore`、`LICENSE`、`README.md`、
> `qmlrunner.pro`、`src/main.cpp` 五个文件；无 tests/ 目录、无 CTest/pytest 注册、
> qmake 工程无 check target（`grep -nE "check|test" qmlrunner.pro` 无输出），
> 上游测试用例数为 0，未能执行，不计入通过率分母（详见 `test_package/MANIFEST.yml`
> 与 `notes.md` 的 R51 清点）。

---

## 二、测试结论

### 2.1 总体评价

✅ **qmlrunner 1.0.2 在 OHOS/aarch64 上编译、打包与核心功能（QML 应用加载）全部通过验证。**

- 正例在 `QT_QPA_PLATFORM=offscreen` + `QT_QUICK_BACKEND=software` 下真实加载
  QtQuick 窗口应用（`import QtQuick 2.0` / `QtQuick.Window 2.0`），Timer 触发
  `Qt.quit()` 后事件循环正常退出（rc=0），并验证翻译回退路径（"Translation not found"）。
- 4 个负例对照覆盖 CLI 参数解析与错误路径，退出码与上游 `main.cpp` 的返回值约定
  完全一致（-1/-2/-3 → 255/254/253）。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 上游无自动化测试 | 需自行补全消费者测试（本报告） | 🟢 |
| OHOS 无 X11/Wayland 平台插件运行时保证 | 有显示交互场景需 offscreen/minimal/vnc 插件 | 🟢 |

### 2.3 可用功能清单

```
✅ 按约定加载 PREFIX/appname/qml/appname.qml 作为窗口应用
✅ -P prefix（默认 /usr/share）、-path 附加 QML 导入路径（可重复）
✅ -scale / -noscale（AA_EnableHighDpiScaling / AA_DisableHighDpiScaling）
✅ 翻译加载与回退（PREFIX/appname/translations/appname-LOCALE.qm）
✅ 回退图标路径（PREFIX/appname/icons，Qt >= 5.11）
✅ `--` 之后参数透传给应用；CLI 错误路径（重复应用名/未知选项/应用缺失）退出码契约
```

### 2.4 已知限制

1. 上游无自动化测试套件，`make check` 不存在；消费者测试为本仓库补全。
2. OHOS PC 无 X11/Wayland QPA 运行时保证；本测试以 offscreen + 软件渲染验证
   功能正确性（QML 加载与事件循环），未做真实窗口显示验证。
3. 运行时依赖 Qt5 库、平台插件与 QML 模块路径（conanrun 环境自动提供）。

---

## 三、测试详情

### 3.1 正例（2 用例 / 5 断言）

| 测试项 | 命令 | 断言 | 结果 |
|--------|------|------|------|
| QML 窗口加载 | `qmlrunner -P <root> myapp` | rc=0；输出含 `Current locale:`；输出含 `Translation not found` | ✅ PASS |
| 参数组合 | `qmlrunner -noscale -path <qml_dir> -P <root> myapp` | rc=0；输出含 `Current locale:` | ✅ PASS |

测试 QML（`test_package/testapp/qml/myapp.qml`）：

```qml
import QtQuick 2.0
import QtQuick.Window 2.0

Window {
    visible: true
    width: 320
    height: 200
    title: "qmlrunner consumer test"

    Timer {
        interval: 300
        running: true
        repeat: false
        onTriggered: Qt.quit()
    }
}
```

### 3.2 负例（4 用例 / 8 断言）

| 测试项 | 命令 | 期望 | 结果 |
|--------|------|------|------|
| 无应用名 | `qmlrunner` | rc=255；stderr 含 `Usage: qmlrunner` | ✅ PASS |
| 未知选项 | `qmlrunner --bogus myapp` | rc=253；含 `Unknown option: --bogus` | ✅ PASS |
| 重复应用名 | `qmlrunner app-one app-two` | rc=254；含 `Application name specified multiple times` | ✅ PASS |
| 应用缺失 | `qmlrunner -P <root>/absent myapp` | rc=254；含 `Cannot find` | ✅ PASS |

### 3.3 证据

- `conan create`（干净源码构建 + 自动 test_package）日志：
  `reports/conan-create.log`（本次 W3/CI 复现；原始日志见平台 CI build 号）——
  末段输出 `ALL PASS (2 positive + 4 negative cases)`。
- `conan-verify` 门禁报告：G0/G1/G2/G3 PASS，G4/L2/L4/L5 跳过（工具未从日志解析到包 ID，
  非失败；见 `reports/conan-verify-report.md`）。
- 安装产物与链接产物逐字节一致（签名保留，可直接执行）：
  `md5sum = 9f1f7ed09c002eac1d1644ddf5f8a698`。

### 3.4 复现命令

```bash
python3 scripts/ohc-run.py conan-verify qmlrunner 1.0.2 --profile ohos-aarch64-device
# 或直接：
conan create archives/q/qmlrunner/1.0.2 --user=ohpcd --channel=stable \
  -pr:h=ohos-aarch64-device -pr:b=ohos-aarch64-device --build=missing
```
