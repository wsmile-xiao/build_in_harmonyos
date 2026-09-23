# E543 — qmake 模块 .pri 路径重写正则漏 .cache/conan2 形态导致 QML 插件被静默跳过

## 错误特征
qmake 阶段输出大量告警，但退出码为 0：

```
Cannot read /<path>/.cache/conan2/p/b/qt5-q<hash>/b/mkspecs/modules-inst/qt_lib_qml.pri: No such file or directory
Cannot read /<path>/.cache/conan2/p/b/qt5-q<hash>/b/mkspecs/modules-inst/qt_lib_quick.pri: No such file or directory
Cannot read /<path>/.cache/conan2/p/b/qt5-q<hash>/b/mkspecs/modules-inst/qt_lib_qmlmodels.pri: No such file or directory
```

make 正常结束、构建"看起来成功"，但最终产物缺少 QML 插件 `libqtchartsqml2.so`，包内无 `qml/` 目录。

## 触发条件
- 构建系统: qmake（Qt5 子模块）
- 阶段: configure（qmake 解析 .pro）
- 前提: 依赖上游 qt5-qtdeclarative 包，且 conan home 位于 `~/.cache/conan2`

## 根因分析
Conan 配方在 `_fix_qtbase_paths()` 中合并上游 qt5-qtdeclarative 包的 `mkspecs/modules*.pri` 时，需把其中记录的"构建时旧目录"重写为当前包路径。

原正则只覆盖一种形态：

```python
r"(/[^\s]*/\.conan2/p/b/qt5-q[0-9a-f]+/b)"
```

而当 conan home 被配置到 `~/.cache/conan2` 时，`.pri` 内记录的是 `.cache/conan2/p/b/...` 形态，正则匹配不到 → 旧路径残留 → qmake 读不到 QtQuick 模块描述 → `qtHaveModule(quick)` 判为 false → `src/src.pro` 中的条件子目录被静默跳过：

```qmake
qtHaveModule(quick): SUBDIRS += chartsqml2
```

**关键点**：qmake 对读不到的 `.pri` 只告警不报错，这是"静默失败"的根源。

## 解决方案

### 推荐方案
把重写正则统一为宽版，同时覆盖两种 conan home 形态，并提取为类级常量供所有调用点复用：

```python
_BUILD_DIR_PATTERN = re.compile(
    r"(/[^\s]*/(?:\.cache/)?\.?conan2/p/b/qt5-q[0-9a-f]+/b)"
)
```

配方内所有 `.pri` / `.prl` / `.pc` / cmake config 的路径重写点必须共用同一常量，避免只修一处。

### 禁止做法
- ❌ 只修改单个调用点的正则，留下其他调用点的窄版正则
- ❌ 硬编码 `.conan2` 或 `.cache/conan2` 任一形态
- ❌ 仅凭 make 退出码 0 判定构建成功

## 验证
```bash
# 1) qmake 日志中不再出现 mkspecs 读取告警
grep -c "Cannot read .*mkspecs/modules-inst" build.log   # 期望 0

# 2) 构建日志出现 chartsqml2 子目录
grep "Entering directory.*src/chartsqml2" build.log

# 3) 包内 QML 插件齐全
P=$(conan cache path "qt5-qtcharts/5.15.2:*" | tail -1)
ls $P/qml/QtCharts/libqtchartsqml2.so $P/qml/QtCharts/qmldir
```

## 关联条目
- 相关: E544
- 原则: R32, W3
