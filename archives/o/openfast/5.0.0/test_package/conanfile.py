import os

from conan import ConanFile


class TestPkg(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _compile(self, source, output):
        """用 SDK clang 把 C 消费者编到被测包（-I/-L 全部指向被测包安装树）。"""
        pkg = self.dependencies["openfast"].package_folder
        self.run(
            '/data/service/hnp/bin/clang "{src}" -I"{pkg}/include" -L"{pkg}/lib" '
            '-lopenfastlib -lm -o "{out}"'.format(
                src=os.path.join(self.source_folder, source),
                pkg=pkg,
                out=os.path.join(self.build_folder, output),
            ),
            env="conanbuild",
        )
        if not os.path.isfile(os.path.join(self.build_folder, output)):
            raise Exception("test binary was not produced: {}".format(output))

    def build(self):
        # smoke：库级初始化/释放链路；abi：dlopen(RTLD_NOW) 交付面契约
        self._compile("smoke.c", "smoke")
        self._compile("abi.c", "abi")

    def _package_libdir(self):
        for _ref, dep in self.dependencies.items():
            if dep.ref.name == "openfast" and dep.package_folder:
                return os.path.join(dep.package_folder, "lib")
        raise Exception("openfast package_folder was not found")

    def test(self):
        pkg = self.dependencies["openfast"].package_folder
        ld_paths = [os.path.join(pkg, "lib")]
        if "openblas" in self.dependencies:
            ld_paths.append(os.path.join(self.dependencies["openblas"].package_folder, "lib"))
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(ld_paths)

        # 1) 版本冒烟：被测包的 openfast 可执行（banner 含 OpenFAST-v5.0.0 与编译器/精度信息）
        self.run('"{pkg}/bin/openfast" -v'.format(pkg=pkg))
        # 2) 库级冒烟：FAST_AllocateTurbines + FAST_DeallocateTurbines
        self.run('"{build}/smoke"'.format(build=self.build_folder))
        # 3) 交付面契约：按绝对路径 dlopen 被测包 libopenfastlib.so 并 dlsym C 接口符号
        self.run(
            'OPENFAST_PACKAGE_LIBDIR="{libdir}" "{build}/abi"'.format(
                libdir=self._package_libdir(), build=self.build_folder),
            cwd=self.build_folder,
        )
        self.output.info("OpenFAST test_package passed: openfast -v + smoke(3) + abi(5)")
