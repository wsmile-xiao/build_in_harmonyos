# libutempter

libutempter 是一个终端多路复用器的辅助库，用于在终端会话开始和结束时更新 utmp 记录，使得终端多路复用器（如 screen、tmux）的会话能够正确显示在 `who` 和 `w` 命令的输出中。

## OHOS 适配

### 已知问题
- **updwtmp 函数缺失**: OHOS 使用 musl libc，不提供 `updwtmp()` 函数，需要添加 stub 实现
- **软链接创建限制**: HMDFS 文件系统不支持 `ln -sf` 直接覆盖，需要先 `rm -f` 再 `ln -s`

### 解决方案
- 添加 `#ifdef __OHOS__` 守卫，为 updwtmp 提供空实现
- 修改 Makefile 中的软链接创建逻辑

## 依赖

- 无外部依赖

## 功能验证

```bash
# 检查库文件
ls ~/usr/local/lib/libutempter.so*

# 查看版本（如有）
pkg-config --modversion libutempter
```

## 参考

- 官网: https://github.com/altlinux/libutempter
- 源码: https://github.com/altlinux/libutempter/archive/refs/tags/1.2.3.tar.gz