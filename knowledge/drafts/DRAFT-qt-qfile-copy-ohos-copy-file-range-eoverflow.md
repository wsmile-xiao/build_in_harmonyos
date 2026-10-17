# Qt `QFile::copy()` 在 OHOS 上恒失败（errno 75 / EOVERFLOW）

> 草稿条目对应的 KV：`knowledge/drafts/DRAFT-qt-qfile-copy-ohos-copy-file-range-eoverflow.kv`
> 状态：DRAFT（待人工/主审合并为 E 条目）

## 1. 现象

OHOS 上任何使用 `QFile::copy(source, target)` 的代码都返回 `false`，无论源/目标是否可读写：

- 上游 autotest 直接断言失败：
  `kcoreaddons` → `autotests/plugin/kpluginmetadatatest.cpp` 的
  `testFindingPluginInAppDirFirst`、`testFindingPluginInPluginNamespace`：
  ```
  QVERIFY(QFile::copy(originalPluginPath, pluginAppPath));   // FAIL
  ```
- `QFile::error()` 为 `QFile::ResourceError`；系统层 `errno = 75`（`EOVERFLOW`，
  "Value too large for defined data type"）。
- **反证**：把同一对文件改成 64 KiB 缓冲的 read/write 循环复制，**成功**。
  即失败点不是文件系统不可写，而是 Qt 选用的拷贝系统调用在 OHOS 上不被支持。

## 2. 根因

Qt 6 的 `QFile::copy()` 走 `QFileSystemEngine::copyFile()`，在 Unix 上优先尝试
`copy_file_range()` / `sendfile()` 快路径，只在 **EXDEV / ENOSYS / EINVAL / EPERM**
等少数 errno 上回退到 read/write。

OHOS 文件系统（HMDFS 挂载点，例如 `$HOME` 下的构建目录、`$TMPDIR`、应用沙箱目录）
上的 `copy_file_range()` 未正确实现，对任意源/目标均返回 `-1` 且 `errno=EOVERFLOW`。
Qt 未把 `EOVERFLOW` 列入回退集合 → 每一次 `QFile::copy()` 都注定失败。

对比：`fallocate()` 在同平台返回 `EACCES`（见 E523/E331），可见 OHOS 文件系统对
若干 POSIX/内核扩展调用的实现不完整，且 Qt/工具链的错误码回退白名单往往只覆盖
"标准"取值 —— 这是同一类平台缺陷的另一种表现。

## 3. 影响面

| 场景 | 影响 |
|---|---|
| 上游 autotest fixture staging（`QTemporaryDir` + `QFile::copy`） | 测试硬失败，无法通过 |
| 应用安装/缓存/配置拷贝 | **静默失效**（返回 false 不抛异常），比测试失败更隐蔽 |
| KDE 框架测试族（kcoreaddons 起，kio 闭包内同构代码） | 每个包重复踩坑 |

## 4. 处置方案

### 首选：调用点改 read/write 循环（配方以补丁承载）

本仓已落地先例：
`archives/k/kcoreaddons/6.26.0.1/patches/0006-qfilecopy-harmonyos-plugin-test.patch`

```cpp
// QFile::copy() fails on HarmonyOS: Qt's copy path reports EOVERFLOW
// (errno 75) for every source and target on the OHOS filesystem, while a
// plain read/write loop copies the very same files fine.
static bool copyPluginFixture(const QString &source, const QString &destination)
{
    QFile in(source);
    if (!in.open(QIODevice::ReadOnly)) return false;
    QFile out(destination);
    if (!out.open(QIODevice::WriteOnly | QIODevice::Truncate)) return false;
    char buffer[64 * 1024];
    qint64 readBytes = 0;
    while ((readBytes = in.read(buffer, sizeof(buffer))) > 0)
        if (out.write(buffer, readBytes) != readBytes) return false;
    return readBytes == 0 && out.flush();
}
```

补丁只替换复制方式，**保留**原有的插件查找断言逻辑（不弱化测试）。

### 回退：LD_PRELOAD shim

`LD_PRELOAD` 一个令 `copy_file_range()` 返回 `-1/ENOSYS` 的 shim，逼 Qt 走
read/write 回退分支。仅用于测试进程与本地复现；shim 必须返回 `ENOSYS`
（返回 `EOVERFLOW` 无效，因为 Qt 不回退该 errno）。

### 禁止

- `QVERIFY(true)` / 宏屏蔽 `QFile::copy` / 直接删断言 —— 等于删除测试，掩盖平台缺陷
  （与 R8 空壳 stub 同类问题）。

## 5. 复现命令

```sh
printf '%s\n' '#include <QFile>' '#include <cstdio>' '#include <cerrno>' \
  '#include <cstring>' 'int main(int c,char**v){QFile s(v[1]),d(v[2]);' \
  'bool ok=s.copy(v[2]);printf("copy=%d errno=%d (%s) error=%d %s\n",ok,errno,' \
  'std::strerror(errno),(int)d.error(),qPrintable(d.errorString()));return ok?0:1;}' \
  > $TMPDIR/qcopy.cpp
clang++ $TMPDIR/qcopy.cpp $(pkg-config --cflags --libs Qt6Core) -o $TMPDIR/qcopy
echo hi > $TMPDIR/qsrc && $TMPDIR/qcopy $TMPDIR/qsrc $TMPDIR/qdst
# OHOS 预期: copy=0 errno=75 (Value too large for defined data type)
```

## 6. 关联

- `similar_to`: E331（Go 链接器 fallocate 在 HMDFS 上 EACCES）、E523（同一族工具链
  写盘调用在 HMDFS 上未实现 → 错误码不在回退白名单）
- 出处任务：kcoreaddons 6.26.0.1 适配（kio/6.26.0.1 依赖闭包）
