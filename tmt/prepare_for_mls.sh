# prepare_for_mls - switch the guest from targeted to SELinux MLS.
#
# Follows "Switching the SELinux policy to MLS" in the RHEL Using SELinux
# guide: permissive + SELINUXTYPE=mls, fixfiles -F onboot, reboot, then
# enforcing and a second reboot.
#
# The MLS policy has no unconfined user. Map root to sysadm_u and enable
# ssh_sysadm_login before the first MLS boot so SSH as sysadm still works
# (needed for Testing Farm).
#
# Usage:
#   source .../prepare_for_mls.sh
#   prepare_for_mls_configure   # permissive, mls, login map, fixfiles -F onboot
#   prepare_for_mls_reboot
#   prepare_for_mls_set_enforcing
#   prepare_for_mls_reboot
#
# Or: prepare_for_mls  (configure + first reboot only)

prepare_for_mls_configure() {
    sed -i 's/^SELINUX=.*/SELINUX=permissive/' /etc/selinux/config
    sed -i 's/^SELINUXTYPE=.*/SELINUXTYPE=mls/' /etc/selinux/config
    # -N: do not reload; still running targeted until reboot.
    semanage login -N -m -s sysadm_u root
    semanage boolean -N -m --on ssh_sysadm_login
    fixfiles -F onboot
}

prepare_for_mls_set_enforcing() {
    sed -i 's/^SELINUX=.*/SELINUX=enforcing/' /etc/selinux/config
}

prepare_for_mls_reboot() {
    if ! command -v tmt-reboot >/dev/null 2>&1; then
        echo "tmt-reboot not available; cannot reboot" >&2
        exit 1
    fi
    tmt-reboot -t 1200
}

prepare_for_mls() {
    prepare_for_mls_configure
    prepare_for_mls_reboot
}
