# NetHack 3.6.7 适配笔记

## 软件信息
- 名称: nethack
- 版本: 3.6.7
- 上游: https://www.nethack.org/
- 构建系统: 纯 Makefile（sys/unix/setup.sh 根据 hints 生成 Makefile）
- 产物: nethack 终端游戏 + dat 游戏数据 + recover 工具

## OHOS 适配要点
1. 自定义 hints 文件（ohos-conan）：tty + curses 窗口，链接仓库 ncurses/6.6
   （ncursesw 宽字符静态库），避免依赖系统 ncurses/tinfo
2. CFLAGS 注入依赖头文件路径，WINTTYLIB/WINCURSESLIB 注入 -lncursesw 与库路径
3. CHOWN/CHGRP 置为 true，跳过 setuid/setgid 安装逻辑（L4 安全扫描要求）
4. 上游 make install 不支持 DESTDIR 且会 rm -rf HACKDIR，配方改为手动打包：
   src/nethack + util/recover -> bin/，dat/* + sysconf -> share/nethack/

## 测试
- test_package 运行 nethack --version 验证二进制可启动并输出版本

## 依赖
- ncurses/6.6（仓库内已有适配）