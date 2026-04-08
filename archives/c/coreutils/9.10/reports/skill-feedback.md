# coreutils 9.10 — SKILL 反馈

## F001: make check 在 gnulib-tests 阶段卡死
- 类别: 流程缺失
- 严重: 🟡
- 场景: make check 执行 ~23 分钟后在 gnulib-tests 阶段卡死
- 症状: CPU 0%, 无活跃子进程, FDSize=0
- 可能原因: gnulib-tests 中某测试 fork 子进程后等待 pipe/信号，子进程因 syscall 缺失异常终止，父进程永远阻塞
- 建议: 考虑对 make check 设置超时机制，或分阶段运行 tests/ 和 gnulib-tests/

## F002: refresh-patch.sh 因 /tmp symlink 权限失败
- 类别: 脚本问题
- 严重: 🟡
- 场景: finish-build.sh 内部调用 refresh-patch.sh --auto 时失败
- 错误: ln: failed to create symbolic link '/storage/Users/currentUser/tmp/.patch-work-coreutils/orig': Permission denied
- 原因: HMDFS 文件系统在 /tmp 下不允许创建符号链接
- 建议: patch 工作目录改用 $HOME/tmp 或 $TMPDIR 替代 /tmp

## F003: package.sh 复制了非 coreutils 二进制
- 类别: 流程缺陷
- 严重: 🟢
- 场景: package.sh 从 TEST_PREFIX 复制时，TEST_PREFIX 目录可能包含之前安装的其他软件的二进制
- 现象: 质量门禁 G1 检测到 pkg-config, sed, man 等 non-coreutils 文件
- 影响: 打包产物可能包含无关文件
- 建议: package.sh 应仅复制当前软件产生的文件，或提供白名单机制
