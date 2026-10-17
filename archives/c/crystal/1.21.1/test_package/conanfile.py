import os

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        pkg = self.dependencies["crystal"].package_folder
        crystal = os.path.join(pkg, "bin", "crystal")
        shards = os.path.join(pkg, "bin", "shards")
        for p in (crystal, shards):
            if not os.path.isfile(p):
                raise Exception("missing installed binary: %s" % p)

        # 1) 编译器真实可运行（补签后才会成功；未签名时 execve 报 EACCES）
        self.run('"%s" --version' % crystal, env="conanrun")
        self.run('"%s" --version' % shards, env="conanrun")

        # 2) 真编译一个程序并运行（R34：空壳测试无法通过）
        src = os.path.join(self.build_folder, "hello.cr")
        with open(src, "w", encoding="utf-8") as fh:
            fh.write('puts "crystal-hello-ok"\n')
        out = os.path.join(self.build_folder, "hello")
        self.run('"%s" build "%s" -o "%s" '
                 '--target aarch64-unknown-linux-musl' % (crystal, src, out),
                 env="conanrun")
        # 产物同样需要签名才能在 OHOS 上执行
        signed = out + ".signed"
        self.run('binary-sign-tool sign -inFile "%s" -outFile "%s" -selfSign 1'
                 % (out, signed), env="conanrun")
        os.replace(signed, out)
        os.chmod(out, 0o755)
        self.run('"%s"' % out, env="conanrun")
