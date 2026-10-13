"""Official libzippp 6.1 tag, complete assertion-active upstream suite."""
import glob,json,os,re,shutil,subprocess
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake,CMakeDeps,CMakeToolchain,cmake_layout
from conan.tools.files import apply_conandata_patches,copy,export_conandata_patches,get

class LibzipppConan(ConanFile):
    name = 'libzippp'
    version = '6.1-1.9.2'
    description='C++ wrapper for libzip'
    license='BSD-3-Clause'
    homepage='https://github.com/ctabin/libzippp'
    settings='os','arch','compiler','build_type'
    package_type='library'
    options={'shared':[True,False],'fPIC':[True,False]}
    default_options={'shared':True,'fPIC':True}
    def export_sources(self):export_conandata_patches(self)
    def config_options(self):
        if self.settings.os=='Windows':self.options.rm_safe('fPIC')
    def configure(self):
        if self.options.shared:self.options.rm_safe('fPIC')
    def requirements(self):
        self.requires('libzip/1.11.4')
        self.requires('zlib/1.3.1.1')
    def validate(self):
        if self.settings.os!='OHOS' or not self.options.shared:
            raise ConanInvalidConfiguration('This adaptation validates native OHOS shared libraries')
        if not can_run(self):
            raise ConanInvalidConfiguration('A native build is required to execute the full upstream suite')
    def layout(self):cmake_layout(self,src_folder='.')
    def source(self):get(self,**self.conan_data['sources'][str(self.version)],strip_root=True)
    def generate(self):
        CMakeDeps(self).generate()
        tc=CMakeToolchain(self)
        # The native CMake has no HarmonyOS platform module. Use ELF/Unix
        # library rules; Conan identity and the actual runtime remain OHOS.
        tc.blocks['generic_system'].values['cmake_system_name']='Linux'
        tc.variables['BUILD_SHARED_LIBS']=bool(self.options.shared)
        tc.variables['LIBZIPPP_BUILD_TESTS']=True
        tc.variables['LIBZIPPP_ENABLE_ENCRYPTION']=False
        tc.variables['LIBZIPPP_GNUINSTALLDIRS']=True
        tc.variables['CMAKE_INSTALL_LIBDIR']='lib'
        libzip=self.dependencies['libzip'];zlib=self.dependencies['zlib']
        tc.variables['LIBZIP_INCLUDE_DIR']=libzip.cpp_info.includedirs[0]
        tc.variables['LIBZIP_LIBRARY']=os.path.join(libzip.cpp_info.libdirs[0],'libzip.so')
        tc.variables['_libzip_pkgcfg']=os.path.join(libzip.cpp_info.libdirs[0],'pkgconfig','libzip.pc')
        tc.variables['ZLIB_INCLUDE_DIR']=zlib.cpp_info.includedirs[0]
        tc.variables['ZLIB_LIBRARY']=os.path.join(zlib.cpp_info.libdirs[0],'libz.a')
        # Native runtime closure must be bound at configure, not ambient LD_LIBRARY_PATH.
        tc.variables['CMAKE_BUILD_RPATH']=[libzip.cpp_info.libdirs[0]]
        tc.generate()
    def _sign(self,path):
        if self.settings.os!='OHOS':return
        signer=shutil.which('binary-sign-tool')
        if not signer:raise ConanInvalidConfiguration('Native binary-sign-tool required')
        pending=path+'.signed'
        original_mode=os.stat(path).st_mode & 0o777
        subprocess.run([signer,'sign','-inFile',path,'-outFile',pending,'-selfSign','1'],check=True)
        os.chmod(pending,original_mode)
        os.replace(pending,path)
    def build(self):
        apply_conandata_patches(self)
        cmake=CMake(self);cmake.configure();cmake.build()
        binaries=glob.glob(os.path.join(self.build_folder,'libzippp.so*'))
        tests=glob.glob(os.path.join(self.build_folder,'libzippp_*_test'))
        if len(tests)!=1:raise ConanInvalidConfiguration('Full upstream test binary missing or ambiguous')
        for path in binaries+tests:
            if os.path.isfile(path) and not os.path.islink(path):self._sign(path)
        # CTest is the official entry. Runtime output verifies all 24 function identities.
        log=os.path.join(self.build_folder,'upstream-ctest-output.txt')
        cmake.ctest(cli_args=['--test-dir',self.build_folder,'--verbose','--output-log',log])
        with open(log,encoding='utf-8') as f:text=f.read()
        actual=[int(x) for x in re.findall(r'Running test (\d+)\.\.\.',text)]
        if actual!=list(range(1,25)):raise ConanInvalidConfiguration('Upstream runtime inventory is incomplete')
        self.output.info('UPSTREAM_TEST_PASS=24/24; CTEST_CONTAINERS=1/1')
    def package(self):
        CMake(self).install()
        # Installation may rewrite RPATH after the build-side signature.
        for path in glob.glob(os.path.join(self.package_folder,'lib','libzippp.so*')):
            if not os.path.islink(path):self._sign(path)
        copy(self,'LICENCE',src=self.source_folder,dst=os.path.join(self.package_folder,'licenses'))
    def package_info(self):
        self.cpp_info.libs=['zippp' if self.options.shared else 'zippp_static']
        self.cpp_info.includedirs=['include/libzippp']
        self.cpp_info.set_property('cmake_file_name','libzippp')
        self.cpp_info.set_property('cmake_target_name','libzippp::libzippp')
        self.cpp_info.set_property('pkg_config_name','libzippp')
