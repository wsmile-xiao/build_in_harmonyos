# DRAFT-10491-sent-1: libXft 把 libx11 硬 pin 在旧血脉上，与已审的 libx11/6.4.0 口径互斥

## 症状

给一个需要 `libXft` 的 X11 客户端写配方时，若照抄已合并 X 客户端（如 xeyes）的依赖口径
`libx11/6.4.0 + libxext/6.4.0`，依赖解析直接失败，报的是**版本冲突**而不是编译错误。

## 根因

本仓同一个库存在**两条并行发布的血脉**：

| 血脉 | 组成 | 出处 |
|---|---|---|
| 旧（预编译栈配套） | `libx11/1.8.10`、`libx11/1.8.13` + `libxext/1.3.x` | 早期预编译栈时代的产物 |
| 新（自构建族） | `libx11/6.4.0` + `libxext/6.4.0` | xeyes 配方注释记载 CI #28097 起主配方改用它 |

关键在中间层：`libxft` 自己的配方把 libx11 **写死在旧血脉**上。实测读已发布二进制
的依赖闭包（`conan graph explain --requires=libxft/2.3.9 -pr:h <OHOS profile> -r ohpcd`）：

```
libxft/2.3.9#1b44a37fe776be92368a5d393266c87a:e5cf91366c9b091a65c988a829f1d50600d97fbe
  requires: fontconfig/2.18.Z, freetype/2.14.Z, libx11/1.8.Z,
            libxrender/0.9.Z, xorgproto/2025.1
  settings: OHOS, armv8, Release, clang, 17, libc++, 15, 6.0 ; options: shared=True
```

`libxft/2.3.8` 的 pin 完全相同。于是 `libx11/1.8.Z` 与 `libx11/6.4.0` 版本区间不相交
⇒ **只要配方 require 了 libXft，就不能同时采用 6.4.0 口径**。

## 最小复现

```python
def requirements(self):
    self.requires("libxft/2.3.9")
    self.requires("libx11/6.4.0")   # xeyes 口径
```
`conan graph info` / `conan create` 在解析阶段即因 libx11 版本区间冲突失败。

## 已试过的失败方案

1. **混用两族**（上面的最小复现）⇒ 解析期版本冲突，进不到编译。
2. **靠 override 强拉**（`--force`/`conf`）⇒ 即便解析过去，产物与已审口径不一致，
   审查面风险高于收益；且 libXft 的 .so 实际链的是 1.8 的符号版本。

## 最终方案

需要 libXft 的包，**整条栈跟随 libXft 自身的 pin 走**，不要跨族拼接：

- 首选只声明 `self.requires("libxft/<ver>")`，让 libx11 / libxrender / freetype /
  fontconfig / xorgproto 由它**传递解析**带出，避免手填精确版本造成区间打架；
- 若必须显式声明（例如要直接吃 Xlib 的头），把 libx11 也 pin 到同一 `1.8.Z` 区间；
- 选型前先跑一次
  `conan graph explain --requires=libxft/<ver> -pr:h <OHOS profile> -r ohpcd`
  读它的 `requires:` 行，**以已发布二进制的实际依赖为准，不要照抄别的配方**。

## 适用边界

- **适用**：所有经由 `libXft` 取字体的 X11 客户端/工具（suckless 家族
  `dmenu`/`st`/`sent`/`lsx`/`scroll`/`sprop`/`sselp`/`tabbed` 以及任何
  `-lXft` 程序）——本仓这批包在排期里成批存在，是高频坑。
- **不适用**：
  - 只用 `libX11`/`libXext`、不经 libXft 的包（可以继续用 6.4.0 自构建族）；
  - 纯字体库包（freetype/fontconfig 自身不涉及此冲突）。
- 附带一条同类判据（同一次实测发现）：**这些包的已发布二进制是
  `options: shared=True` 而 `gdbm` 一类是 `shared=False`**（各包
  `default_options` 不同）⇒ **conan profile 的 `[options]` 里不要写死
  `shared=*`**，否则会把整片 X 栈误判成"缺二进制"。
