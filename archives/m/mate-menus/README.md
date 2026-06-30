# mate-menus

## 简介
mate-menus 是 MATE 桌面环境的菜单实现库，提供菜单布局和桌面目录配置功能。

## OHOS 适配
- **构建系统**: autotools，需要补丁 config.guess/config.sub
- **平台识别**: GNU config.guess（2014年版）不包含 HarmonyOS 检测分支
- **文件系统限制**: HMDFS 上 configure 的 umask 077 导致临时文件创建失败
- **解决方案**:
  1. 使用 `patch-autotools-ohos.pl` 补丁 HarmonyOS 系统识别
  2. `sed -i 's/umask 077/umask 022/g' configure` 修改权限设置
  3. 手动添加 `linux-ohos*) ;;` 到 config.sub

### 与 Linux 的差异
- Linux 下可直接 configure + make
- HarmonyOS 需要补丁平台识别和权限设置

### 已知问题
- 测试工具 mate-menu-spec-test 因 musl/glibc 兼容性问题无法编译
- glib 预编译包依赖 glibc FORTIFY_SOURCE（musl 缺少 __fd_chk）

## 排除与替代
- 测试工具未编译，但不影响核心库功能
- 核心库 libmate-menu 可正常使用

## 依赖
- glib >= 2.50.0（提供 gio-unix-2.0）
- gettext（系统自带）

## 功能验证
```bash
# 检查库文件
ls -la $PREFIX/lib/libmate-menu.so*

# pkg-config 验证
pkg-config --modversion libmate-menu
```

## 参考
- 官网: https://mate-desktop.org
- 源码: https://pub.mate-desktop.org/releases/