# DRAFT-libfbclient-5.0.4-client-only-make-install-broken

## 可复现症状与稳定错误签名

configure / make 全部成功后执行 `make install`：

```
(cd ../gen/Firebird-5.0.4.1812-0-linux-arm64; FIREBIRD= FIREBIRD_LOCK= ./install.sh)
/bin/sh: ./install.sh: inaccessible or not found
make[2]: *** [Makefile.install:128: install] Error 127
make[1]: *** [Makefile:790: install] Error 2
make: *** [Makefile:6: install] Error 2
```

稳定签名：`./install.sh: inaccessible or not found` + `Makefile.install:<n>: install ... Error 127`。

## 根因

`builds/install/arch-specific/linux/Makefile.in`（生成 `gen/Makefile.install`）：

```make
buildTarDir: buildImageDir
	mkdir -p $(GEN_ROOT)/$(TarDir)
ifeq ($(CLIENT_ONLY_FLG),N)
	cp -r $(GEN_ROOT)/install/install.sh $(GEN_ROOT)/$(TarDir)   # ← 仅非裁剪模式拷贝
	chmod a+x $(GEN_ROOT)/$(TarDir)/*.sh
endif
	(cd $(GEN_ROOT)/$(TarDir); $(TAR) -C ../buildroot -czf buildroot.tar.gz . )

install: buildTarDir
	(cd $(GEN_ROOT)/$(TarDir); FIREBIRD= FIREBIRD_LOCK= ./install.sh)  # ← 无条件执行
	cp -r $(GEN_ROOT)/$(DebugDir)/* /                                  # ← 向 / 复制调试符号
```

`--enable-client-only` 时 `install.sh` 永远不会被打进 `$(TarDir)`，但 `install:` 仍然要求执行它
→ 必然 Error 127。补充风险：该目标末行会把调试符号复制到文件系统根 `/`，在 CI 与沙箱上即使
能跑也不可接受；另外 Firebird 的 `make install` 并不使用 `DESTDIR` 语义（实测它直接写入
configure 时的 `--prefix`），因此标准 `Autotools.install()`（DESTDIR=package_folder）也不成立。

## 修复：打包上游安装镜像，而不是 make install

```python
def package(self):
    # 上游 make 阶段已经产出完整安装镜像（与 distro recipe 使用的是同一个目录）
    image = os.path.join(self.build_folder, "gen", "Release", "firebird")
    copy(self, "libfbclient.so*", src=os.path.join(image, "lib"),
         dst=os.path.join(self.package_folder, "lib"))
    copy(self, "*", src=os.path.join(image, "include"),
         dst=os.path.join(self.package_folder, "include"))
    copy(self, "libChaCha.so", src=os.path.join(image, "plugins"),
         dst=os.path.join(self.package_folder, "plugins"))
    copy(self, "plugins.conf", src=image, dst=self.package_folder)
    copy(self, "*", src=os.path.join(image, "tzdata"),
         dst=os.path.join(self.package_folder, "tzdata"))
```

镜像本身由 `make` 阶段（`makeInstallImage.sh`）生成，因此这不是"手写打包脚本"，而是沿用上游
自己的安装布局；制品仍由 `conan create` + CI `upload.sh` 产出与分发。

## 适用范围

- 上游提供"裁剪/子集构建"开关（Firebird `--enable-client-only`、MySQL `WITHOUT_SERVER=ON` 等），
  而 `install` 目标沿用了完整树的假设；
- 上游 `install` 目标依赖只有在完整构建里才生成的脚本/文件；
- 上游 `install` 目标会写文件系统根或系统目录（`cp ... /`、`/etc/init.d` 等）。

## 证据

- 实测：`make install` → `Makefile.install:128` Error 127（`./install.sh` 不存在于 kit 目录）；
  `ls gen/Firebird-5.0.4.1812-0-linux-arm64/` 仅有 `buildroot.tar.gz` 与 `manifest.txt`。
- 改用镜像打包后：`conan create` 成功，包内包含 lib/libfbclient.so{,.2,.5.0.4}（5.3MB）、include/（63 个头文件）、plugins/libChaCha.so、plugins.conf、tzdata/*.res 与 licenses/IDPL.txt，
  `conan-verify` G0–G4 + L2/L4/L5 全 PASS，W3 本地 CI `Pass rate 100% (1/1)`。
- Distro 口径：Debian `firebird5.0` 的 `debian/rules` 写明 `override_dh_auto_install: true`
  并在 `override_dh_auto_build` 里 `cp -a ./gen/Release/firebird debian/firebird-image`。
