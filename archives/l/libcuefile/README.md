# libcuefile — CUE/TOC 文件处理库

## 基本信息

| 项目 | 信息 |
|------|------|
| 软件 | libcuefile |
| 版本 | r475 |
| 构建系统 | CMake |
| 目标平台 | ohos-aarch64 |
| 功能 | CUE/TOC 光盘映像文件解析与生成 |

## 编译指导

### 配置命令

```bash
cmake .. -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
         -DCMAKE_POLICY_VERSION_MINIMUM=3.5
```

**注意**: 原始 CMakeLists.txt 要求 CMake 2.4，需要使用 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 参数启用兼容模式。

### 编译命令

```bash
make -j$(nproc)
make install DESTDIR=$TEST_PREFIX  # staging 安装
make install                       # 本地安装
```

### 编译产物

- **静态库**: `lib/libcuefile.a`
- **动态库**: `lib/libcuefile.so`
- **头文件**: `include/cuetools/{cd.h, cdtext.h, cuefile.h}`

## 补丁清单

### 0001-src-CMakeLists.txt.patch

**类型**: 功能补丁（平台通用）

**问题**: 原始 CMakeLists.txt 只安装库文件，缺少头文件安装指令。

**修改内容**:
```diff
+install(DIRECTORY ${libcuefile_SOURCE_DIR}/include/cuetools DESTINATION include)
```

**应用方式**: 自动应用（`ohc-run.py finish`）

**说明**: 此补丁对所有平台都必需，因为头文件是使用库的前提条件。

## 已知限制

1. **编译警告**: cue_parse.y 中存在未声明函数警告（不影响功能）
2. **无测试套件**: 项目未提供自动化测试，需手动验证功能
3. **无 pkg-config**: 未生成 .pc 文件，编译依赖库时需手动指定路径

## 功能验证

### API 测试

```c
// 创建 CD 结构
Cd *cd = cd_init();

// 设置 CD 模式
cd_set_mode(cd, MODE_CD_DA);

// 添加 track
Track *track = cd_add_track(cd);
track_set_filename(track, "audio.wav");
track_set_mode(track, MODE_AUDIO);

// 设置 CDTEXT
Cdtext *cdtext = cdtext_init();
cdtext_set(PTI_TITLE, "Album Title", cdtext);
```

### CUE 文件解析

```c
int format;
Cd *cd = cf_parse("album.cue", &format);
if (cd && format == CUE) {
    printf("Tracks: %d\n", cd_get_ntrack(cd));
    Cdtext *text = cd_get_cdtext(cd);
    printf("Album: %s\n", cdtext_get(PTI_TITLE, text));
}
```

### 编译依赖库的程序

```bash
cc -o myapp myapp.c \
   -I/storage/Users/currentUser/usr/local/include \
   -L/storage/Users/currentUser/usr/local/lib \
   -lcuefile
```

## 版本历史

| 版本 | 日期 | 状态 | 备注 |
|------|------|------|------|
| r475 | 2026-05-11 | ✅ success | 首次编译，添加头文件安装补丁 |