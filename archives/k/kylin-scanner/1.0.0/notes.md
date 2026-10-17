# kylin-scanner/1.0.0 备注

## 包描述
kylin-scanner 是麒麟桌面环境的扫描仪图形前端，基于 Qt5 + SANE 构建。
通过 SANE 后端驱动完成扫描仪设备发现、参数配置、图像采集与保存，
底层图像增强依赖 leptonica + tesseract + opencv。

## 系统级构建阻碍
上游原生构建仅面向 x86_64 Linux，在 OHOS arm64 上存在以下阻碍：
1. **架构不匹配**：硬编码 x86_64 库路径 `/usr/lib/x86_64-linux-gnu/`
2. **pkg-config 依赖**：使用 `link_pkgconfig` 自动探测 SANE/Leptonica/Tesseract，OHOS 交叉编译环境不可用
3. **安装路径硬编码**：桌面文件/图标/翻译安装到 `/usr/share`，Conan 无法管理
4. **/tmp 只读**：main.cpp 中 QLockFile 硬编码 `/tmp/kylin-scanner.lock`，OHOS 上 /tmp 只读导致 tryLock 失败，程序立即退出

## 适配补丁说明
- `0001-fix-pro-deps-and-install-paths.patch`：移除 pkg-config 和硬编码 x86 路径，移除 /usr 安装目标（Conan 管理打包）
- `0002-make-lockfile-path-configurable.patch`：QLockFile 路径支持 `KYLIN_SCANNER_LOCK_FILE` 环境变量覆盖（默认 `/tmp/kylin-scanner.lock`），解决 OHOS /tmp 只读问题

## 上游测试结论
上游仓库无 tests/ 目录、无 ctest/pytest 注册项，工程内未发现任何自动化测试代码。

## 消费者测试用例说明
由于上游无自动化测试，test_package 提供 2 项验证：

1. **冒烟测试**：实跑被测 GUI 二进制 kylin-scanner（QT_QPA_PLATFORM=offscreen），验证二进制可加载全部依赖库（Qt5/glib/opencv/leptonica/tesseract/sane/libxml2）并完成 Qt 初始化
   - 断言：二进制可执行且正常退出（退出码 0）
   - 计数：1 项

2. **消费者用例（端到端运行验证）**：启动 kylin-scanner 应用并验证其在 offscreen 模式下稳定运行 10s 无崩溃，验证资源文件完整性（翻译/图标/桌面文件），随后正常终止应用
   - 断言：资源文件完整 + 应用启动成功 + 稳定运行 10s 无崩溃 + 正常终止
   - 计数：3 项（资源完整性 + 启动 + 稳定运行）

**总计**：2 项测试，4 项断言

### 关键 OHOS 适配细节
- **/tmp 只读**：consumer_test.sh 设置 `KYLIN_SCANNER_LOCK_FILE` 环境变量指向可写目录（`$HOME/tmp/kylin-scanner-lock`），使程序能正常加锁并进入 Qt 事件循环
- **HOME 可写**：冒烟测试设置 `HOME=$HOME/tmp`（OHOS /tmp 只读）
- **shebang**：consumer_test.sh 使用 `#!/bin/sh`（OHOS 上 /bin/bash 不存在）
- **test_type**：test_package/conanfile.py 不设置 `test_type = "explicit"`，确保 conan create 自动运行 test_package

## 编译产物说明
- `bin/kylin-scanner`：主程序（Qt5 GUI + SANE 扫描）
- `lib/`：空（kylin-scanner 为纯应用程序，不产出共享库）
- `res/`：翻译文件、图标、桌面文件
