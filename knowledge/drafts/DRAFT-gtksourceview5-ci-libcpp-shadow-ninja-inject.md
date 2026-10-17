# E6408：CI Worker 沙箱 libc++ 遮蔽+NINJA 注入

## 错误特征

```
Error relocating cmake: _ZTINSt4__n1...   # 工具链二进制启动即挂
Program ninja not found or not executable  # meson compile 找不到 ninja
```

## 根因

1. **el1 bundle libc++ 遮蔽**：CI Worker 沙箱自带 libc++_shared.so 遮蔽系统真 so——工具链二进制（cmake/meson）符号缺失
2. **NINJA 路径**：conanbuildenv 的 PATH 无 ninja 可执行位

## 解法

1. 测试环境 LD_LIBRARY_PATH：/system/lib64 前置+全依赖 lib（kysdk E6405 同族范式）
2. conanbuildenv 注入 NINJA=/usr/bin/ninja

## 实证

PR #12817 gtksourceview5 5.22.0：修复后 CI passed+180 语言 ALL PASS。
