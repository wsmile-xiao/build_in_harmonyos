# zsa-wally 2.0.1 — 适配笔记

## 任务卡形态定谳（W0 实测）

任务卡 #12412 `zsa-wally 2.0.1`（lang=cpp 为任务卡预填，实际以上游 sdist 为准）。
上游形态实测：

| 仓库 | 形态 | tag 2.0.1 | 结论 |
|---|---|---|---|
| github.com/zsa/wally-cli | Go CLI（go.mod go 1.14，gousb v2.1.0 CGO→libusb-1.0，gohex，pb.v1，spin，aurora） | **有**（`2.0.1-linux`） | ✅ 本件适配对象 |
| github.com/zsa/wally (GUI) | Go + Wails v1.16（webkit2gtk + npm 前端） | **无**（tag 序列 2.0.0→2.1.0） | ❌ 不适用 |
| github.com/zsa/wally-win | Windows 原生重写版 | 无 2.0.1 | ❌ 不适用 |

佐证链：
1. Codeberg 镜像 `djerun/zsa-wally`（zsa/wally 的完整镜像）tag 列表实测：2.0.0-linux / 2.0.0-osx / 2.0.0-win / 2.0.0-winx64 → 2.1.0-linux / 2.1.0-osx / 2.1.0-winx64，**无 2.0.1**。
2. AUR `zsa-wally-cli 2.0.1-6` PKGBUILD：`url="https://github.com/zsa/wally-cli"`，`source=...$url/archive/refs/tags/$pkgver-linux.tar.gz`，sha256 `071b1bd10e9160c441e833be3bea211ccf835c4f1792b0c6c7fc86f7aa0695d1`。
3. 本地经镜像通道下载官方 tarball，sha256 与 AUR 权威值**逐位一致**；与 jsdelivr CDN 逐文件 diff 完全一致（12 文件：main.go/dfu.go/teensy.go/usb.go/go.mod/go.sum/README.md/license.md/default.nix/flake.nix/flake.lock/.gitignore）。
4. 任务卡 url 字段为 null，以实测为准。

### GUI 路线不可行存证（Electron/Wails 均不适配 OHOS 制品仓）

- 任务卡预案提示"Electron 件查仓内先例（大概率无）"。实测：GUI 仓 zsa/wally 2.x 是 **Wails v1**（Go+webkit2gtk+npm），不是 Electron；1.x 历史版本是更老技术栈。
- `conan list "webkit2gtk/*" -r=ohpcd` → Found 0；`conan list "wails/*" -r=ohpcd` → Found 0。GUI 框架依赖链在制品仓完全缺失。
- CLI flavor（wally-cli）与 GUI 共享同一 USB 烧录核心（gousb/libusb），CLI 是 ZSA 官方维护的完整烧录工具，功能上覆盖 ErgoDox EZ（.hex/Teensy HalfKay）与 Moonlander/Planck EZ（.bin/STM32 DFU）两条烧录路径。
- 结论：按 wally-cli 2.0.1（tag `2.0.1-linux`）适配，CLI 路线可行且是 2.0.1 唯一真身。

## 构建

