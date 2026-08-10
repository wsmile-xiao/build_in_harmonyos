script_folder="/storage/Users/currentUser/opt/ai-worker/repo/archives/l/lua-resty-http/0.17.2/test_package"
echo "echo Restoring environment" > "$script_folder/deactivate_conanbuildenv-armv8.sh"
for v in SHELL CONFIG_SHELL
do
   is_defined="true"
   value=$(printenv $v) || is_defined="" || true
   if [ -n "$value" ] || [ -n "$is_defined" ]
   then
       echo export "$v='$value'" >> "$script_folder/deactivate_conanbuildenv-armv8.sh"
   else
       echo unset $v >> "$script_folder/deactivate_conanbuildenv-armv8.sh"
   fi
done

export SHELL="/data/service/hnp/bin/bash"
export CONFIG_SHELL="/data/service/hnp/bin/bash"