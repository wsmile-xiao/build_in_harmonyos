# DRAFT-installkernel-conan-get-unzip

## conan 2.29.1 get() 无条件解压：裸文件上游必须用 download()

### 现象

真机（HarmonyOS PC，Conan 2.29.1）`conan-verify installkernel 4.1` G2 首验 FAIL：

```
ERROR: installkernel/4.1@ohpcd/stable: Error in source() method
    BadZipFile: File is not a zip file
```

installkernel 上游为 Alpine aports 内嵌的单文件 POSIX 脚本（918 字节），无
tarball/tag；配方用 `get(self, **self.conan_data["sources"])` 下载裸文件。

### 根因

- conan 2.x `tools.files.get()` 是「下载 + 解压」高层封装，源码为
  `download() → unzip() → os.unlink()`，**无条件**调用 unzip()：
  - 与 filename 是否带归档扩展名无关（"installkernel" 无扩展名照样解压）
  - 与 `strip_root` 参数无关（strip_root 仅转发给 unzip 的目录拍平逻辑；
    首轮怀疑 strip_root=True 触发、去掉后二连败，读设备端
    `conan/tools/files/files.py` 源码确认）
- 裸文件被当 zip 解压 → `BadZipFile: File is not a zip file`

### 推荐方案

裸文件上游一律改用 `download()`：

```python
from conan.tools.files import download

def source(self):
    src = self.conan_data["sources"]
    download(self, src["url"], filename=src.get("filename"),
             sha256=src.get("sha256"))
```

- 纯下载，不碰解压；sha256 校验与多 URL 回退原生支持
- conandata 结构（url/sha256/filename）不变，仅 source() 换 API
- 本包改后真机八门禁（G0-G4/L2/L4/L5）全绿

### 实证记录

- 2026-09-26 真机 conan 2.29.1：get() 裸文件两连败（strip_root 有/无均
  BadZipFile）→ 读源码定位 → download() 一次通过
