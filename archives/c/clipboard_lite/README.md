# clipboard_lite

Cross-platform clipboard management library (lightweight and fast).

- 上游: https://github.com/smasherprog/clipboard_lite (MIT)
- C++14，单库 libclipboard_lite.a + 公开头 include/Clipboard_Lite.h
- Linux/OHOS 后端基于 X11 (libx11 @6.4.0) + Xfixes (libxfixes @6.1.0) +
  XTest (libxtst @6.1.0)，协议头来自 xorgproto/2025.1
- HarmonyOS PC (aarch64, os=OHOS) 交叉编译适配，Conan 配方见 3.4/

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 3.4  | built | 完整适配：conan-verify G0-G4 通过、W3 本地 CI 通过、上游测试台账 + 鸿蒙专项 T1-T4 + 消费者用例 |