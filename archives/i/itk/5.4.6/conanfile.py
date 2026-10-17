#!/usr/bin/env python3
"""Conan recipe for ITK 5.4.6."""
import base64
import binascii
import hashlib
import json
import os
import re
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    collect_libs,
    copy,
    export_conandata_patches,
    get,
    rmdir,
)


_EXTERNAL_DATA_MANIFEST_SHA256 = (
    "ad3197d166788b0c791e82d9c574afdd7dc739841c23649f3012952361af22bf"
)
_EXTERNAL_DATA_SOURCE_MANIFEST_SHA256 = (
    "ff80a5000f30422f8301e528214e9709c0aae3524bb3576a64f7c3d34376ff4e"
)
_EXTERNAL_DATA_BASE64_LINE_WIDTH = 76


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _is_path_link(path):
    return path.is_symlink() or (
        hasattr(path, "is_junction") and path.is_junction()
    )


def _validated_external_data_manifest(manifest_path):
    if (
        not manifest_path.is_file()
        or _is_path_link(manifest_path)
    ):
        raise ConanInvalidConfiguration(
            f"ITK ExternalData manifest is missing: {manifest_path}"
        )
    if _sha256(manifest_path) != _EXTERNAL_DATA_MANIFEST_SHA256:
        raise ConanInvalidConfiguration(
            f"ITK ExternalData manifest hash mismatch: {manifest_path}"
        )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ConanInvalidConfiguration(
            f"cannot read ITK ExternalData manifest {manifest_path}: {error}"
        ) from error
    if (
        set(manifest) != {
            "schema",
            "source_manifest_sha256",
            "object_count",
            "upstream_test_count",
            "objects",
        }
        or manifest.get("schema") != "itk-5.4.6-conan-externaldata-store-v1"
        or manifest.get("source_manifest_sha256")
        != _EXTERNAL_DATA_SOURCE_MANIFEST_SHA256
        or manifest.get("object_count") != 14
        or manifest.get("upstream_test_count") != 618
        or not isinstance(manifest.get("objects"), list)
        or len(manifest["objects"]) != 14
    ):
        raise ConanInvalidConfiguration(
            f"ITK ExternalData manifest schema is invalid: {manifest_path}"
        )

    expected_items = {}
    for item in manifest["objects"]:
        if not isinstance(item, dict) or set(item) != {"path", "bytes", "sha256"}:
            raise ConanInvalidConfiguration(
                f"ITK ExternalData object entry is invalid: {manifest_path}"
            )
        relative = item["path"]
        if (
            not isinstance(relative, str)
            or not re.fullmatch(r"CID/bafkrei[a-z2-7]{52}", relative)
            or not isinstance(item["bytes"], int)
            or isinstance(item["bytes"], bool)
            or item["bytes"] <= 0
            or not isinstance(item["sha256"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"])
        ):
            raise ConanInvalidConfiguration(
                f"ITK ExternalData object identity is invalid: {relative!r}"
            )
        if relative in expected_items:
            raise ConanInvalidConfiguration(
                f"ITK ExternalData object entry is duplicated: {relative}"
            )
        expected_items[relative] = item
    return expected_items


def _validated_external_data_store(path):
    requested_store = Path(path).expanduser()
    object_store = requested_store.resolve()
    manifest_path = object_store.parent / "MANIFEST.json"
    if not requested_store.is_dir() or _is_path_link(requested_store):
        raise ConanInvalidConfiguration(
            f"ITK ExternalData store is missing: {object_store}"
        )
    expected_items = _validated_external_data_manifest(manifest_path)

    expected_files = set()
    for relative, item in expected_items.items():
        object_path = object_store / Path(*relative.split("/"))
        try:
            object_path.resolve().relative_to(object_store)
        except ValueError as error:
            raise ConanInvalidConfiguration(
                f"ITK ExternalData object escapes its store: {relative}"
            ) from error
        if (
            not object_path.is_file()
            or _is_path_link(object_path)
            or object_path.stat().st_size != item["bytes"]
            or _sha256(object_path) != item["sha256"]
        ):
            raise ConanInvalidConfiguration(
                f"ITK ExternalData object identity mismatch: {relative}"
            )
        expected_files.add(relative)

    actual_files = set()
    for candidate in object_store.rglob("*"):
        if _is_path_link(candidate):
            raise ConanInvalidConfiguration(
                f"ITK ExternalData store contains a link: {candidate}"
            )
        if candidate.is_file():
            actual_files.add(candidate.relative_to(object_store).as_posix())
    if actual_files != expected_files:
        raise ConanInvalidConfiguration(
            f"ITK ExternalData store contains missing or extra objects: {object_store}"
        )
    return object_store


def _canonical_base64(payload):
    encoded = base64.b64encode(payload)
    lines = [
        encoded[offset : offset + _EXTERNAL_DATA_BASE64_LINE_WIDTH]
        for offset in range(0, len(encoded), _EXTERNAL_DATA_BASE64_LINE_WIDTH)
    ]
    return b"\n".join(lines) + b"\n"


def _export_external_data_store(recipe_root, export_root):
    manifest_path = recipe_root / "MANIFEST.json"
    encoded_store = recipe_root / "Encoded"
    object_store = export_root / "Objects"
    expected_items = _validated_external_data_manifest(manifest_path)
    export_root.mkdir(parents=True, exist_ok=True)
    exported_manifest = export_root / "MANIFEST.json"
    if _is_path_link(exported_manifest):
        raise ConanInvalidConfiguration(
            f"ITK ExternalData exported manifest is a link: {exported_manifest}"
        )
    exported_manifest.write_bytes(manifest_path.read_bytes())
    if _sha256(exported_manifest) != _EXTERNAL_DATA_MANIFEST_SHA256:
        raise ConanInvalidConfiguration(
            f"ITK ExternalData exported manifest hash mismatch: {exported_manifest}"
        )
    if not encoded_store.is_dir() or _is_path_link(encoded_store):
        raise ConanInvalidConfiguration(
            f"ITK ExternalData encoded store is missing: {encoded_store}"
        )

    expected_encoded_files = {f"{relative}.b64" for relative in expected_items}
    actual_encoded_files = set()
    for candidate in encoded_store.rglob("*"):
        if _is_path_link(candidate):
            raise ConanInvalidConfiguration(
                f"ITK ExternalData encoded store contains a link: {candidate}"
            )
        if candidate.is_file():
            actual_encoded_files.add(candidate.relative_to(encoded_store).as_posix())
    if actual_encoded_files != expected_encoded_files:
        raise ConanInvalidConfiguration(
            "ITK ExternalData encoded store contains missing or extra objects: "
            f"{encoded_store}"
        )

    for relative, item in expected_items.items():
        encoded_path = encoded_store / Path(*f"{relative}.b64".split("/"))
        try:
            encoded_path.resolve().relative_to(encoded_store.resolve())
        except ValueError as error:
            raise ConanInvalidConfiguration(
                f"ITK ExternalData encoded object escapes its store: {relative}"
            ) from error
        try:
            encoded = encoded_path.read_bytes()
            payload = base64.b64decode(b"".join(encoded.splitlines()), validate=True)
        except (OSError, binascii.Error, ValueError) as error:
            raise ConanInvalidConfiguration(
                f"cannot decode ITK ExternalData object {relative}: {error}"
            ) from error
        if (
            encoded != _canonical_base64(payload)
            or len(payload) != item["bytes"]
            or hashlib.sha256(payload).hexdigest() != item["sha256"]
        ):
            raise ConanInvalidConfiguration(
                f"ITK ExternalData encoded object identity mismatch: {relative}"
            )

        object_path = object_store / Path(*relative.split("/"))
        object_path.parent.mkdir(parents=True, exist_ok=True)
        object_path.write_bytes(payload)
        if (
            object_path.stat().st_size != item["bytes"]
            or _sha256(object_path) != item["sha256"]
        ):
            raise ConanInvalidConfiguration(
                f"ITK ExternalData exported object identity mismatch: {relative}"
            )


def _validated_itk_memory_size(value):
    if value is None:
        return None
    if not re.fullmatch(r"[1-9][0-9]*", value):
        raise ConanInvalidConfiguration(
            "ITK_COMPUTER_MEMORY_SIZE must be an unsigned decimal integer"
        )
    memory_size = int(value)
    if not 5 <= memory_size <= 1024:
        raise ConanInvalidConfiguration(
            "ITK_COMPUTER_MEMORY_SIZE must be between 5 and 1024 GiB"
        )
    return memory_size


def _itk_memory_size_from_meminfo(path=Path("/proc/meminfo")):
    try:
        lines = path.read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeError) as error:
        raise ConanInvalidConfiguration(
            f"cannot read ITK memory source {path}: {error}"
        ) from error

    matches = [line.split() for line in lines if line.startswith("MemTotal:")]
    if (
        len(matches) != 1
        or len(matches[0]) != 3
        or matches[0][0] != "MemTotal:"
        or not re.fullmatch(r"[1-9][0-9]*", matches[0][1])
        or matches[0][2] != "kB"
    ):
        raise ConanInvalidConfiguration(
            f"{path} must contain exactly one 'MemTotal: <integer> kB' field"
        )

    total_kib = int(matches[0][1])
    if not 5 * 1024 * 1024 <= total_kib <= 1280 * 1024 * 1024:
        raise ConanInvalidConfiguration(
            f"MemTotal must be between 5 and 1280 GiB, got {total_kib} kB"
        )
    total_mib = total_kib // 1024
    return _validated_itk_memory_size(str((total_mib * 80) // (1024 * 100)))


class ItkConan(ConanFile):
    name = "itk"
    version = "5.4.6"
    description = "Insight Toolkit image analysis library"
    license = "Apache-2.0"
    homepage = "https://itk.org/"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("ITK 5.4.6 supports POSIX targets")

    def export_sources(self):
        export_conandata_patches(self)
        object_store = os.path.join(self.export_sources_folder, "test-data", "Objects")
        rmdir(self, object_store)
        _export_external_data_store(
            Path(self.recipe_folder) / "test-data",
            Path(self.export_sources_folder) / "test-data",
        )

    def layout(self):
        cmake_layout(self, build_folder="b")

    def source(self):
        source = dict(self.conan_data["sources"])
        source_archive = os.getenv("ITK_SOURCE_ARCHIVE")
        if source_archive:
            archive_path = Path(source_archive).expanduser().resolve()
            source["url"] = archive_path.as_uri()
            source["filename"] = archive_path.name
        get(self, **source, strip_root=True)

        kwstyle_source = dict(self.conan_data["kwstyle_source"])
        kwstyle_archive = os.getenv("ITK_KWSTYLE_SOURCE_ARCHIVE")
        if kwstyle_archive:
            archive_path = Path(kwstyle_archive).expanduser().resolve()
            kwstyle_source["url"] = archive_path.as_uri()
            kwstyle_source["filename"] = archive_path.name
        get(
            self,
            **kwstyle_source,
            destination=os.path.join(self.source_folder, "_kwstyle"),
            strip_root=True,
        )

    def generate(self):
        run_upstream_tests = can_run(self)
        external_data_store = None
        if run_upstream_tests:
            external_data_store = os.getenv("ITK_EXTERNALDATA_OBJECT_STORE")
            if not external_data_store:
                external_data_store = os.path.join(
                    self.source_folder, "test-data", "Objects"
                )
        memory_size = _validated_itk_memory_size(
            os.getenv("ITK_COMPUTER_MEMORY_SIZE")
        )
        if self.settings.os == "OHOS" and run_upstream_tests and memory_size is None:
            memory_size = _itk_memory_size_from_meminfo()
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.cache_variables["BUILD_TESTING"] = run_upstream_tests
        tc.cache_variables["BUILD_EXAMPLES"] = False
        tc.cache_variables["BUILD_DOCUMENTATION"] = False
        tc.cache_variables["ITK_BUILD_DEFAULT_MODULES"] = False
        tc.cache_variables["Module_ITKCommon"] = True
        tc.cache_variables["Module_ITKGoogleTest"] = run_upstream_tests
        tc.cache_variables["ITK_FORBID_DOWNLOADS"] = True
        tc.cache_variables["ITK_USE_CLANG_FORMAT"] = False
        tc.cache_variables["ITK_KWSTYLE_SOURCE_DIR"] = os.path.join(
            self.source_folder, "_kwstyle"
        )
        if memory_size is not None:
            tc.cache_variables["ITK_COMPUTER_MEMORY_SIZE"] = str(memory_size)
        if external_data_store:
            store_path = _validated_external_data_store(external_data_store)
            tc.cache_variables["ExternalData_OBJECT_STORES"] = str(store_path)
            tc.cache_variables["ExternalData_NO_SYMLINKS"] = True
        tc.cache_variables["ITK_USE_GPU"] = False
        tc.cache_variables["ITK_USE_SYSTEM_LIBRARIES"] = False
        tc.cache_variables["ITK_WRAP_PYTHON"] = False
        if self.settings.os == "OHOS":
            # OHOS exposes the required math functions without a separate libm.
            tc.cache_variables["NIFTI_SYSTEM_MATH_LIB"] = ""
        if "fPIC" in self.options:
            tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(
                self.options.fPIC
            )
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])
        if can_run(self):
            cmake.ctest(cli_args=["--output-on-failure", "-j1"])

    def package(self):
        CMake(self).install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake", "ITK-5.4", "__pycache__"))

    def package_info(self):
        self.cpp_info.libs = collect_libs(self)
        # ITK installs its own ITKConfig.cmake. Reuse it so consumers keep the
        # upstream module variables and avoid a generated CMakeDeps shadow file.
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.set_property("cmake_find_mode", "none")
