# gnutrition — GNUtrition

GNUtrition 是一个饮食分析 GUI 程序（GPL-3.0-or-later，GNU 官方项目）。

- 版本：0.33
- 上游：https://ftp.gnu.org/gnu/gnutrition/
- 构建：Autotools（configure + make），C99，GTK3 GUI
- 依赖：gtk/3.24.43、sqlite3/3.49.1（ohpcd 制品仓）
- 产物：`bin/gnutrition` 可执行 + `share/gnutrition/food.db` 数据
- 适配要点：`GNUTRITION_DATADIR` 环境变量覆盖数据路径（详见 0.33/notes.md）

## 版本列表

| 版本 | 状态 |
|------|------|
| 0.33 | built |

## 使用

```bash
conan install gnutrition/0.33 -r=ohpcd
# 运行时数据路径：GNUTRITION_DATADIR=<prefix>/share/gnutrition gnutrition
```