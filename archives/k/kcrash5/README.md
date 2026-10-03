# kcrash5

KDE Frameworks 5 崩溃处理库（平台包名 `kcrash5` = 上游 KDE `kcrash`，版本串一致）。

- 上游：<https://invent.kde.org/frameworks/kcrash>（KF5 Attic 冻结分支）
- 版本：5.116.0（KDE Frameworks 5.116.0 系列）
- 构建系统：CMake（ECM + KDEFrameworkCompilerSettings）
- 产物：`libKF5Crash.so` / `KF5::Crash`、`KF5CrashConfig.cmake`、`KCrash` 公开头文件
- 能力：SIGSEGV/SIGBUS/SIGFPE/SIGILL/SIGABRT 信号处置、DrKonqi 崩溃对话框对接、
  紧急保存回调（`setEmergencySaveFunction`）、崩溃后 exec 自重启（`KCrash::AutoRestart`）
- 源码布局：`archives/k/kcrash5/<版本>/`（conanfile.py / conandata.yml / manifest.yaml /
  notes.md / patches/ / test_package/）
