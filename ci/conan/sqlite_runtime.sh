#!/usr/bin/zsh
# Restore the sqlite runtime needed by the OHOS Python build on each CI step.

ensure_python_sqlite_runtime() {
    local python_bin="${CI_PYTHON3_BIN:-python3}"

    if "$python_bin" -c "import sqlite3" >/dev/null 2>&1; then
        return 0
    fi

    echo "[warn] Python sqlite3 is unavailable; searching for an OHOS sqlite runtime..."

    local -a search_dirs
    search_dirs=()
    if [ -n "${CI_SQLITE_SEARCH_DIR:-}" ]; then
        if [ -d "$CI_SQLITE_SEARCH_DIR" ]; then
            search_dirs+=("$CI_SQLITE_SEARCH_DIR")
        fi
    else
        local python_base
        python_base=$("$python_bin" -c "import sys; print(sys.base_prefix)" 2>/dev/null || true)
        if [ -n "$python_base" ]; then
            local python_dir
            for python_dir in "$python_base/lib/external" "$python_base/lib" "$python_base"; do
                if [ -d "$python_dir" ]; then
                    search_dirs+=("$python_dir")
                fi
            done
        fi

        local dir
        for dir in \
            /data/service/hnp \
            /system/lib /system/lib64 /system/lib32 \
            /vendor/lib /vendor/lib64 \
            /usr/lib /usr/lib64; do
            if [ -d "$dir" ]; then
                search_dirs+=("$dir")
            fi
        done
    fi

    if [ ${#search_dirs[@]} -eq 0 ]; then
        echo "[error] No sqlite search directories are available on this Worker"
        return 1
    fi

    local sqlite_lib=""
    local pattern
    # Prefer Python-compatible SONAME variants. libsqlite.z.so is a last-resort
    # OHOS candidate and is accepted only when the import retry succeeds.
    for pattern in 'libsqlite3.so.0' 'libsqlite3.so.0.*' 'libsqlite3.so' 'libsqlite.z.so'; do
        sqlite_lib=$(find "${search_dirs[@]}" -name "$pattern" -print -quit 2>/dev/null || true)
        if [ -n "$sqlite_lib" ]; then
            break
        fi
    done

    if [ -z "$sqlite_lib" ]; then
        echo "[error] libsqlite3.so.0 or a compatible OHOS sqlite runtime was not found"
        return 1
    fi

    local sqlite_lib_dir="$(dirname "$sqlite_lib")"
    local sqlite_name="$(basename "$sqlite_lib")"
    if [ "$sqlite_name" != "libsqlite3.so.0" ]; then
        local shim_root="${CI_SQLITE_SHIM_ROOT:-${TMPDIR:-$HOME/tmp}}"
        mkdir -p "$shim_root"

        local shim_dir
        shim_dir=$(mktemp -d "$shim_root/ci-sqlite-shim.XXXXXX" 2>/dev/null || true)
        if [ -z "$shim_dir" ]; then
            echo "[error] Failed to create sqlite compatibility directory under $shim_root"
            return 1
        fi
        if ! ln -sf "$sqlite_lib" "$shim_dir/libsqlite3.so.0" 2>/dev/null; then
            echo "[warn] Symbolic links are unavailable; copying the sqlite runtime instead"
            if ! cp "$sqlite_lib" "$shim_dir/libsqlite3.so.0"; then
                echo "[error] Failed to provide $sqlite_lib as libsqlite3.so.0"
                return 1
            fi
        fi
        sqlite_lib_dir="$shim_dir"
    fi

    export LD_LIBRARY_PATH="$sqlite_lib_dir${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
    echo "[step] Retrying Python sqlite3 with LD_LIBRARY_PATH=$sqlite_lib_dir"

    if "$python_bin" -c "import sqlite3" >/dev/null 2>&1; then
        echo "[ok] Python sqlite3 runtime restored"
        return 0
    fi

    echo "[error] Python sqlite3 still cannot load after sqlite runtime recovery"
    "$python_bin" -c "import sqlite3" 2>&1 || true
    return 1
}
