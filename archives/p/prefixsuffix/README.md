# prefixsuffix

## 简介

prefixsuffix 是 GNOME 桌面环境下的 GUI 批量文件重命名工具，使用 gtkmm3（C++ GTK 绑定）
开发。用户可以通过添加前缀或后缀的方式批量重命名文件，支持目录递归处理。

- **官方网站**: https://github.com/murraycu/prefixsuffix
- **上游源码**: https://download.gnome.org/sources/prefixsuffix/
- **License**: GPL-2.0-or-later
- **Homebrew formula**: https://github.com/Homebrew/homebrew-core/blob/master/Formula/p/prefixsuffix.rb

## 适配版本

- **版本**: homebrew（对应上游 0.6.9）
- **状态**: 无法适配

## 编译方式（OHOS）

上游使用 Autotools 构建系统，prefixsuffix 是 C++ GUI 应用程序。Homebrew formula
使用标准的 `./configure` + `make install` 流程。

CI #3074 已确认编译器、交叉编译参数和 `CONFIG_SHELL` 均正常，配置阶段失败于：

```text
configure: error: Package requirements (gtkmm-3.0) were not met:
No package 'gtkmm-3.0' found
```

上游不提供禁用 GUI 或 gtkmm 的构建选项。当前仓库和 OHOS CI 环境缺少
gtkmm3 所需的完整 GTK3 C++ 依赖链，因此无法完成适配。

详见 `homebrew/notes.md`。

## 依赖

### 构建期
- intltool（国际化工具，需 perl + XML::Parser）
- pkg-config（依赖检测）
- gettext

### 缺失依赖
- gtkmm-3.0
- glibmm-2.4
- atkmm-1.6
- cairomm-1.0
- pangomm-1.4

完整失败记录详见 `homebrew/notes.md`。
