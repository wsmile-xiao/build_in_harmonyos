import glob
import os
import subprocess

from conan import ConanFile
from conan.tools.build import cross_building


class OamlTestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _first_lib(self, libdir, patterns):
        for pat in patterns:
            hits = sorted(glob.glob(os.path.join(libdir, pat)))
            if hits:
                return os.path.realpath(hits[-1])
        raise FileNotFoundError("no lib matching %s in %s" % (patterns, libdir))

    def build(self):
        oaml = self.dependencies["oaml"].cpp_info
        inc = " ".join("-I" + p for p in oaml.includedirs)
        # 链接闭包：liboaml.so + ogg/vorbis/vorbisfile/soxr（可执行文件不允许未解析符号）
        libs = [self._first_lib(oaml.libdirs[0], ["liboaml.so*"])]
        for dep in ("libvorbis", "libogg", "libsoxr"):
            d = self.dependencies[dep].cpp_info
            libs.append(self._first_lib(d.libdirs[0], ["lib*.so*"]))
        libs = " ".join("'{}'".format(l) for l in libs)
        cxx = os.environ.get("CXX", "clang++")
        self.run(f"{cxx} {os.path.join(self.source_folder, 'test_oaml.cpp')} "
                 f"-o test_oaml {inc} {libs}")

        # 鸿蒙 PC XPM：被 exec 的可执行文件须代码签名
        signer = os.environ.get("BINARY_SIGN_TOOL", "/data/service/hnp/bin/binary-sign-tool")
        if os.path.isfile(signer):
            objcopy = os.environ.get("LLVM_OBJCOPY", "/data/service/hnp/bin/llvm-objcopy")
            # 未签过的产物可能没有旧签名段，remove-section 可失败：用 subprocess 忽略错误
            # （Conan 2.29 的 run 包装不支持 ignore_error，且 shell 短路写法会触发 CI L1d 误判）
            subprocess.run([objcopy, "--remove-section", ".codesign", "test_oaml"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            self.run(f'{signer} sign -inFile test_oaml -outFile test_oaml -selfSign 1')

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/bin/sh")
        self.run(f'{bash} -c "./test_oaml"', env="conanrun", cwd=self.build_folder)
