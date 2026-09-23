# E-draft：meson 消费 GLib/Pango 栈的 .pc 传递链断裂（隐形传递静态依赖）

## 问题场景

meson 系项目依赖 GLib/Pango 栈（如 `dependency('pangoft2')`）时，conan 构建中 pkg-config 解析失败：

```
Package 'libpcre2-8', required by 'glib-2.0', not found
ERROR: Dependency lookup for pangoft2 with method 'pkg-config' failed
```

## 根因

- glib-2.0.pc 的 `Requires.private` 引用 libpcre2-8；gobject-2.0.pc 引用 libffi
- pcre2/libffi 在消费场景是**隐形传递静态依赖**（用户配方不直接 requires）
- PkgConfigDeps 只为**直接可见依赖图**生成 .pc，不为隐形传递依赖生成
- 拷上游 .pc 改 prefix 的 "pc-fix" 方案是死路：上游 .pc 的跨包 Requires 链引入未依赖的包，依旧断裂

## 正解（paps 9 轮实证）

1. 声明完整的**直接依赖集**（pango 场景声明 pango 包即可）
2. 信任 conan 标准流：PkgConfigDeps 为可见依赖图生成组件级 .pc，prefix 已指向真实包目录
3. MesonToolchain 默认把 pkg_config_path 指到 generators 目录——不要手动覆盖
4. 验证：`source conanbuild.sh && pkg-config --cflags --libs pangoft2`

## 弯路记录（有实证的失败路径）

| 轮次 | 尝试 | 结果 |
|---|---|---|
| 1-8 | pc-fix（拷上游 .pc + 改 prefix + 前置 PKG_CONFIG_PATH） | 全部失败——跨包 Requires 链断裂 |
| 9 | 信任 PkgConfigDeps 组件级生成 | ✅ 通过，17 项测试全绿 |

## 与已有条目的区别

- E348/E321：别名 pc 转发（pkg_config_name 不匹配）——不同问题
- E247：Libs.private 静态运行时传递——不重合
- E075：环境变量陷阱（C_INCLUDE_PATH）——不同层面

## 推广价值

所有 meson 系 GNOME/GLib 栈消费者（gnumeric/goffice/gtk 消费端等）都会踩这个坑。

## 关联

- 实证 PR：paps #8328
- Agent: 主任务
