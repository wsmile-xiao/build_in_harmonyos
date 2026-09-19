from conan import ConanFile
import os
import shutil


class VecmathTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    @staticmethod
    def _find_java_home():
        candidates = [
            os.environ.get("JAVA_HOME", ""),
            os.path.expanduser("~/bishengjdk17"),
            os.path.expanduser("~/usr/local/bishengjdk17"),
            "/storage/Users/currentUser/usr/local/bishengjdk17",
            "/storage/Users/currentUser/usr/local/bishengjdk",
        ]
        java = shutil.which("java")
        if java:
            candidates.append(os.path.dirname(os.path.dirname(os.path.realpath(java))))
        for candidate in candidates:
            if candidate:
                home = os.path.abspath(os.path.expanduser(candidate))
                if os.path.isfile(os.path.join(home, "bin", "java")) and os.path.isfile(
                    os.path.join(home, "bin", "javac")
                ):
                    return home
        return None

    def test(self):
        pkg = self.dependencies["vecmath"].package_folder
        jar_path = os.path.join(pkg, "libexec", "vecmath-1.5.2.jar")
        self.output.info(f"Testing package in: {pkg}")
        if not os.path.isfile(jar_path):
            raise Exception(f"vecmath JAR not found at {jar_path}")

        java_home = self._find_java_home()
        if not java_home:
            raise Exception(
                "JAVA_HOME not set and no JDK found. Set JAVA_HOME to a JDK 17+."
            )

        script = os.path.join(self.source_folder, "test.sh")
        self.run(
            f'bash "{script}" "{jar_path}" "{java_home}"',
            env="conanrun",
        )

        # HMBS_UPSTREAM_TEST_RESULT — 上游测试审计证据（hmbs 硬门禁）。
        # 结论：vecmath 1.5.2 上游发行版（Maven Central sources jar）仅含
        # javax/vecmath/*.java 源码与资源，无任何测试代码（无 tests/、无
        # build 脚本接入测试），详见 test_package/MANIFEST.yml upstream_test_audit。
        # discovered/executed=0，status=no_tests。test.sh 已输出该标记，
        # 此处再冗余 print 一行（xeyes/xidle 同款双保险，覆盖 cache-hit）。
        print(
            'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests",'
            '"framework":"none",'
            '"command":"n/a (vecmath 1.5.2 release contains no test suite)",'
            '"discovered":0,"executed":0,"passed":0,"failed":0,'
            '"skipped":0,'
            '"reason":"vecmath 1.5.2 上游发行版（Maven Central sources jar）'
            '经审计不含任何测试代码；功能验证由 test_package 对打包 JAR 做真实 API 断言"}',
            flush=True,
        )
