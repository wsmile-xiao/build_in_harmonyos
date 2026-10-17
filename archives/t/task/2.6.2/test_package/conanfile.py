#!/usr/bin/env python3
"""Conan test_package for task 2.6.2 (Taskwarrior).

Tests the installed binary by running `task --version` and basic commands.
"""
import os
import tempfile

from conan import ConanFile


class TaskTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_dir = self.dependencies["task"].cpp_info.bindirs[0]
        task_bin = os.path.join(bin_dir, "task")
        # Test 1: version check
        self.run(f'"{task_bin}" --version', env="conanrun")
        # Test 2: basic add/list/done workflow with pre-created config
        with tempfile.TemporaryDirectory() as tmpdir:
            testdata = os.path.join(tmpdir, "data")
            testrc = os.path.join(tmpdir, "taskrc")
            os.makedirs(testdata, exist_ok=True)
            # Create a minimal taskrc
            with open(testrc, "w") as f:
                f.write("data.location=" + testdata + "\n")
            # Set environment variables for task
            os.environ["TASKDATA"] = testdata
            os.environ["TASKRC"] = testrc
            # Add a task (non-interactive)
            self.run(f'"{task_bin}" add "Conan test task"')
            # List tasks
            self.run(f'"{task_bin}" list')
            # Mark done
            self.run(f'"{task_bin}" 1 done')
            # List again (returns exit 1 when no matches - that's expected)
            self.run(f'"{task_bin}" list', ignore_errors=True)
            # Clean up env
            del os.environ["TASKDATA"]
            del os.environ["TASKRC"]
