import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class BibtexTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        # Get bibtex binary path from the built package
        bibtex_bin = os.path.join(self.dependencies["bibtex"].package_folder, "bin", "bibtex")

        # Test 1: version output (R34: must run the actual binary)
        self.run(f'"{bibtex_bin}" --version')

        # Test 2: process a .aux file with bibtex
        test_src = os.path.dirname(__file__)
        test_dir = os.path.join(self.build_folder, "test_data")
        os.makedirs(test_dir, exist_ok=True)

        # Copy test files from test_package source directory
        for fname in ["exampl.aux", "xampl.bib", "apalike.bst"]:
            src = os.path.join(test_src, fname)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(test_dir, fname))

        # Run bibtex on exampl.aux
        aux_src = os.path.join(test_dir, "exampl.aux")
        if os.path.exists(aux_src):
            shutil.copy2(aux_src, os.path.join(test_dir, "xexampl.aux"))
            os.environ["BIBINPUTS"] = test_dir
            os.environ["BSTINPUTS"] = test_dir
            self.run(f'cd "{test_dir}" && "{bibtex_bin}" xexampl')
            # Verify .bbl was produced
            bbl_path = os.path.join(test_dir, "xexampl.bbl")
            assert os.path.exists(bbl_path), "bibtex did not produce .bbl output"
