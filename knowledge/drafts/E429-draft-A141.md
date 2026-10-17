# E429 — conan get() 按 URL basename 扩展名推断压缩格式：无扩展名 URL（codeload tag 归档）回退 zip 报 BadZipFile

## 错误特征
```
ERROR: ...: BadZipFile: File is not a zip file
```
conan source() 阶段（conan create / conan install --build）下载后解压立即失败，无后续编译日志；tarball 本体完整（sha256 校验通过或可另行验证）。

## 触发条件
- 构建系统: conan（conandata.yml sources URL）
- 阶段: source（下载/解压）
- 特征: sources url 的 basename 无文件扩展名，典型为 codeload.github.com/<owner>/<repo>/tar.gz/refs/tags/<tag>（basename 即 tag 名，如 "0.26"）

## 根因分析
conan 2.29 的 get()→unzip() 按文件名后缀判定压缩格式（conan/tools/files/files.py L349 实测）；codeload tag 归档 URL 的 basename 是 tag 名（无 .tar.gz 扩展名）→ 格式判定回退 zip → 对 tar.gz 内容报 `BadZipFile: File is not a zip file`。sha256 校验针对实际下载内容，不受 basename 影响。

## 解决方案

### 推荐方案
conandata.yml sources 增加 `filename: '<name>.<ver>.tar.gz'` 字段——get() 将该值透传给 unzip() 作为格式判定名，判定即正确；sha256 仍校验实际内容，不受影响。备选：改用带扩展名的官方源 URL（release 资产链）。

### 禁止做法
- ❌ 仅凭下载成功即判定解压可用——BadZipFile 发生在解压阶段，下载 sha256 通过不代表 conan 能解开
- ❌ 把 codeload URL 手动改写成带扩展名的个人镜像/网盘链接（R39：源 URL 必须官方源）

## 验证
```bash
conan create <配方目录> -pr=<ohos profile>
# 修复前：source() 阶段 BadZipFile: File is not a zip file
# 修复后（conandata 加 filename）：下载/解压通过，进入 build()
```

## 关联条目
- 相关: 无（新模式，库内无重复条目）
- 背景知识: E002（设备 /tmp 只读）为同批次 conan 下载链路的环境类踩坑，非同一模式
