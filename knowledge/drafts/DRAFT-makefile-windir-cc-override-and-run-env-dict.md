# DRAFT: makefile 用 ifdef WINDIR 判定 Windows 宿主——命令行 CC= 覆盖可救；conanfile 的 self.run() 不接受 dict env

- 发现于：tinymembench/0.4 适配（本机 Windows 交叉验证 + 真机 r5）
- 触发面：上游 makefile 以 `ifdef WINDIR` 区分 MinGW/Windows 的项目
  （tinymembench、一批 MinGW 风格工具），在 Windows 宿主上做本机验证
  时必遇；以及需要在 Conan build() 里改环境变量的配方

## 现象一：WINDIR 强制 CC=gcc

上游 makefile：

```make
ifdef WINDIR
	CC = gcc
endif
```

在 Windows 宿主（WINDIR 环境变量恒存在）上交叉编译时，makefile 内
`CC = gcc` 会覆盖……吗？

## 根因与解法（现象一）

GNU make 的变量优先级：**命令行变量 > makefile 内赋值**。因此

```sh
make CC="<交叉 clang 路径>" CFLAGS="" -j1
```

在 Windows 上依然生效，`ifdef WINDIR` 分支形同虚设——**无需改
makefile、无需清环境**。真机（OHOS）上无 WINDIR，更无影响。

- 误判风险：以为必须 `env.pop("WINDIR")` 之类处理——不必要；更不能
  因此给 self.run() 传环境 dict（见现象二）。
- 判别方法：`grep -n "WINDIR" Makefile`；注意 makefile 中 CC 是"编译器
  程序名"还是"完整命令串"决定覆盖串的内容（另见 simh 条目三形态表）。

## 现象二：self.run(env=dict) 直接 AssertionError

在 build() 里为清 WINDIR 写了：

```python
env = os.environ.copy()
env.pop("WINDIR", None)
self.run("make ...", env=env)
```

真机报错：

```
AssertionError: env argument to ConanFile.run() should be a list
```

Conan 2.x 的 `self.run(env=...)` 只接受 None 或 list（环境脚本列表，
如 `["conanbuild"]`），不接受普通 dict。普通的环境改写需求：

- 若变量可被命令行覆盖替代（本例 CC=）→ 直接去掉 env 参数；
- 确需改环境 → 用 `conan.tools.env.Environment`：

```python
from conan.tools.env import Environment
e = Environment()
e.unset("WINDIR")
with e.vars(self).apply():
    self.run("make ...")
```

## 验证

tinymembench/0.4：Windows 本机以 OHOS SDK clang 交叉编译（WINDIR
存在 + 命令行 CC= 覆盖）成功，0 警告；真机 r5 去掉 env=dict 后
build() 通过，r6 全绿。
