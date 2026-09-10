# statusnotifieritem 6.26.0 — conan create 验证报告

- 日期: 2026-09-07
- 环境: ohos-aarch64 profile (clang 15, libc++, armv8, os=OHOS 6.0)
- 命令: `conan create archives/s/statusnotifieritem/6.26.0 --user=ohpcd --channel=stable -pr:h=~/.conan2/profiles/ohos-aarch64 -pr:b=~/.conan2/profiles/ohos-aarch64 --build=missing`
- 日志 SHA-256: `341cb6bade2d1868fda85c92a1f844767742b50c339d21aa048ab1a45f19aa56`

## 结果

- **exit 0** — Package `statusnotifieritem/6.26.0@ohpcd/stable:b8d7c06d07651175e501ee85c5977b7812677caf` created
- 0 个 ERROR

## 产物

| 产物 | 说明 |
|------|------|
| libKF6StatusNotifierItem.so | 主库（含 DBus 适配器 + libdbusmenu-qt，USE_DBUS=ON） |
| KF6StatusNotifierItemConfig.cmake / ConfigVersion / Targets(-release) | CMake 消费配置 4 个 |
| kstatusnotifieritem.h / kstatusnotifieritem_export.h / kstatusnotifieritem_version.h | 公共头文件 3 个 |
| kf6_org.kde.StatusNotifierItem.xml / kf6_org.kde.StatusNotifierWatcher.xml | DBus 接口声明 2 个 |
| kstatusnotifieritem.categories | 日志分类 |

## 测试

1. **上游测试**（tests/kstatusnotifieritemtest.cpp，唯一测试源）：
   - 上游无 add_test 注册（任何平台 ctest 均 0 项）——如实记录
   - demo 编译 100%（Built target kstatusnotifieritemtest）
   - demo offscreen 执行：**到达 Qt 事件循环（25s 超时被杀）= PASS**
     （动态链接 libKF6StatusNotifierItem + Qt6Widgets + Qt6DBus + QApplication 构造成功）
2. **test_package**：`100% tests passed, 0 tests failed out of 1`
   - ctest: test_kstatusnotifieritem Passed (0.06 sec)
   - 直接运行: `PASS: KStatusNotifierItem API round-trip OK (title/category/status/toolTip)`

## 依赖（全部缓存命中，零源码重编）

qtbase/6.11.1.1 (override) / kwindowsystem/6.18.0 / ecm/6.26.0 (tool) /
qt6linguisttools/6.11.1 (tool)
