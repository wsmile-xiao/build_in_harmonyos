# dbus-glib 0.114.1 — OHOS aarch64 依赖对齐版本

> 本文件记录 **0.114.1** 这个新增点号版本相对 **0.114** 的差异、根因与实测证据。
> 上游源码、补丁集与 0.114 完全一致（同一 tarball，sha256 见 manifest.yaml）；
> 平台背景、E236/E216 方案说明、上游用例清单见 `test_package/MANIFEST.yml`
> 与 0.114 版本目录下的 notes.md。

---

## 0. 为什么新增 0.114.1，而不是原地改 0.114

### 0.1 冲突链（实测错误串）

`gtk/3.24.4x` 精确 pin `glib/2.84.0.1`，而 `dbus-glib/0.114` 配方 pin `glib/2.88.0`。
conan 2 拒绝同一张依赖图里出现两个 glib：

```
ERROR: Version conflict: Conflict between glib/2.88.0 and glib/2.84.0.1 in the graph.
Conflict originates from dbus-glib/0.114
```

首例现场是 `libcryptui/3.12.2`（库本体只依赖 gtk3 + dbus-glib，二者必须同图）。
全仓 6438 个配方中没有任何一个同时 require gtk 与 dbus-glib，说明这条分叉此前从未被撞上。

配套的 expat 分叉同理：`dbus/1.14.10` pin `expat/2.8.2`，GTK3 链（fontconfig）pin `expat/2.8.2.1`。

### 0.2 消费者侧 override 为什么不行（实测）

在消费者（如 libcryptui）里写 `override=True` 能解开图冲突，但会把 dbus-glib 的
`package_id` 从已发布的按 `glib/2.88.0` 构建的那一个改成另一个值
（实测 `c1a87fd6…` ≠ 已发布 `5073980f…`）。而 CI 只构建包本体
（`conan create … --build="${pkg_name}/*"`），不会重建依赖 →
**CI 会以「dbus-glib 二进制缺失」红灯**。

结论：对齐必须落在**依赖侧配方**里，于是新增 `0.114.1`（对齐 glib/2.84.0.1 线），
仓内先例：`dbus 1.14.10.1`、`cairo 1.18.4.1` 均以新增点号版本落地。

---

## 1. 与 0.114 的差异（全部差异；源码与补丁零改动）

| 项 | 0.114 | 0.114.1 |
| --- | --- | --- |
| glib | `2.88.0` | `2.84.0.1`（GTK3 链） |
| expat | `2.8.2` | `2.8.2.1`，**以 `override=True` 声明**（dbus 仍 pin 2.8.2） |
| zlib | `1.3.1`（显式） | 不再显式声明（glib 转共享后不是链接输入，见 §2.3） |
| pcre2 | `10.45` | `10.45`（不变） |
| dbus | `1.14.10` | `1.14.10`（不变） |
| GLIB_CPPFLAGS / GLIB_LIBS | 指向 E236 la-free 私有目录里的静态 glib | 追加**共享 glib 的 include/libdir**（glib/2.84.0.1 是 shared-only） |
| 源码 / 补丁 | tarball sha256 `c09c5c08…`，5 个补丁 | **完全一致** |

---

## 2. 根因与修法（均为实机复现后定位）

### 2.1 症状

沿用 0.114 的 E236 方案（把依赖的 `.a` 拷进构建私有 `la-free` 目录，
再用 `GLIB_LIBS/GLIB_CPPFLAGS/DBUS_LIBS` cache 变量喂 configure）重建时：

```
ld.lld: error: unable to find library -lgio-2.0 / -lgobject-2.0 / -lgthread-2.0
                     / -lgmodule-2.0 / -lglib-2.0 / -lintl / -lffi
make[2]: *** [Makefile:716: tests/test-30574] Error 1
```

### 2.2 原因

`glib/2.84.0.1` 的 OHOS 制品是 **shared-only**（`lib` 下只有 `libgio-2.0.so` 等，没有 `.a`）。
E236 的「拷贝依赖静态库到私有目录」因此拷不到任何 glib 静态库，
`-L<la-free>` 下自然找不到 `libgio-2.0`。

### 2.3 修法

* `GLIB_CPPFLAGS` 追加共享 glib 的 `include`（含 `glib-2.0`、`include` 子目录）；
* `GLIB_LIBS` 追加 `-L<glib libdir>`，并去掉静态 glib 才需要的
  `-lintl -lffi -lpcre2-* -lz`（这些现在由 glib 的 `.so` 自身承载）；
* `la-free` 目录仍然保留（`dbus/1.14.10` 至今 static-only）：
  实测拷贝内容为 `['libdbus-1.a', 'libexpat.so', 'libexpat.so.1', 'libexpat.so.1.12.2',
  'libpcre2-8.a', 'libpcre2-posix.a']`——**glib 贡献为 0 正是 shared-only 的预期**。

### 2.4 两个 conan 语义坑（本次踩到并已修）

