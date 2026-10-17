#!/usr/bin/env python3
"""Consumer tests for kytea 0.4.7.

Two distinct consumer scenarios (library + CLI both shipped upstream):

  A) kytea_lib_test — links libkytea, calls StringUtil / FullCorpusIO /
     Kytea training-prediction API through installed headers.
  B) CLI test — upstream ships TWO command-line tools:
       * `train-kytea` trains a model from a fully annotated corpus
         (`train-kytea -full <corpus> -model <abs-path>`);
       * `kytea` analyzes raw text with a trained model
         (`kytea -model <model> <raw>`).
     The test trains a tiny model, then segments raw text and checks that
     trained words and pronunciations appear in the output.
     NOTE: analysis-mode `kytea` does NOT accept training args (-full etc.);
     model paths must be ABSOLUTE on HMDFS-backed filesystems (relative
     model names fail to reopen after training).
"""

import os
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class KyteaTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("cross-build: consumer tests skipped")
            return
        # A) library consumer
        self.run(os.path.join(self.cpp.build.bindirs[0], "kytea_lib_test"),
                 env="conanrun")

        # B) CLI consumer
        bindir = self.dependencies[self.tested_reference_str].cpp_info.bindirs[0]
        kytea_bin = os.path.join(bindir, "kytea")
        train_bin = os.path.join(bindir, "train-kytea")
        self.output.info(f"CLI under test: {train_bin}, {kytea_bin}")

        workdir = os.path.abspath(os.path.join(self.build_folder, "cli-work"))
        os.makedirs(workdir, exist_ok=True)
        corpus = os.path.join(workdir, "corpus.txt")
        with open(corpus, "w", encoding="utf-8") as f:
            f.write("これ/代名詞/これ は/助詞/は 学習/名詞/がくしゅう データ/名詞/でーた\n"
                    "\n"
                    "どうぞ/副詞/どうぞ モデル/名詞/もでる を/助詞/を 学習/名詞/がくしゅう\n"
                    "京都/名詞/きょうと に/助詞/に 行/動詞/い っ/語尾/っ た/助動詞/た\n")

        # train-kytea: train a model from the fully annotated corpus.
        # The model path must be absolute (relative names fail to reopen on
        # HMDFS-backed filesystems).
        model = os.path.join(workdir, "model.bin")
        if os.path.exists(model):
            os.remove(model)
        self.run(f'"{train_bin}" -full "{corpus}" -model "{model}"',
                 env="conanrun")
        if not os.path.exists(model) or os.path.getsize(model) == 0:
            raise AssertionError("train-kytea did not produce a model file")

        # kytea: analyze raw text with the trained model.
        raw = os.path.join(workdir, "raw.txt")
        with open(raw, "w", encoding="utf-8") as f:
            f.write("どうぞモデル\n")
        out = subprocess.run([kytea_bin, "-model", model, raw],
                             capture_output=True, timeout=120)
        if out.returncode != 0:
            raise AssertionError(f"kytea analyze failed rc={out.returncode}: "
                                 f"{out.stderr.decode(errors='replace')[:400]}")
        text = out.stdout.decode("utf-8", errors="replace")
        for expected in ("どうぞ", "モデル"):
            if expected not in text:
                raise AssertionError(f"kytea output missing {expected!r}: {text[:200]!r}")
        self.output.info(f"kytea CLI analysis output: {text.strip()[:120]!r}")
