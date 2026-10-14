# DRAFT-12412-zsa-wally-ohos-lld-placeholder-codesign

## 问题

OHOS target（lld，aarch64-unknown-linux-ohos）上新链接出的 Go/CGO ELF 产物，
readelf 已能看到 `.codesign` 节与 `.note.ohos.ident` 节，但执行时被内核以 EPERM 拒绝：

```
$ timeout 6 ./wally-cli --version
timeout: exec ./wally-cli: Operation not permitted     # rc=126
```

而同一配方里对 Go 工具链（纯 Go 静态 ELF）的常规签名流程又能正常工作——
签名助手的"已签名"早退检查（读文件内容，子串搜索 `.codesign`）对新链接产物
**误判为已签名**，跳过了真实签名。

## 根因

- OHOS target 的 lld 在链接时自动给产物加**占位** `.codesign` 节（伴随
  `.note.ohos.ident`）。占位节带有节名字符串，因此 `b".codesign" in data`
  的子串检查会命中；但占位内容**不是有效签名**，内核装载器/Seccomp 不接受，
  exec 返回 EPERM。
- 纯 Go 静态工具链二进制（go/gofmt/pkg/tool）不走 OHOS lld target 链接，
  无 `.codesign` 节，走常规首签路径没有问题——两类产物行为不同，
  同一套 has-signature 早退逻辑只对前者安全。
- 误判的后果是静默跳签：构建绿、打包绿，到 test_package 一执行才炸
  （所有 exec 断言 rc=126）。

## 修复（force re-sign 新链接产物）

对新链接出的产物强制重签，绕过 has-signature 早退：

```sh
llvm-objcopy --remove-section .codesign <tmp-copy>
binary-sign-tool sign -selfSign 1 -inFile <tmp> -outFile <tmp.signed> \
  -signAlg SHA256withECDSA
mv <tmp.signed> <original> && chmod 755 <original>
```

has-signature 早退只保留给**复用的既有产物**（如缓存的 Go SDK 工作区）。
配方实现见 `archives/z/zsa-wally/2.0.1/conanfile.py` 的
`_sign_elf_if_ohos(path, force=False)` 与 build() 中的 `force=True` 调用。

实测定谳（zsa-wally 2.0.1，wally-cli，Go+CGO/gousb→libusb）：
- 占位 `.codesign` → exec EPERM（rc=126）
- binary-sign-tool 重签 → 正常执行（`wally-cli v2.0.1`，rc=0）

## 验证

PR #14957（任务卡 #12412）本地 conan create ohos-aarch64：rc=0，
test_package 6/6；force 修复前同一二进制全部 exec 断言 EPERM 失败。

## 兜底

若不便逐产物 force 重签，可解析 `.codesign` 节内容（readelf -x .codesign 或
手工 ELF 节表遍历）判断签名载荷是否全零/缺失；仅凭节名子串匹配在 OHOS
target 上永远不充分。
