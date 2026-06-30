script_folder="/storage/Users/currentUser/.opendesk/apps/skills/resources/openharmony-compile-agent/archives/u/uptimed/0.4.7/test_package"
echo "echo Restoring environment" > "$script_folder/deactivate_conanbuildenv-release-armv8.sh"
for v in ACLOCAL_PATH LD_LIBRARY_PATH PKG_CONFIG_PATH PATH CXX CC CONFIG_SHELL
do
    is_defined="true"
    value=$(printenv $v) || is_defined="" || true
    if [ -n "$value" ] || [ -n "$is_defined" ]
    then
        echo export "$v='$value'" >> "$script_folder/deactivate_conanbuildenv-release-armv8.sh"
    else
        echo unset $v >> "$script_folder/deactivate_conanbuildenv-release-armv8.sh"
    fi
done


export ACLOCAL_PATH="/storage/Users/currentUser/usr/local/share/aclocal"
export LD_LIBRARY_PATH="/storage/Users/currentUser/usr/local/lib"
export PKG_CONFIG_PATH="/storage/Users/currentUser/usr/local/lib/pkgconfig:/storage/Users/currentUser/usr/local/share/pkgconfig"
export PATH="/storage/Users/currentUser/usr/local/bin:/data/service/hnp/bin:/usr/bin:/bin"
export CXX="/data/service/hnp/bin/clang++"
export CC="/data/service/hnp/bin/clang"
export CONFIG_SHELL="/data/service/hnp/bin/bash"