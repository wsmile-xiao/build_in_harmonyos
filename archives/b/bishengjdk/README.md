# BiSheng JDK 17.0.13 for HarmonyOS (Self-Signed)

鸿蒙系统专用 BiSheng JDK 17.0.13，所有 ELF 文件已用 `binary-sign-tool -selfSign 1` 统一签名。
可直接使用 `System.load()` / `System.loadLibrary()` 加载自签名的 JNI 库。

## 打包

| 文件 | 大小 | 说明 |
|------|------|------|
| `bishengjdk17-ohos-aarch64-runtime.tar.gz` | 156MB | 运行时版（无 src.zip/jmods/demo/man/legal） |
| `bishengjdk17-ohos-aarch64.tar.gz` | 286MB | 完整版 |

## 安装

```bash
tar xzf bishengjdk17-ohos-aarch64-runtime.tar.gz -C $HOME/usr/local/
export JAVA_HOME=$HOME/usr/local/bishengjdk17
```

## 为什么需要这个

原始系统 JDK (`/data/service/hnp/bishengjdk17*`) 使用系统级签名，会拒绝加载自签名的 JNI 库（`System.load` 报 `Permission denied`）。拷贝并全量自签名后，JVM 与 JNI 库使用同一签名体系，加载正常。

详见知识图谱 E083。