- Go 1.23.8 自举（mirrors.aliyun.com/golang/go1.23.8.linux-arm64.tar.gz，sha256 `9d6d938422724a954832d6f806d397cf85ccfde8c581c201673e50e634fdc992`，与 addchain/aiac 配方同款权威值）。
- CGO_ENABLED=1（gousb `#cgo pkg-config: libusb-1.0`）：CC 取 profile `tools.build:compiler_executables`（clang 15，target aarch64-unknown-linux-ohos）。
- libusb/1.0.27 来自 ohpcd 制品仓（package_id 01d92cf349a0dd98ff915f4bd99a04430171517f，armv8/OHOS/clang15/Release/shared）。
- **.pc 前缀改写**：制品仓 libusb 的 `lib/pkgconfig/libusb-1.0.pc` 带 `prefix=/usr/local`（autotools DESTDIR+prefix= 安装的副作用，指向系统路径对 Conan 包错误）。配方在 generate() 把 .pc 复制到 build/pkgconfig/ 并改写 prefix 为制品包真实路径，注入 `PKG_CONFIG_PATH`+`PKG_CONFIG_LIBDIR`；同时 `CGO_CFLAGS=-I<include>`/`CGO_LDFLAGS=-L<lib> -lusb-1.0` 显式注入做双保险（gousb 的 cgo 指令二选一即可解析，但 OHOS 上 pkg-config 环境不可控，显式 flags 保证确定性）。
- 链接输出放 el2 工作区 `/data/storage/el2/base/haps/entry/files/zsa-wally-conan-go/2.0.1/link-out/`（HMDFS 上 Go linker mmap 失败 E051，addchain 先例），再拷回 build/bin。
- Go 工具链 ELF（go/gofmt/pkg/tool/linux_arm64/*）逐个 binary-sign-tool 自签（OHOS Seccomp 拦截无 .codesign 段的 ELF）。
- ldflags `-X main.appVersion=2.0.1`：上游 tag `2.0.1-linux` 的 main.go 内 `appVersion = "2.0.0"` 是上游笔误（tag 名与内部版本串脱节，AUR 同版本包也如此），注入后 `wally-cli --version` 输出真实版本号。

## 测试

- **上游测试结构实测**：12 文件全量扫描，**零 `*_test.go`**；上游无 CI 测试工作流（release-only）。`go test -v -count=1 ./...` 输出 `[no test files]` → HMBS `no_tests`（aiac/aribb24/augustus/xidle 同款零测试先例，权威标记在 test_package stdout 裸 print）。
- **test_package 消费者侧断言**（rule4 逐项定性，硬件行为无法在无设备环境验证属环境限制，用消费者侧逻辑断言覆盖）：
  1. `--version` 输出 `wally-cli v2.0.1`（版本注入验证）
  2. 无参运行打印 Usage 且退出码 2（flag.Usage 路径）
  3. `.hex` 烧录入口：无设备环境，USB 枚举等待循环会一直转（"Press the reset button"）→ 用 timeout 探测到 spinner 文案后按超时定性（环境限制：无 ZSA 键盘硬件）
  4. `.bin`（DFU）路径同上定性
  5. 非法参数（如 .txt 固件）被拒绝并提示有效扩展名（参数校验逻辑，纯逻辑可测）
  6. ELF magic + ldd 动态链接 libusb-1.0 验证（打包完整性）

## 依赖断链检查

- libusb/1.0.27：ohpcd 制品仓有 recipe + armv8 二进制制品（L0i 通过）。
- Go 工具链：配方内自举（不走 conan requires）。
- go.mod 全部 7 个模块 goproxy.cn 实测 200 可达。

## 踩坑记录

| # | 现象 | 根因 | 规避 |
|---|---|---|---|
| 1 | GUI 仓找不到 2.0.1 tag | 任务卡名 zsa-wally 对应 GUI 仓，但 2.0.1 只在 wally-cli 仓 | 形态定谳走"tag 实测"而非仓库名猜测；AUR/Codeberg/jsdelivr 三源交叉验证 |
| 2 | 本机直连 GitHub 全超时（codeload/镜像代理 rc=35/28） | 出网通道受限 | ghfast.top 间歇可用（重试第 5 次成功）；Go 模块走 goproxy.cn；Go SDK 走 aliyun 镜像 |
| 3 | `go version` permission denied | OHOS Seccomp 要求 ELF 带 .codesign 段 | binary-sign-tool 自签 go/gofmt/pkg/tool 全部 ELF |
| 4 | gousb 编译期 `pkg-config: libusb-1.0` 可能解析到系统路径 | 制品仓 .pc 的 prefix=/usr/local | .pc 改写 prefix 后注入 PKG_CONFIG_PATH + CGO_CFLAGS/LDFLAGS 双保险 |