1. **override-only 依赖在图中被标 `Skip`、`package_folder` 为 `None`**：
   起初把 zlib 写成 `override=True`，构建时 `self.dependencies["zlib"].package_folder`
   触发 `TypeError: expected str, bytes or os.PathLike object, not NoneType`。
   共享 glib 之后 zlib 已不是链接输入 → 直接删除显式依赖，拷贝循环也只遍历
   `glib/dbus/pcre2`。
2. **`cpp_info.requires` 不能引用 override-only 的包**：
   `ERROR: package_info(): There are '(cpp_info/components).requires' that includes
   package 'expat::', but such package is not a a direct requirement of the recipe`。
   expat 的链接输入经生成的 `.pc`（`Libs`）到达 pkg-config 消费者；
   仓内同样组合的 `audtty/0.1.12`、`avahi-*`、`awf-gtk/4.2.0`、`libkysdk-base/3.0.1.3`
   共 8 个配方也都不在 `cpp_info.requires` 里列 expat。

---

## 3. 本地验证（OHOS aarch64 + 内置 clang 15，conan 2.29.1）

### 3.1 复现命令

```sh
# 工作树（提交树）: archives/d/dbus-glib/0.114.1
conan create archives/d/dbus-glib/0.114.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  -c tools.build:jobs=8 --build=missing
```

（本机执行时加了 `--no-remote`：ohpcd 匿名查询在本机会挂在
`Connecting to remote 'ohpcd' anonymously`，依赖二进制与构建目录已在本地缓存；
CI 侧不需要该参数。）

### 3.2 结果

| 项 | 实测值 |
| --- | --- |
| 退出码 | `0` |
| recipe revision | `dbus-glib/0.114.1#1cfdb01352458c4300b678a48a79f925` |
| package_id | `5bfc87a30a1fa593fed342216f869b4bd22b0134` |
| package revision | `75d86aac00835632977b69b075a82af6` |
| options | `fPIC=True shared=False`（静态库，与 0.114 一致） |
| 构建目录 | `…/p/b/dbus-392e15c1b929f/b/build-release` |

依赖图（测试包视图，全部来自缓存）：

```
Requirements
  dbus/1.14.10#2d1366526a2e661f4aa339ea87d1693c
  expat/2.8.2.1#332af6a48367eceadb1f9cf0c32f340d
  glib/2.84.0.1#75f29176eede55310742f73ebcf9a572
  pcre2/10.45#5ecd2f9871deb549e2ae07489f2e40df
Overrides
  expat/2.8.2: ['expat/2.8.2.1']
Skipped binaries
  libffi/3.4.4, zlib/1.3.1.1      # glib 共享 → 两者的二进制无需安装
```

**原失败点已消除**：`dbus-gmain/tests/test-30574`（以及
`tests/test-thread-server`、`tests/test-thread-client`、`tests/test-profile`、
`dbus/examples/*`）全部 `CCLD` 成功，`libdbus-glib-1.la` 正常 install 到包目录。

### 3.3 test_package（消费者层，两层均真实执行）

```
dbus-glib/0.114.1 (test package): RUN: clang … test_package/test.c -o test_dbus_glib \
                                   $(pkg-config --cflags --libs dbus-glib-1)
dbus-glib/0.114.1 (test package): RUN: ./test_dbus_glib
dbus-glib test_package: all checks passed          <- 第 1 层：C 消费者真实调用 API
dbus-glib/0.114.1 (test package): RUN: …/p/bin/dbus-binding-tool --mode=glib-client \
                                   --output=sample-client-glue.h sample-interface.xml
dbus-glib/0.114.1 (test package): dbus-glib test_package: API + codegen verified
```

第 1 层断言：GType 特化注册（`au`/`a{ss}`/`a{sv}`/`ao`/`as`/`suo`）、类型化追加往返、
`DBUS_GERROR` 名称映射；第 2 层：包内 `bin/dbus-binding-tool` 端到端生成客户端胶水代码
并做**内容**断言（`dbus_g_proxy_begin_call` / `org_freedesktop_Sample` / `Hello`）。

---

## 4. 上游用例

上游用例清单与逐条结果与 0.114 相同（同一 tarball、同一补丁集），
本次未重跑，原因与现实一致：上游 `make check` 的包装脚本依赖
`dbus-run-session`/`dbus-daemon`（设备与 CI worker 都缺，`exit 127`）。
逐条口径见 `test_package/MANIFEST.yml`（8 项：5 passed、3 blocked on session bus，
`assertion_count: 357`，无 stub）。

---

## 5. 限制与后续

* 本机无 D-Bus session bus 工具，涉及 session 的 3 个上游用例只能记为 blocked
  （与 0.114 同因，原因是环境而非配方）。
* 本机不验证 `shared=True` 分支（glib 无静态库时配方会按 E236 风格拒绝，与 0.114 一致）。
* 后续消费方：`libcryptui/3.12.2`（gtk3 + dbus-glib 同图的首个真实用例）
  回流重跑 `conan create --build=missing`，通过后提交 `feat/libcryptui-3.12.2`。
