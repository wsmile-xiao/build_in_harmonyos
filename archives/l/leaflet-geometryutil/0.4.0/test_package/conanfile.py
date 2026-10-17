import os
from conan import ConanFile
from conan.tools.build import can_run


class LeafletGeometryUtilTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        base = os.path.join(pkg_folder, "lib", "node_modules", "leaflet-geometryutil")
        js_file = os.path.join(base, "dist", "leaflet.geometryutil.js")
        pkg_json = os.path.join(base, "package.json")

        assert os.path.exists(js_file), f"Missing: {js_file}"
        assert os.path.exists(pkg_json), f"Missing: {pkg_json}"
        with open(js_file) as f:
            assert "L.GeometryUtil" in f.read(), "L.GeometryUtil not found"

        # test.sh 只接受一个参数：leaflet.geometryutil.js 路径
        self.run(f'sh test.sh "{js_file}"', env="conanrun")
