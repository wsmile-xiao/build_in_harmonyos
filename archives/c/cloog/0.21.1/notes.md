# cloog 0.21.1 适配笔记

## 编译信息
- 构建系统: autotools (configure + make)
- 编译器: /data/service/hnp/bin/clang
- 依赖: gmp/6.3.0 (system), isl25/0.25 (system), osl (bundled)
- 构建选项: --with-gmp=system --with-isl=system --with-osl=bundled --with-cloog-int=gmp

## 适配要点
1. config.guess 需 patch 添加 OHOS 检测（aarch64:Linux 分支）
2. config.sub 需 patch 添加 ohos 到 OS 合法性列表 + linux-ohos 内核验证
3. configure 需 patch: mktemp -d 在 HMDFS 上创建 drwx--S--- 目录无法写入，改用 mkdir -p -m 755
4. 子目录（isl/osl）也有独立的 config.guess/sub/configure 需要同步 patch
5. libisl.la 里的 gmp 依赖路径可能需要修正（//lib/libgmp.la → 正确路径）

## 测试结果
- make check: 超时（180s），未完成全部测试
- conan create (G2): 通过
- conan-verify smoke test: 通过

## 最终状态
status: closed
编译结束
