# keditbookmarks 26.04.0 验证报告

## 本机 conan create（W3）

```
conan create archives/k/keditbookmarks/26.04.0 \
  -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

结果：**PASSED**（package_id b3741dcadae35e594e699f44707b5c66b8620e13）

- configure：全部 KF6 6.14.0 依赖解析成功；KF6DocTools/X11 OPTIONAL 未找到（预期，自动跳过 doc/）
- build：keditbookmarks + kbookmarkmerger + libkbookmarkmodel_private 编译链接成功
- 上游测试：ctest 1/1 PASS（kbookmarkmodeltest，offscreen + 沙箱 HOME/XDG）
- test_package：三步冒烟全过（见下）

## 上游测试对照

| 上游注册测试 | 注册条件 | 本机执行 | 结果 |
|---|---|---|---|
| kbookmarkmodeltest | BUILD_TESTING=ON（ecm_add_test） | ctest（conan create 内） | PASS |

上游注册测试总数 N=1（26.04.0 源码 src/kbookmarkmodel/tests/ 唯一测试目标）。

## test_package 冒烟（bin 交付）

| 步骤 | 命令 | 验证点 | 结果 |
|---|---|---|---|
| 1 | kbookmarkmerger --help | QCommandLineParser usage 输出，exit 0 | PASS |
| 2 | keditbookmarks --importkde3 bookmarks.xml | headless 导入写默认 XBEL 库，exit 0 | PASS |
| 3 | keditbookmarks --exportns out.html | Netscape HTML 导出，含导入书签 | PASS |

导出内容抽样（端到端数据完整性）：
```
<!DOCTYPE NETSCAPE-Bookmark-file-1>
...
<DT><A HREF="https://kde.org">KDE Homepage</A>
<DT><A HREF="https://invent.kde.org/utilities/keditbookmarks">keditbookmarks upstream</A>
```

## 产物清单

- bin/keditbookmarks（GUI 编辑器 ELF）
- bin/kbookmarkmerger（CLI 合并工具 ELF）
- lib/libkbookmarkmodel_private.so.6（+ .so.5.97.0，SOVERSION 6）
