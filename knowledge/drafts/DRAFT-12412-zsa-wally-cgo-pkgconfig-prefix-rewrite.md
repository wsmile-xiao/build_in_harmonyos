# DRAFT-12412-zsa-wally-cgo-pkgconfig-prefix-rewrite

## 问题

Go CGO 依赖（gousb v2.1.0，`#cgo pkg-config: libusb-1.0`）在 OHOS CI worker 上
构建时，cgo 通过 pkg-config 解析 libusb 的头/库路径。ohpcd 制品仓的
libusb/1.0.27 包（autotools `make install DESTDIR=<pkg> prefix=` 安装）里，
`lib/pkgconfig/libusb-1.0.pc` 记录的是：

```
prefix=/usr/local
libdir=${exec_prefix}/lib
includedir=${prefix}/include
```

`pkg-config --cflags libusb-1.0` 因此给出 `-I/usr/local/include/libusb-1.0`——
系统前缀，而非 Conan 制品包真实路径。worker 上该路径不存在（或指向宿主残留），
轻则报 `libusb.h: No such file or directory`，重则静默拿到宿主头文件错配。

## 根因

- autotools `DESTDIR` + 空 `--prefix` 的安装方式不会改写 libtool 生成的 .pc 里的
  `prefix=/usr/local`（.pc 的 prefix 在 configure 阶段烧录，DESTDIR 只影响落盘位置）。
- Conan 的 `cpp_info.includedirs/libdirs` 是给 conan 生成器（CMakeDeps 等）用的，
  但 `#cgo pkg-config:` 指令只走 pkg-config，不经过 conan 生成器——两条路径
  的前缀信息互不打通。
- 该问题影响一切"CGO + `#cgo pkg-config:` + 制品仓依赖"的组合（不止 libusb）。

## 修复（.pc 前缀改写 + CGO 显式注入双保险）

在 generate()/build() 里：

1. 把依赖包的 `lib/pkgconfig/libusb-1.0.pc` 复制到 `<build_folder>/pkgconfig/`，
   将 `prefix=/usr/local` 替换为 `prefix=<依赖制品包真实路径>`；
2. 导出 `PKG_CONFIG_PATH` 与 `PKG_CONFIG_LIBDIR` 指向该目录（后者屏蔽系统
   .pc 目录，防串）；
3. 双保险：`CGO_CFLAGS=-I<pkg>/include/libusb-1.0`、
   `CGO_LDFLAGS=-L<pkg>/lib -lusb-1.0` 显式注入——即使 worker 上 pkg-config
   缺失/异常，cgo 仍能解析；
4. 源 .pc 缺失时按包布局合成最小 .pc。

实现见 `archives/z/zsa-wally/2.0.1/conanfile.py` `_libusb_paths()`
（generate() 与 go-test 审计环境共用）。

## 验证

PR #14957（任务卡 #12412）本地 conan create ohos-aarch64：rc=0，
`CGO_ENABLED=1` 编译 gousb v2.1.0 链接制品仓 libusb/1.0.27；
产物 `NEEDED libusb-1.0.so.0`，test_package 经 VirtualRunEnv 提供
LD_LIBRARY_PATH 后 6/6 断言全过。

## 兜底

若制品仓配方日后修复（打包时改写 .pc prefix），改写步骤自动变为 no-op，
仅保留 CGO 显式注入；纯 C 消费者不受影响（走 conan 生成器，路径本就正确）。
