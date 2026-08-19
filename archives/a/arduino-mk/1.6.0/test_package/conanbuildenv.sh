script_folder="/storage/Users/currentUser/runner002/build_in_harmonyos/archives/a/arduino-mk/1.6.0/test_package"
echo "echo Restoring environment" > "$script_folder/deactivate_conanbuildenv.sh"
for v in PATH SHELL CONFIG_SHELL
do
   is_defined="true"
   value=$(printenv $v) || is_defined="" || true
   if [ -n "$value" ] || [ -n "$is_defined" ]
   then
       echo export "$v='$value'" >> "$script_folder/deactivate_conanbuildenv.sh"
   else
       echo unset $v >> "$script_folder/deactivate_conanbuildenv.sh"
   fi
done

export PATH="/data/service/hnp/bin:/storage/Users/currentUser/usr/local/bin:${PATH}"
export SHELL="/data/service/hnp/bin/bash"
export CONFIG_SHELL="/data/service/hnp/bin/bash"