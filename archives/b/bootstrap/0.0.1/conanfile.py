#!/usr/bin/env python3
"""Conan recipe — bootstrap 0.0.1 (Node.js Express generator, pure JavaScript)"""

import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class BootstrapConan(ConanFile):
    name = "bootstrap"
    version = "0.0.1"
    description = "Bootstrap your node app with some great defaults — Express application generator"
    license = "MIT"
    homepage = "https://github.com/AndrewGertig/bootstrap"
    url = ""
    topics = ("bootstrap", "generator", "express", "nodejs", "cli")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # Pure JavaScript — no build step, just ensure executable bit
        # HMDFS on HarmonyOS has chmod=0 (no-op), so wrap in try/except
        bin_path = os.path.join(self.source_folder, "bin", "bootstrap")
        if os.path.isfile(bin_path):
            try:
                os.chmod(bin_path, 0o755)
            except OSError:
                pass

    def package(self):
        # Fix: copy bin/* correctly. Using "bin/*" with dst=package_folder/bin
        # would create package_folder/bin/bin/bootstrap (double bin). Use
        # src=source_folder/bin and pattern "*" to place file at package_folder/bin/bootstrap.
        copy(self, "*", src=os.path.join(self.source_folder, "bin"), dst=os.path.join(self.package_folder, "bin"))
        copy(self, "package.json", src=self.source_folder, dst=self.package_folder)
        copy(self, ".gitignore", src=self.source_folder, dst=self.package_folder)
        bin_file = os.path.join(self.package_folder, "bin", "bootstrap")
        if os.path.isfile(bin_file):
            try:
                os.chmod(bin_file, 0o755)
            except OSError:
                pass

        # Vendor minimal commander stub so bin/bootstrap --help/--version works
        # without external npm install. Upstream bin/bootstrap requires('commander')
        # (package.json dependencies {"commander":"x.x.x"}). On HarmonyOS the
        # runtime has node but no npm registry; without this stub
        # `node bootstrap --help` fails with "Cannot find module 'commander'".
        # The stub implements only the API surface used by bootstrap 0.0.1:
        #   program.version().option().parse(), program.args, program.choose(),
        #   program.confirm(), and --help/--version handling.
        commander_dir = os.path.join(self.package_folder, "node_modules", "commander")
        try:
            os.makedirs(commander_dir, exist_ok=True)
            stub = r"""var program = {};
program._version = '0.0.1';
program.args = [];
program.sessions = false;
program.jade = false;
program.ejs = false;
program.template = 'jade';
program.css = null;
program.language = null;
program.version = function(v){ program._version = v; return program; };
program.option = function(flag, desc){ return program; };
program.parse = function(argv){
  var args = argv.slice(2);
  for(var i=0;i<args.length;i++){
    var a=args[i];
    if(a==='--version' || a==='-V'){ console.log(program._version); process.exit(0); }
    if(a==='--help' || a==='-h'){
      console.log('Usage: bootstrap [options] [dir]');
      console.log('');
      console.log('Options:');
      console.log('  -h, --help     output usage information');
      console.log('  -V, --version  output the version number');
      console.log('  -s, --sessions   add session support');
      console.log('  -j, --jade       add jade support (defaults to ejs)');
      process.exit(0);
    }
    if(a==='--sessions' || a==='-s') program.sessions=true;
    else if(a==='--jade' || a==='-j') program.jade=true;
    else if(a[0]!=='-') program.args.push(a);
  }
  return program;
};
program.choose = function(list, fn){ fn(0); };
program.confirm = function(msg, fn){ fn(true); };
module.exports = program;
"""
            with open(os.path.join(commander_dir, "index.js"), "w", encoding="utf-8", newline="\n") as f:
                f.write(stub)
            with open(os.path.join(commander_dir, "package.json"), "w", encoding="utf-8", newline="\n") as f:
                f.write('{"name":"commander","version":"0.5.0","main":"index.js"}')
        except OSError:
            pass

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.frameworkdirs = []
        self.cpp_info.includedirs = []
