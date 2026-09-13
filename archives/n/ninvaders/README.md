# nInvaders

nInvaders 是一个基于 ncurses 的经典太空侵略者终端游戏，纯 C 编写，使用普通
Makefile 构建，仅依赖 ncurses（宽字符版，Conan 依赖 ncurses/6.4）。

## 构建

```bash
make
```

产物为可执行文件 `nInvaders`，安装到 `bin/`。

## 使用

```bash
nInvaders [-l skill] [-gpl]
```

- `-l x`：设置技能等级（0=噩梦，9=简单）
- `-gpl`：打印 GPL 许可证文本
- 无 `--version` 参数；未知选项打印版本+用法后退出码 1（上游 CLI 契约）

## 版本

- 0.1.1（本仓库适配版本）
