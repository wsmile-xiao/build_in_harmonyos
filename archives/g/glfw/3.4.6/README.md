# glfw 3.4.6 — 鸿蒙 PC conan 制品

`os=OHOS, arch=armv8`(= aarch64)的 conan 包,支持两种消费形态。

## 出包(开发验证 / CI)

```bash
# macOS：交叉编译验证(需 export OHOS_NDK_HOME 指向已装 OHOS SDK 的 native ndk)
bash make-package.sh

# 鸿蒙 PC CI：原生编译并上传 remote
bash make-package.sh --upload
```

> 源码由 `conandata.yml` 的 url 在 `conan create` 时下载并 sha256 校验（`source()` 用 `get()`）。

## 前提

> 所用 conan 的 settings 须含 `os=OHOS`（大写）及 `compiler.version=15`；stock conan 2 默认不含 OHOS。推荐在 `~/.conan2/settings_user.yml` 的 `os:` 下加一行 `    OHOS:`（非侵入扩展，不改 settings.yml），或使用 OpenHarmonyPCDeveloper 分发的 conan。

## .so 签名

鸿蒙 PC 对 `dlopen` 加载的 `.so` 强制校验签名（未签名时 `dlopen` 不报错，但 `dlsym` 全返回 NULL）。本 recipe 的 `package()` 在 install 后会对包内所有 `.so` 就地自签，调随包的 `scripts/sign-so.sh`（DevEco `binary-sign-tool` localSign）。

签名器三选一（`sign-so.sh` 自动解析）：**鸿蒙 PC** 用原生 `binary-sign-tool`（放进 PATH 或 `SIGN_TOOL=<路径>`，**无需 java**）；**mac** 回退 DevEco 的 `java -jar binary-sign-tool.jar`，路径可经环境变量覆盖（mac 默认即 `/Applications/DevEco-Studio.app`）：

```bash
export DEVECO=/Applications/DevEco-Studio.app
export JAVA=$DEVECO/Contents/jbr/Contents/Home/bin/java
export JAR=$DEVECO/Contents/sdk/default/openharmony/toolchains/lib/binary-sign-tool.jar
```

设备 CI 上须用上述 env 指到设备侧工具，否则 `package()` 因签名工具缺失而失败。

## 一次性设备配置(鸿蒙 PC，让后续消费命令免写 `-pr`)

在本 recipe 目录下执行一次(用的都是随包自带的 profiles/ 与 deployers/)：

```bash
# 加 remote（默认地址；有上传账号时再 conan remote login）
conan remote add ohos-conan https://cnb.cool/OpenHarmonyPCDeveloper/Conan

# 把 ohos-native 设成 default profile → 后续 conan install 免写 -pr
cp profiles/ohos-native ~/.conan2/profiles/default

# deployer 装进 conan home → --deployer 按名引用，不用写路径
mkdir -p ~/.conan2/extensions/deployers
cp deployers/usr_local_deploy.py ~/.conan2/extensions/deployers/
```

> 前提：conan settings 须认 `os=OHOS`（见上「前提」）。`default`=ohos-native 假定本机只做 OHOS 目标。

## 消费 A：conan 工程(需求 3，如 macOS 交叉编译依赖本库的库)

```bash
# 鸿蒙 PC（已做上面一次性配置）：免 -pr，[*] 自动取最新版
conan install --requires="glfw/[*]"

# 未做配置 / macOS 交叉：显式给 profile
conan install --requires=glfw/3.4.6 -pr:b default -pr:h profiles/ohos-cross            # macOS
conan install --requires=glfw/3.4.6 -pr:b profiles/ohos-native -pr:h profiles/ohos-native   # 设备
```

生成 `glfw-config.cmake` / `glfw.pc`(指向 cache)；`find_package(glfw)` 消费，运行期 `source conanrun.sh`。

## 消费 B：裸程序(需求 2，设备 ~/usr/local + dlopen)

```bash
# 已做一次性配置：免 -pr、deployer 按名引用
conan install --requires="glfw/[*]" --deployer=usr_local_deploy --deployer-folder=$HOME/usr/local

# 未做配置：显式 profile + deployer 路径
conan install --requires=glfw/3.4.6 -pr:b profiles/ohos-native -pr:h profiles/ohos-native \
    --deployer=deployers/usr_local_deploy --deployer-folder=$HOME/usr/local
```

头文件/库/.pc 展开到 `~/usr/local/{include,lib,lib/pkgconfig}`，`.pc` 前缀已重定位；裸 `dlopen`/pkg-config 即可命中(必要时 `export LD_LIBRARY_PATH=$HOME/usr/local/lib`)。

## 卸载

```bash
# 卸 ~/usr/local 部署：deployer 生成的精确卸载脚本（按清单删 + 收空目录，绝不 rm -rf 前缀；被改动过的文件跳过）
bash ~/usr/local/.conan-deployed/glfw-3.4.6-uninstall.sh

# 从 conan 本地缓存移除
conan remove "glfw/*" -c
```

## remote / 无账号共享

默认 remote `https://cnb.cool/OpenHarmonyPCDeveloper/Conan`(`CONAN_REMOTE_URL` 环境变量 / `--remote-url` 覆盖)。有上传权限：`bash make-package.sh --upload` 传二进制，消费方 `conan install --requires="glfw/[*]"` 即从 remote 自动拉最新。

无上传账号时点对点搬运预编译包(免 remote)：

```bash
conan cache save "glfw/3.4.6:*" --file glfw.tgz   # 出包机导出（recipe + 二进制）
conan cache restore glfw.tgz                               # 目标机导入
```
