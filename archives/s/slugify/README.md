# slugify

**把文件名与目录名转换成适合 Web 使用的格式的 Bash 命令**

## 简介

slugify 将参数给出的文件/目录改名：默认转小写、空格替换为下划线；
`-d` 改用连字符，`-c` 合并连续空格，`-a` 去掉紧邻连字符的空格，
`-t`/`-u` 把已有的连字符/下划线当作空格处理，`-i` 保留大小写，`-n` 预演不改动。

```
slugify -v "My file.txt"                # rename: My file.txt -> my_file.txt
slugify -vdc "My  dashed  file.txt"     # rename: ... -> my-dashed-file.txt
```

## 适配要点

- 纯 bash 脚本（`[[ ]]`、`function`、`==`、getopts），无需编译；解释器由 `bash/5.3` 提供
- 鸿蒙 PC 用户存储（HMDFS）大小写不敏感：上游 1.0.1 在这里把 `README.md -> readme.md`
  这类仅大小写不同的改名一律报 `conflict`，补丁 `0001-slugify.patch` 让其经临时名完成改名，
  真正的冲突仍然拒绝
- 鸿蒙上以 `bash "$(command -v slugify)" ...` 调用（用户存储拒绝直接 exec `#!` 脚本，且无 `/usr/bin/env`）

## 编译状态

| 版本 | 状态 | 构建系统 | 日期 |
|------|------|----------|------|
| 1.0.1 | built | none | 2026-09-28 |

## 许可证

MIT（上游在 v1.0.1 之后的提交 b2a371b 补入 LICENSE，配方固定到该提交下载）
