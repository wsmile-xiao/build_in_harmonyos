# DRAFT-8960: meson ninja 探测失败——hnp ninja 依赖 libc++_shared.so 而 LD_LIBRARY_PATH 缺干净 /system/lib64 项

## 触发场景

libei 1.5.0 适配（2026-09-15）：conan create 在 meson configure 阶段报
`ERROR: Could not detect Ninja v1.8.2 or newer`，但同参数手动 meson setup
成功。之前多个 meson 包（libxkbcommon/libevdev）能过是走了别的路径
（wrapper/CI 环境差异）。

## 症状签名

```
ERROR: Could not detect Ninja v1.8.2 or newer
```
且 meson-logs/meson-log.txt 中**没有任何** ninja 探测痕迹（无
`Running command: ...ninja --version` 行）——这是与 PATH 缺失类问题的
鉴别点（PATH 缺失时 ExternalProgram 找不到，同样零痕迹，需用下一步区分）。

## 根因（三层叠加）

1. `/data/service/hnp/bin/ninja` 动态依赖 `/system/lib64/libc++_shared.so`
2. 交互 shell 默认 LD_LIBRARY_PATH 含空格污染项：
   `...:/system/lib64/chipset-pub-sdk:         /system/lib64:/system/lib64/ndk:...`
   ——`"         /system/lib64"`（带 9 个空格前缀）是另一个路径名，
   干净的 `/system/lib64` 项实际**不存在**
3. meson `tooldetect.detect_ninja_command_and_version` 的异常捕获只有
   `FileNotFoundError/PermissionError`；ninja 进程启动但动态库加载失败
   rc=127，不在捕获范围 → 被当成"版本不匹配"静默跳过 → 三个 candidate
   （ninja/ninja-build/samu）全灭 → 报探测失败

**实锤命令**：
```python
subprocess.run(['/data/service/hnp/bin/ninja', '--version'])
# rc: 127, stderr: Error loading shared library libc++_shared.so: ...
```

## 修复方案

conanfile.py generate() 里给 build env 前置干净的 /system/lib64：

```python
from conan.tools.env import Environment

def generate(self):
    tc = MesonToolchain(self)
    ...
    tc.generate()
    env = Environment()
    env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
    env.vars(self, scope="build").save_script("conanbuild_libcxx")
```

等价于 `~/usr/local/bin/ninja` wrapper 的手法。CI worker 与本地同构
（OHOS 设备），conanfile 内注入最稳。

## 排障路径（实测有效）

1. conan 构建目录内 `source build-release/conan/conanbuild.sh` 后跑
   `meson setup` 复现（确保与 conan 环境一致）
2. `env` 显式传变量二分（注意直接改 PATH 会丢 LD_LIBRARY_PATH）
3. python subprocess 直接跑 ninja 看真实 rc 与 stderr
4. readelf/strace 定位缺哪个 so

## 鉴别诊断

| 现象 | 根因 | 方向 |
|---|---|---|
| ninja rc=127 + libc++_shared.so 报错 | LD_LIBRARY_PATH 缺干净项 | 本条 |
| ExternalProgram 零痕迹且 which 不见 | PATH 真缺失 | 查 profile buildenv |
| make 报 /bin/sh Error 127 | SHELL 变量 | E346 |

## 验证

libei 1.5.0：修复前 conan create 必现失败 → 注入后 G2 干净构建全绿。
