# qtserialport-opensource-src

Qt5 Serial Port module — provides APIs for accessing serial ports
(QSerialPort/QSerialPortInfo, Qt 5.15.15).

## Build Notes (OHOS adaptation)

- 构建系统 qmake（上游 .pro 原生构建，`QT = core-private` 私有模块），
  依赖制品仓 `qt5-qtbase/5.15.2.2`；5.15.15 与 qtbase 5.15.2 二进制兼容。
- 上游源码零修改（无 patches）：qmake 重写 qtbase 包内 qt.conf/.pri 残留
  构建机路径后即可原生构建（qt5-qtdeclarative 先例模式）。
- 无 libudev：qt5-qtbase 构建时 libudev 为 disabled feature，串口枚举
  走 `/sys/class/tty` 回退路径（Qt 运行时日志的 udev 加载警告为预期行为）。
- `make QMAKE_STRIP=""`：OHOS loader 拒绝被 strip 的 ELF，保留符号。
- 产物：`libQt5SerialPort.so`（含 .prl/.pc/mkspecs 模块 .pri/可重定位
  Qt5SerialPortConfig.cmake）。

## 依赖

- qt5-qtbase/5.15.2.2（QtCore；无其他运行时依赖）

## 参考

- 官网：https://doc.qt.io/qt-5/qtserialport-index.html
- 源码：https://download.qt.io/archive/qt/5.15/5.15.15/submodules/
