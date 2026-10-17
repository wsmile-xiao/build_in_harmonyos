import os

from conan import ConanFile


class PddTestConan(ConanFile):
    test_type = "explicit"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 依赖显式再声明（catkin-pkg/1.1.0、libjwt-tools/3.3.3 先例）：
        # 否则 python-dateutil/six 在 test 图里被跳过（skip trait），包文件夹为 None，
        # dateutil 将不可 import，消费者用例失去意义
        self.requires("python-dateutil/2.9.0.post0")
        self.requires("six/1.17.0")

    def test(self):
        pdd = self.dependencies["pdd"]
        pdd_bin = os.path.join(pdd.package_folder, "bin", "pdd")

        site_rel_options = (
            "lib/python3.12/site-packages",
            "lib/site-packages",
            "lib/python/site-packages",
        )

        def collect(include_self):
            found = []
            for _req, dep in self.dependencies.items():
                # items() 的 key 是 Requirement 对象，勿与 str 比较
                # （Requirement.__eq__ 会访问 other.ref 而 AttributeError）；
                # 名字一律经 dep.ref.name 取
                if not include_self and dep.ref.name == "pdd":
                    continue
                folder = getattr(dep, "package_folder", None)
                if not folder:
                    continue
                for rel in site_rel_options:
                    path = os.path.join(folder, rel)
                    if os.path.isdir(path) and path not in found:
                        found.append(path)
            return found

        # site_all：本体 + 依赖（等价 conanrun PYTHONPATH）
        # site_deps：仅依赖（模拟消费者环境——本体 site 由 launcher 自定位）
        site_all = os.pathsep.join(collect(include_self=True))
        site_deps = os.pathsep.join(collect(include_self=False))
        dateutil_site = ""
        if "python-dateutil" in self.dependencies:
            dateutil_site = os.path.join(
                self.dependencies["python-dateutil"].package_folder,
                "lib", "python3.12", "site-packages")

        script = os.path.join(os.path.dirname(__file__), "test_pdd.py")
        self.run(
            f'python3 "{script}" "{pdd_bin}" "{site_all}" "{site_deps}" "{dateutil_site}"',
            env="conanrun")
