import os

from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS CI 上 test() 的 python3 经 AppSpawn 以 app uid 运行（如
        # 20020101），HMDFS 按目录继承属主并裁剪 other 权限位（755→750），
        # 直接 dlopen 包内 .so（属主=构建 uid 20001006）会被 mmap PROT_EXEC
        # 拒绝（EACCES）。探针把主库+依赖库复制到 app 私有 TMPDIR
        # （/data/storage/el2/base/cache，属主=探针）再 dlopen 副本，
        # 属主正确即可加载 —— 见 test_kysdk_coreai_speech.py 注释。
        dep = self.dependencies["libkysdk-coreai-speech"]
        lib_dir = os.path.join(dep.package_folder, "lib")
        libs = [
            name for name in sorted(os.listdir(lib_dir))
            if name.startswith("libkysdk-coreai-speech.so") and name.count(".so") == 1
        ]
        if not libs:
            raise SystemExit(f"FAIL: libkysdk-coreai-speech.so not found in {lib_dir}")
        probe_lib = os.path.join(lib_dir, libs[0])
        self.run(f"python3 test_kysdk_coreai_speech.py {probe_lib}", env="conanrun")
