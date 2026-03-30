# texinfo 7.3 编译说明

## 编译信息

- **软件名**: texinfo
- **版本**: 7.3
- **编译日期**: 2026-03-30
- **构建系统**: autotools
- **目标平台**: aarch64-unknown-linux-gnu

## 编译环境

- **编译器**: clang 15.0.4
- **操作系统**: HarmonyOS (HongMeng Kernel 1.12.0)
- **安装前缀**: /storage/Users/currentUser/usr/local

## 编译配置

```bash
./configure \
  --prefix=/storage/Users/currentUser/usr/local \
  --disable-nls \
  --build=aarch64-unknown-linux-gnu \
  --host=aarch64-unknown-linux-gnu \
  CC=clang \
  CFLAGS="-I/storage/Users/currentUser/usr/local/include" \
  LDFLAGS="-L/storage/Users/currentUser/usr/local/lib"
```

### 关键配置说明

- `--disable-nls`: 禁用 NLS（Native Language Support），因为 HarmonyOS 缺少相关库
- `--build` 和 `--host`: 设置为 aarch64-unknown-linux-gnu，确保与系统兼容

## 编译产物

- `install-info/ginstall-info` - install-info 工具 (238K)
- `tta/perl/texi2any` - texi2any 脚本 (91K)
- `util/texi2dvi` - texi2dvi 脚本 (51K)

## 功能验证

所有工具链均已验证通过：
- ✅ install-info 7.3 版本正确
- ✅ install-info 帮助信息正常
- ✅ texi2any 和 texi2dvi 脚本可执行

## 兼容性说明

- **兼容性等级**: high
- **已知问题**: 无
- **备注**: 核心功能正常，install-info 工具验证通过

## 编译备注

- texinfo 7.3 在 HarmonyOS 上使用 autotools 编译成功
- 使用 `--disable-nls` 禁用 NLS 支持（HarmonyOS 缺少相关库）
- 无需特殊补丁
- 使用 clang 编译器
- 构建系统类型为 autotools

## 参考资料

- https://www.gnu.org/software/texinfo/
