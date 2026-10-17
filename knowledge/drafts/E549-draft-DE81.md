# E549 — LD_LIBRARY_PATH 段带空格导致系统库解析失败（libc++_shared.so 假性缺符号）

## 现象

conan create 的 test_package 阶段（或直接运行测试二进制）报：

```
Error relocating .../libLerc.so.4: _ZTISt12length_error: symbol not found
Error relocating .../libLerc.so.4: _ZTVN10__cxxabiv117__class_type_infoE: symbol not found
```

看似 `libc++_shared.so` 缺符号（C++ ABI typeinfo），实际是**该库根本没被加载**
——路径解析失败。

## 根因

开发机 shell 继承的 `LD_LIBRARY_PATH` 中某段含**前导/尾随空格**：

```
/system/lib64/platformsdk:/system/lib64/chipset-pub-sdk:         /system/lib64:...
                                                            ^^^^^ 空格！
```

musl ld.so 不 trim 路径段，把 `"         /system/lib64"` 当字面目录名查找 →
不存在 → 整段失效。`libc++_shared.so` 只在 `/system/lib64`，conanrun 环境
又不含系统目录 → C++ 依赖链（lerc 等）relocating 失败。

## 定位实验

```bash
# 1) 暴露损坏段
echo "$LD_LIBRARY_PATH" | tr ':' '\n' | grep -n ' '
# 2) 干净环境对照（能跑通 = 环境问题而非二进制问题）
env -i LD_LIBRARY_PATH=/system/lib64 ./lerc_probe   # OK
```

## 修复

test_package 的 `generate()` 显式注入系统库路径，不依赖外层 shell：

```python
from conan.tools.env import Environment

def generate(self):
    run_env = Environment()
    run_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
    run_env.vars(self).save_script("system_run_env")

def test(self):
    self.run("ctest --output-on-failure", env=["conanrun", "system_run_env"])
```

（与 avahi-ui 0.8 test_package 同法——GTK 栈的 C++ .so 同样需要系统 libc++。）

## 禁止

把该错误当成"libc++ 版本不匹配/缺符号"去换库、补符号——方向全错。
对照实验（env -i）两分钟就能证伪。

## 实证

libtiff 4.7.0 适配（2026-09-05）：lerc.so.4 加载报 40+ typeinfo/vtable 符号缺失；
`env -i LD_LIBRARY_PATH=/system/lib64` 下 dlopen+lerc_decode 全通过；
配方 generate() 注入后 conan create test_package 1/1 PASSED。

## 关键词

LD_LIBRARY_PATH, whitespace, libc++_shared.so, Error relocating, symbol not found, conanrun, /system/lib64, lerc
