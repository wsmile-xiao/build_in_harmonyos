# DRAFT-zita-lrx-0.1.2-ohos-staged-closure-libcpp-resolution

## 现象（zita-lrx 0.1.2 本机实测）

test_package 按 jaaa/aliki 模式把依赖闭包 staged 到可写目录并签名后，直接
`LD_LIBRARY_PATH=<staged> ./zita-lrx -h` 报：

```
Error loading shared library libc++_shared.so: (needed by ./zita-lrx)
rc=127
```

staged 闭包里有 libclthreads.so.2 / libjack.so.0（conan 依赖），唯独没有
libc++_shared.so——它不是任何 conan 包的产物，是 OHOS 系统 C++ 运行时。

## 实测矩阵（本机，/lib/ld-musl-aarch64.so.1）

| 运行方式 | 结果 |
|---|---|
| bare（无 LD_LIBRARY_PATH） | rc=127（Error loading shared library libc++_shared.so） |
| LD_LIBRARY_PATH=/system/lib64 | rc=0 |
| LD_LIBRARY_PATH=<staged 闭包> | rc=127（同上错误） |
| **LD_LIBRARY_PATH=<staged>:/system/lib64** | **rc=0，三层断言全过** |

关键观察：musl ldso 在 LD_LIBRARY_PATH 已指向 staged 目录时，**不会**再从
默认路径（/etc/ld-musl-aarch64.path 含 /system/lib64）补位解析 staged 里缺的
soname——LD_LIBRARY_PATH 一旦设置就整个接管了搜索顺序，缺的库不会回落。
（/system/lib64 里确实存在 libc++_shared.so，1291536 字节。）

不同构建主机行为漂移：部分 CI worker 上同类测试不需要该兜底也能跑，说明
其 ldso/环境默认解析路径不同——不显式兜底则测试结果随主机漂移，偶发 127。

## 方案

test_package 的 OHOS 分支：

```python
self.run(
    'LD_LIBRARY_PATH="%s:/system/lib64" "%s" "%s" "%s"' % (runtime_root, script, staged_dir, work_dir),
    env="conanrun",
)
```

staged 闭包优先（验证包自身依赖），/system/lib64 兜底（C++ 运行时 soname）。

## 豁免与边界

- 适用于"裸 make 产物 + 手工 staged 闭包"的消费者测试；CMake 产物经
  conanrun env 的 LDLIB 另有机制，不在本条范围。
- 极端裁剪系统若无 /system/lib64/libc++_shared.so，退路是把 SDK
  llvm/lib 下的同名库复制进 staged 闭包并同样签名（见 kv fallback）。
- 与 DRAFT-nedit-5.8 headless 冒烟范式互补：nedit 解决"跑什么断言"，
  本条解决"闭包跑得起来"的运行时解析兜底。

## 关联

- E137 查重：E137 是 Perl ld.lld 编译期 flag 问题，与本条（运行期 ldso
  解析）不同根因，零覆盖。
