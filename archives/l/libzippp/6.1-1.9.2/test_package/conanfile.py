import os,shlex,shutil,subprocess,tempfile
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake,CMakeDeps,CMakeToolchain,cmake_layout
from conan.tools.env import VirtualRunEnv

class TestLibzippp(ConanFile):
    settings='os','arch','compiler','build_type'
    test_type='explicit'
    def requirements(self):self.requires(self.tested_reference_str)
    def layout(self):cmake_layout(self)
    def generate(self):
        CMakeDeps(self).generate();VirtualRunEnv(self).generate()
        tc=CMakeToolchain(self)
        dirs=[directory for dep in self.dependencies.values() for directory in dep.cpp_info.libdirs]
        tc.variables['CMAKE_BUILD_RPATH']=dirs
        tc.generate()
    def build(self):
        cmake=CMake(self);cmake.configure();cmake.build()
        if self.settings.os=='OHOS':
            signer=shutil.which('binary-sign-tool')
            if not signer:raise RuntimeError('Native signer missing')
            path=os.path.join(self.build_folder,'libzippp_consumer')
            original_mode=os.stat(path).st_mode & 0o777
            subprocess.run([signer,'sign','-inFile',path,'-outFile',path+'.signed','-selfSign','1'],check=True)
            os.chmod(path+'.signed',original_mode)
            os.replace(path+'.signed',path)
    def test(self):
        if not can_run(self):raise RuntimeError('Native test execution required')
        library=self.dependencies['libzippp']
        if not library.options.shared:raise RuntimeError('Signed loader专项 requires the shared library build')
        executable=os.path.join(self.build_folder,'libzippp_consumer')
        parent=self.build_folder
        if self.settings.os=='OHOS' and not os.path.abspath(parent).startswith('/storage/Users/'):
            home=os.path.expanduser('~')
            if not os.path.abspath(home).startswith('/storage/Users/'):
                raise RuntimeError('A task-private HarmonyOS storage directory is required')
            parent=home
        with tempfile.TemporaryDirectory(prefix='libzippp-consumer-',dir=parent) as work:
            command=' '.join(shlex.quote(x) for x in (executable,work,library.cpp_info.libdirs[0]))
            self.run(command,env='conanrun')
            if self.settings.os=='OHOS':self.run(command+' --harmony',env='conanrun')
            if os.listdir(work):raise RuntimeError('Consumer left private ZIP files')
