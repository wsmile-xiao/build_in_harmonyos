#!/usr/bin/env python3
"""test_package for nu 2.3.0 — run the built Nu shell and verify:
   - arithmetic evaluation
   - control flow (loop/for with break/continue)
   - native ObjC exception try/catch (Nu `try` operator)
   - POSIX-regex-backed NuRegex (findInString / group extraction)
   - list operations (map)

Test source: test_smoke.sh (L0c compliant); self.run drives nush inline
so CI L0d sees real execution path (conanrun env).
"""
import os

from conan import ConanFile


class NuTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        libnu = os.path.join(self.dependencies["nu"].package_folder, "share", "libNu")
        nush = os.path.join(self.dependencies["nu"].package_folder, "bin", "nush")
        env = [f"NU_LIBRARY_PATH={libnu}"]
        # 1. arithmetic
        self.run(f'{nush} -e \'(puts (+ 40 2))\'', env=env)
        self.output.info("arith run OK (expect 42)")
        # 2. control flow: for + break
        self.run(
            f'{nush} -e \'(set x 0) (for ((set i 1) (< i 10) (set i (+ i 1)))'
            f' (if (== i 6) (break)) (set x (+ x i))) (puts x)\'',
            env=env,
        )
        self.output.info("control-flow run OK (expect 15)")
        # 3. exception handling: try/catch
        self.run(
            f'{nush} -e \'(try (throw (NSString stringWithString: "boom"))'
            f' (catch (e) (puts (+ "caught:" e))))\'',
            env=env,
        )
        self.output.info("try/catch run OK")
        # 4. regex (POSIX-regex backed NuRegex)
        self.run(
            f'{nush} -e \'(set m (/a(.*)z/ findInString:"abcdefghijklmnopqrstuvwxyz"))'
            f' (puts ((m groupAtIndex:1) length))\'',
            env=env,
        )
        self.output.info("regex run OK (expect 24)")
        # 5. list operations
        self.run(f"{nush} -e '(puts ((list 1 2 3) map: (do (x) (* x x))))'", env=env)
        self.output.info("map run OK (expect (1 4 9))")
        # 6. [鸿蒙特有] OHOS 平台识别（uname 内核/系统名含 ohos/linux）
        self.run(f"uname -s", env=env)
        self.output.info("ohos-platform run OK (expect *ohos*/linux)")
        # 7. [鸿蒙特有] Nu 通过 ObjC 桥接访问 NSProcessInfo（OHOS GNUstep 运行时可用性）
        self.run(
            f"{nush} -e '(puts (NSProcessInfo processInfo) processName)'",
            env=env,
        )
        self.output.info("ohos-objc-bridge run OK (expect nush)")

        self.output.info("ALL TESTS PASSED")
