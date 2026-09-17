# libzpaq

**ZPAQ 归档格式 level 0 参考实现**（ZPAQ 开放压缩标准的实验性预发布版，Matt Mahoney / Ocarina Networks，2009-02-15）

zpaq 是可配置的文件压缩器与归档器，目标是以开放格式实现高压缩比。
0.01 是 ZPAQ 标准 0.29 草案（level 0）的参考实现——属于实验性格式，
与后续 level 1 标准不兼容。

## 用法

```bash
# 压缩（需要模型配置文件）
zpaq cmin.cfg archive.zpaq files...

# 追加
zpaq amin.cfg archive.zpaq files...

# 列表
zpaq l archive.zpaq

# 解压（不自动创建目录）
zpaq x archive.zpaq
```

| 命令 | 说明 |
|------|------|
| `c<config>` | 创建归档（覆盖） |
| `a<config>` | 创建/追加 |
| `x` | 解压（按存储名或改名） |
| `l` / `v` | 列表 / 详细列表 |
| `t` | 调试用解压（无后处理） |
| `h<config>` | 编译并单步运行 HCOMP |
| `p<config>` | 运行 PCOMP 后处理 |

模型配置：`min.cfg`（order-4 快速模型，4MB 内存）与 `max.cfg`
（93MB 内存高压缩比）随包安装在 `share/libzpaq/`。

## 构建

- 构建系统：无（上游单文件无构建系统；本包按上游文档
  `g++ -O3 -DNDEBUG zpaq.cpp -o zpaq` 手动编译）
- 版本：0.01（2009-02-15 发布）
- 许可证：GPL-3.0-or-later
- 源码：https://github.com/zpaq/zpaq（tag 0.01）
- 零依赖：仅 C/C++ 标准库

## OHOS 适配

- 零补丁：源码纯 ISO C++，无平台敏感 API
- `-static-libstdc++`：静态烘焙 libc++（SDK libc++_shared.so 是
  链接器脚本，musl 加载器无法运行时解析），二进制仅依赖 libc.so
