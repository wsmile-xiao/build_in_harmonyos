set -euo pipefail
script_folder="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "echo Restoring environment" > "$script_folder/deactivate_conanbuildenv-armv8.sh"
for v in ac_cv_target ac_cv_host ac_cv_build SHELL CONFIG_SHELL
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

export ac_cv_target="aarch64-unknown-linux-gnu"
export ac_cv_host="aarch64-unknown-linux-gnu"
export ac_cv_build="aarch64-unknown-linux-gnu"
export SHELL="/data/service/hnp/bin/bash"
export CONFIG_SHELL="/data/service/hnp/bin/bash"