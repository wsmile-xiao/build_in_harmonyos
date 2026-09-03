from conan import ConanFile
from conan.tools.files import get
import os
import shutil
import sys


class PythonGssapiConan(ConanFile):
    name = "python-gssapi"
    version = "1.8.3"
    description = "Python GSSAPI Wrapper - Cython bindings to the GSSAPI C library"
    license = "ISC"
    homepage = "https://github.com/pythongssapi/python-gssapi"
    url = "https://github.com/pythongssapi/python-gssapi"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def requirements(self):
        self.requires("krb5/1.22.1")

    def source(self):
        get(self, **self.conan_data["sources"][self.version])
        src_subdir = os.path.join(self.source_folder, "python-gssapi-1.8.3")
        if os.path.isdir(src_subdir):
            for item in os.listdir(src_subdir):
                src_path = os.path.join(src_subdir, item)
                dst_path = os.path.join(self.source_folder, item)
                if os.path.exists(dst_path):
                    if os.path.isdir(dst_path):
                        shutil.rmtree(dst_path)
                    else:
                        os.remove(dst_path)
                shutil.move(src_path, dst_path)
            os.rmdir(src_subdir)

    def build(self):
        krb5 = self.dependencies["krb5"]
        krb5_root = krb5.package_folder
        krb5_bin = os.path.join(krb5_root, "bin")
        krb5_lib = os.path.join(krb5_root, "lib")
        krb5_include = os.path.join(krb5_root, "include")

        py_prefix = sys.prefix
        py_lib = os.path.join(py_prefix, "lib")

        compiler_execs = self.conf.get("tools.build:compiler_executables", default={})
        cc = compiler_execs.get("c", "clang")
        cxx = compiler_execs.get("cpp", "clang++")
        cc_dir = os.path.dirname(cc)

        os.environ["CC"] = cc
        os.environ["CXX"] = cxx
        os.environ["GSSAPI_KRB5CONFIG"] = os.path.join(krb5_bin, "krb5-config")
        os.environ["GSSAPI_COMPILER_ARGS"] = (
            f"-I{krb5_include} -DHAS_GSSAPI_EXT_H"
        )
        os.environ["GSSAPI_LINKER_ARGS"] = (
            f"-L{krb5_lib} -L{py_lib} "
            f"-lgssapi_krb5 -lkrb5 -lk5crypto -lcom_err"
        )
        os.environ["GSSAPI_SUPPORT_DETECT"] = "false"
        os.environ["LD_LIBRARY_PATH"] = (
            f"{krb5_lib}:{py_lib}:"
            f"{os.environ.get('LD_LIBRARY_PATH', '')}"
        )
        os.environ["PATH"] = (
            f"{cc_dir}:{krb5_bin}:"
            f"{os.environ.get('PATH', '')}"
        )

        self.run("python3 -m pip install Cython setuptools decorator")

        self.run("python3 setup.py build_ext --inplace")

    def package(self):
        gssapi_src = os.path.join(self.build_folder, "gssapi")
        gssapi_dst = os.path.join(self.package_folder, "lib", "gssapi")

        ignore_patterns = shutil.ignore_patterns(
            "*.pyx", "*.pxd", "*.c", "__pycache__",
            "tests", "build", "*.egg-info",
        )
        shutil.copytree(gssapi_src, gssapi_dst, ignore=ignore_patterns)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib"]
