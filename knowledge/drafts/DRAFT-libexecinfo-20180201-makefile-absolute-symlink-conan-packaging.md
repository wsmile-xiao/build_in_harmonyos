# DRAFT-libexecinfo-20180201-makefile-absolute-symlink-conan-packaging — 纯 Makefile 库的绝对路径 symlink 需在 package() 用 os.symlink 建相对链接

- 触发事件：libexecinfo 20180201 适配，conan create G2 首次失败
- 路径：Path B（知识库扩展）
- 编号：DRAFT-libexecinfo-20180201-makefile-absolute-symlink-conan-packaging

## 现象

首版配方在 `package()` 里尝试用 `symlinks.symlink(self, ...)` 创建
`libexecinfo.so -> libexecinfo.so.1`，conan create 立即失败：

```
ERROR: libexecinfo/20180201@ohpcd/stable: Error in package() method, line 87
AttributeError: module 'conan.tools.files.symlinks.symlinks' has no attribute 'symlink'
```

同时，上游 Makefile 的 install 目标为：

```make
ln -s /usr/lib/libexecinfo.so.1 $(DESTDIR)$(LIBDIR)/libexecinfo.so
```

把宿主绝对路径 `/usr/lib` 硬编码进链接目标，直接 `make install DESTDIR=...`
会打包出指向 `/usr/lib` 的死链接，不适合 Conan 分发。

## 根因

1. conan 2.29.1 的 `conan.tools.files.symlinks.symlinks` 模块只导出
   `get_symlinks` / `absolute_to_relative_symlinks` / `remove_external_symlinks` /
   `remove_broken_symlinks`——定位是"扫描/转换/移除"，**没有创建符号链接的帮手**。
2. 上游纯 Makefile 库以 `/usr` 为安装根编写 install 目标，`ln -s` 目标写绝对路径，
   与 Conan 的 DESTDIR 打包模型冲突。

## 可复用处置

1. 不依赖上游 `make install` 的 `ln -s`；`package()` 手动 copy 头文件/库文件后，
   用标准库 `os.symlink` 创建**相对**链接：

   ```python
   link = os.path.join(libdir, "libexecinfo.so")
   if os.path.islink(link) or os.path.exists(link):
       os.unlink(link)
   os.symlink("libexecinfo.so.1", link)
   ```

2. 相对链接目标不带 `/usr/lib` 等绝对路径，打包进包内 `lib/` 即可被下游解析。
3. 若配方原用 `conan.tools.files.symlinks.symlink` → 直接整体换掉；
   需批量转换已打包链接可用 `absolute_to_relative_symlinks`，需清理死链接
   可用 `remove_broken_symlinks`，但创建必须走 `os.symlink`。

## 判定要点

- 与 E274（`-Wl,-soname` 后需补 soname 链接，链接器期语义）不同域：本条是
  **打包期**链接布局修复。
- 与 DRAFT-E5xx（制品仓 so 烙印绝对 NEEDED 的保签名 symlink 修复）不同：
  那条解决发布机烙印路径问题，本条解决打包期相对链接布局。
- 只在 package() 手工布局的配方需要处理；CMake install 用相对 INSTALL
  目标的配方不触发。

## 实证

- libexecinfo 20180201：改为 `os.symlink` 相对链接后 conan create
  G2/G3/G4 PASS；test_package 双用例（消费者 test.c + 鸿蒙专项
  ohos_special_test.cpp）退出码 0，包内 `libexecinfo.so -> libexecinfo.so.1`
  相对链接生效。