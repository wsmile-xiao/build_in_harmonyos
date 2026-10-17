script_folder="/storage/Users/currentUser/.opendesk/apps/skills/resources/openharmony-compile-agent/archives/s/scdoc/1.11.0/test_package"
echo "echo Restoring environment" > "$script_folder/deactivate_conanbuildenv-release-armv8.sh"
for v in SHELL CONFIG_SHELL
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

export SHELL="/data/service/hnp/bin/bash"
export CONFIG_SHELL="/data/service/hnp/bin/bash"