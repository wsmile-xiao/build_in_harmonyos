# graphviz 13.1.2 编译笔记（HarmonyOS PC · 标准 Conan autotools）

## 定位
- 产出 libgvc.so 等 6 个库，供链接与 dlopen。

## 关键适配
- package() 显式重签 ELF：链接后若再改字节（strip/抹 RUNPATH 等）链接期自签即失效，dlopen 报 Permission denied
- 删除 lib/*.la：其中烤死 libdir 绝对路径，会把下游 libtool 引到 //lib/ 死路
- install 后补跑：bin/dot -c（上游把该步挂在 install hook 上，而 conan 注入 DESTDIR 会让它被跳过）
- 修 configure 的 umask 077→022（HMDFS E011）
- 补转发型 .pc：pangocairo=pango,cairo、pangoft2=pango,freetype2,fontconfig（conan 只生成 recipe 声明的那一个）
- 追加链接标志：/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/lib/aarch64-linux-ohos/libclang_rt.builtins.a

## 状态
built（真机 conan create + test_package 通过）
