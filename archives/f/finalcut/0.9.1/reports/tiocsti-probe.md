# HarmonyOS TIOCSTI 真机探针

- 设备：HarmonyOS 6.0 PC，aarch64
- 进程：本次 Conan/测试工作使用的 HNP 用户进程
- 对象：当前进程通过 `pty.openpty()` 创建的 pty slave
- 日期：2026-10-02

执行命令：

```bash
python3 -c 'import pty,fcntl; m,s=pty.openpty(); fcntl.ioctl(s,0x5412,bytes([120]))'
```

设备原始错误：

```text
Traceback (most recent call last):
  File "<string>", line 1, in <module>
PermissionError: [Errno 13] Permission denied
```

该探针只支持“此设备、版本、进程凭据下 TIOCSTI 输入注入被拒绝”的结论。它不证明其他 HarmonyOS 版本/凭据的行为，也不涉及 `TCFLSH` 或 `TIOCSCTTY`。
