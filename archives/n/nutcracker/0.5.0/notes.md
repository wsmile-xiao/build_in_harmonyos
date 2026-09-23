# nutcracker 0.5.0 适配笔记（HarmonyOS PC / aarch64）

## 概述

twemproxy（nutcracker）是 Twitter 开源的轻量级高性能 Redis/Memcached 协议代理，
用户通过 YAML 文件配置多个后端服务器池，前台监听一个端口向池内分发请求。
本适配目标：OHOS PC（aarch64）环境编译为可运行的 daemon 工具。

## 构建链

```
conan create archives/n/nutcracker/0.5.0 -pr:h ci/conan/profiles/ohos-aarch64 --build=missing
```

configure 失败时（探针实证）：
1. `--host=aarch64-linux-ohos` → `config.sub: system 'ohos' not recognized`（patch 0001 修复）
2. 不带 host → `config.guess: cannot guess build type`（HarmonyOS uname 不识别，patch 0001 修复）

patch 0002（configure）的四个作用：
1. `tar xvfz contrib/yaml-0.2.5.tar.gz -C contrib` 后用主树 patch 后的 config.guess/sub
   覆盖 vendored yaml-0.2.5 的 2011 旧版（否则子 configure 同报 ohos 不识别）。
2. 主 configure 的 `mktemp -d "./confXXXXXX"` → `mkdir ./conf$$-$RANDOM`
   （HMDFS 下 Toybox mktemp 创建 0700 目录，进程 UID≠owner 时 group 无写权限，
   config.status 写临时文件 Permission denied；mkdir 目录 HMDFS 强制 drwxrws--x）。
3. 同样通过 sed 修复 vendored yaml-0.2.5/configure 内的 mktemp。
4. 附带修复了脚本路径下 automake 自动重建的隐患（配合 conanfile 的 touch）。

## 铁律对照

- R32: `settings.os` 判断用 `in ("Linux","OHOS")` ✓
- R33: CC 从 profile conf `tools.build:compiler_executables` 读取 ✓
- R34/PF3: test_package 通过 `bash script` 实际执行 nutcracker（-V/-t/daemon/端口/转发）✓
- R38: daemon 工具 → 软件级 commands.json（type=tool, binary=true）✓
- R39: 源码 URL 官方 GitHub release ✓；sha256 本地计算（FreeBSD distinfo 对应 codeload 归档不同文件，明文记录）
- R9: make -j1（HMDFS jobserver fifo EPERM）✓
- R6: 不重生成构建系统文件；补丁只动 config.guess/sub/configure，不引入平台宏（构建系统探针类文件，PR 已说明理由）✓

## 测试

| 项 | 结果 |
|---|---|
| vendored yaml 0.2.5 上游测试（make check 内） | 2/2 PASS（test-version, test-reader） |
| nutcracker test_all 单元测试（make check 内） | 967/967 PASS（src/ 目录运行） |
| nutcracker -V | nutcracker-0.5.0，async event backend: epoll |
| nutcracker -t 最小配置 | 通过 |
| daemon 起进程 + 端口探测 + shutdown | 通过 |
| 本地 nc 假后端转发 | 环境有 nc 时通过（get foo -> $-1） |

## 已知限制

- HMDFS noexec：脚本不得直接执行（test_package 用 `bash script` 调用）。
- 平台固定 ohos-aarch64（profile ohos-aarch64）；其他平台未验证。
- 包内除 nutcracker/test_all 外会顺带安装 vendored libyaml 的头文件与静态库
  （上游 AC_CONFIG_SUBDIRS 行为），属预期。