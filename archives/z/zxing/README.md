# zxing

ZXing（"Zebra Crossing"）是 Google 维护的条码/二维码编解码库，支持 QR Code、Data Matrix、
Aztec、PDF417、UPC/EAN、Code 39/93/128、Codabar、ITF、RSS 等格式的生成与识别。
本包交付其 **`core` 模块**（Maven 坐标 `com.google.zxing:core`），即库本体。

## OHOS 适配

- **纯 JVM 包**：产物是单个 JAR（291 个 class，字节码 major=52），不含任何 C/C++ 源文件，
  不使用 OpenHarmony C/C++ 交叉编译器，也没有 ELF/动态链接面。
- 使用经 SHA-256 校验的 BiSheng JDK 17.0.13（ohos-aarch64）与 Apache Maven 3.6.3 构建，
  两者均为构建期工具，不进入包。
- 构建与运行注入 `-Dos.name=Linux`：OpenHarmony PC 的 JVM 自报 `os.name=harmonyos`，
  Maven、Surefire 与 `java.awt` 会把它判为不支持平台。
- **零补丁**：上游源码逐字节未改，只把构建入口放在 `core/` 目录内（避开该发布 tag 上
  `zxingorg` 模块的 `3.5.3-SNAPSHOT` 父 POM 残留）。
- 静态交付 `lib/zxing-core-3.5.3.jar`，另装 `licenses/{LICENSE,NOTICE}` 与
  `share/doc/zxing/README.md`。

## 用法

```java
// 编码
BitMatrix matrix = new MultiFormatWriter().encode(text, BarcodeFormat.QR_CODE, 320, 320);
// 解码
RGBLuminanceSource source = new RGBLuminanceSource(w, h, pixels);
Result result = new MultiFormatReader().decode(new BinaryBitmap(new HybridBinarizer(source)));
```

JVM 消费者把 `lib/zxing-core-3.5.3.jar` 放进 classpath 即可；该 JAR 带
`Automatic-Module-Name: com.google.zxing`，可直接作为 JPMS 具名模块使用。

## 验证

- 设备原生 `mvn clean verify`（cwd=`core/`）：`BUILD SUCCESS`，rc=0。
- 上游 Surefire：**131 个测试类 / 542 个用例，542/542 通过，0 失败 / 0 错误 / 0 跳过**。
- `test_package`：对打包后的 JAR 做 12 条产物检查 + 16 条消费者断言
  （QR 编码→解码往返 3 组、核心类加载、枚举与 QR 版本常量），合计 29 项，全部通过。

## 上游

- 源码：https://github.com/zxing/zxing
- 版本：3.5.3（tag `zxing-3.5.3`）
- 许可证：Apache-2.0
