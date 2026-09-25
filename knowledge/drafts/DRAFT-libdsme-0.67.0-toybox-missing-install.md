# DRAFT-libdsme-0.67.0-toybox-missing-install

## 现象

按上游 Makefile 安装到 staging：

```
install -m755 -D -t /.../stage/usr/lib libdsme.so.0.3.0 ...
make: install: No such file or directory
make: *** [Makefile:64: install_main] Error 127
```

`command -v install` 无输出——OHOS toybox 未提供 GNU install(1)。

## 影响

任何依赖 `install -D -t` 的上游安装规则（手写 Makefile 或 automake 生成的
install 目标）在 OHOS 设备侧本地构建时不可用。CI worker 环境可能自带
coreutils，但配方不应假设。

## 修复（推荐）

Conan `package()` 显式布局，不调用 `make install`：

```python
copy(self, "libdsme.so.0.3.0", src=source, dst=libdir)
os.symlink("libdsme.so.0.3.0", libdir + "/libdsme.so.0")
os.symlink("libdsme.so.0", libdir + "/libdsme.so")
copy(self, "*.h", src=source + "/include/dsme", dst=include_dsme)
copy(self, "*.pc", src=source, dst=libdir + "/pkgconfig")
```

## 验证

- conan create 全流程通过；产物树含 3 库（含 SONAME 软链）、8 头文件、3 个
  pkg-config 文件与 COPYING。
- 消费者测试链接 `-ldsme` 成功，运行通过。

## 适用范围

手写 Makefile、automake 项目在 OHOS 本地构建的安装阶段；修复方式统一为
"package() 显式安装"或"补丁把 install 换成 cp"。
