# libbigwig/0.4.8 W0 依赖发布检查报告

- 执行时间: 2026-09-18(macOS 编排,设备端私有 CONAN_HOME 执行)
- 结论: **pass** — 依赖全部已发布,目标版本未被占用,可正常适配
- 原始报告: 任务目录 `w0.json`(sha256 `a9a10072daabe9029c488b75de83c5b1bbd069930dc30e39d32fa298248fa962`,140 行,8038 字节;schema 1)
- 私有环境: `$HOME/ws/tmp/harmony-pipeline/libbigwig-w0-cc4rdokk`(CONAN_HOME,profile 为该目录下核对的 `ohos-aarch64` 绝对路径,remote 仅 ohpcd)

## 版本占用

`libbigwig/0.4.8` 在制品仓不存在(version_occupancy=missing,`conan download libbigwig/0.4.8 -r=ohpcd --only-recipe` 报 Recipe not found)→ 首次适配,版本号 0.4.8 可用,无占用冲突。

## 依赖清单与验证命令

依赖来源: 上游 CMakeLists.txt 静态分析(`find_package(ZLIB REQUIRED)` 必需;`find_package(CURL REQUIRED)` 受 `WITH_CURL` 选项控制,配方默认 ON)。

| 依赖 | 结果 | 验证命令(私有 CONAN_HOME 内执行) | 退出码 |
| --- | --- | --- | --- |
| zlib/1.3.1.1 | available | `conan download zlib/1.3.1.1 -r=ohpcd --only-recipe` | 0 |
| curl/8.15.0 | available | `conan download curl/8.15.0 -r=ohpcd --only-recipe` | 0 |

zlib/1.3.1.1 下载回执(逐字):

```
Local Cache
  zlib
    zlib/1.3.1.1
      revisions
        9a23e7d51311d0440b6e4d36cf44e4d9 (2026-07-14 09:36:56 UTC)
```

curl/8.15.0 下载回执(逐字):

```
Local Cache
  curl
    curl/8.15.0
      revisions
        4ae5a3c702753d2fc507808204655813 (2026-08-04 12:35:09 UTC)
```

## 版本选型依据

- zlib 取 1.3.1.1(而非 1.3.1): curl/8.15.0 配方 requirements 显式声明
  `self.requires("zlib/1.3.1.1")`(注释标明为 PIC 静态包),下游对齐同版本避免依赖图冲突。
- curl 取 8.15.0: 制品仓已发布版本(8.5.0/8.15.0 中较新);其 package_info 导出
  `cmake_file_name=CURL`、`cmake_target_name=CURL::libcurl`,与上游 libBigWig 的
  `find_package(CURL REQUIRED)` 与 `CURL::libcurl` 链接目标完全一致。

## 环境事实

- Conan 入口: `/storage/Users/currentUser/.local/bin/conan`(Conan 2.29.1,启动探针 9.9s,exit 0)
- 目标 profile: `os=OHOS, arch=armv8, compiler=clang 15, compiler.libcxx=libc++, build_type=Release`
