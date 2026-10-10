from conan import ConanFile
from conan.tools.files import get, copy
import os


class LeafletGeometryUtilConan(ConanFile):
    name = "leaflet-geometryutil"
    version = "0.4.0"
    description = "Leaflet utility functions on geometries"
    license = "BSD-3-Clause"
    url = "https://github.com/makinacorpus/Leaflet.GeometryUtil"
    homepage = "https://makinacorpus.github.io/Leaflet.GeometryUtil/"
    topics = ("leaflet", "gis", "geometry", "javascript")
    package_type = "header-library"
    exports_sources = "conandata.yml"
    no_copy_source = True

    def source(self):
        get(self, **self.conan_data["sources"][0], strip_root=True)

    def package_id(self):
        # 纯 JS 资源包，与平台架构无关
        self.info.clear()

    def package(self):
        node_modules = os.path.join(self.package_folder, "lib",
                                    "node_modules", "leaflet-geometryutil")

        # 主 JS 文件：src 指向 dist/ 目录，keep_path=False 避免叠加 dist/dist
        copy(self, "leaflet.geometryutil.js",
             src=os.path.join(self.source_folder, "dist"),
             dst=os.path.join(node_modules, "dist"),
             keep_path=False)

        # package.json（Node.js 入口解析）
        copy(self, "package.json",
             src=self.source_folder,
             dst=node_modules,
             keep_path=False)

        # README
        copy(self, "README.md",
             src=self.source_folder,
             dst=node_modules,
             keep_path=False)

        # License
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        node_modules = os.path.join(self.package_folder, "lib", "node_modules")
        self.buildenv_info.prepend_path("NODE_PATH", node_modules)
        self.runenv_info.prepend_path("NODE_PATH", node_modules)
        # 纯 JS 包，无 C/C++ 信息
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
