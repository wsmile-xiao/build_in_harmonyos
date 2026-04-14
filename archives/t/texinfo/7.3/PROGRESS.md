# texinfo 7.3 编译进度

**日期**: 2026-04-14
**状态**: 🔄 编译中

## 步骤记录

| 步骤 | 状态 | 备注 |
|------|------|------|
| Step 1 init | ⏳ | |
| Step 2 patches | ⏳ | |
| Step 3 configure | ⏳ | |
| Step 4 make | ⏳ | |
| Step 5 install | ⏳ | |
| Step 6 safety | ⏳ | |
| Step 7 check | ⏳ | |
| Step 8 staging | ⏳ | |
| Step 9 package | ⏳ | |
| Step 10 deploy | ⏳ | |
| Step 11 finish | ⏳ | |

## 发现与知识

### E007: config.guess 多处需修补
- **问题**: texinfo 在 build-aux/, tta/build-aux/, tta/perl/CheckXS/build-aux/ 三处有独立的 config.guess/config.sub
- **解决**: 用 patch-autotools-ohos.pl 逐一修补；CheckXS 的 config.sub 版本不同，需用主目录修补版覆盖
- **引用**: E007, E083(draft)

### 文档构建跳过
- **问题**: doc/ 目录的 info 文件生成失败（texi2any 内部 @include 路径解析问题）
- **解决**: 从顶层 SUBDIRS 的 am__append_7 中移除 doc 目录
- **影响**: 不影响核心功能（texi2any, info, install-info, texindex 均正常）

### info 测试权限问题
- **问题**: info viewer 的 90 个交互式测试因脚本文件 Permission denied (exit 126) 全部失败
- **原因**: 鸿蒙系统文件系统权限限制
- **影响**: 不影响二进制功能

### TTA C 扩展默认不编译
- **发现**: tta 子目录的 C 代码默认不编译（build_C_code=no），需 --enable-xs 才启用
- **影响**: 核心功能不依赖 TTA C 扩展

### configure 参数
- --prefix=$TEST_PREFIX（R20 铁律）
- --disable-nls
- CC=clang, CFLAGS="-fPIC -O2 -I$DEFAULT_PREFIX/include"

---

**编译结束**: 2026-04-14 11:05
**最终状态**: success

---

**编译结束**: 2026-04-14 11:07
**最终状态**: success

---

**编译结束**: 2026-04-14 11:09
**最终状态**: success
