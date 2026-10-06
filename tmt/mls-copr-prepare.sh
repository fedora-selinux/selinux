#!/bin/bash
# COPR selinux-policy-mls + prepare_for_mls. COPR_REPO required unless SKIP_COPR_INSTALL=1.
set -eo pipefail

reboot_count="${TMT_REBOOT_COUNT:-0}"

# shellcheck source=/dev/null
source "$TMT_TREE/tmt/prepare_for_mls.sh"

verify_copr_policy_set() {
    [ "$(rpm -q --qf '%{EVR}' selinux-policy-mls)" = "$(rpm -q --qf '%{EVR}' selinux-policy)" ] || {
        echo "FAIL: selinux-policy and selinux-policy-mls EVR mismatch" >&2
        exit 1
    }
    if [ -n "${COPR_SELINUX_POLICY_MLS_NVR:-}" ] && ! rpm -q selinux-policy-mls | grep -qF "${COPR_SELINUX_POLICY_MLS_NVR}"; then
        echo "FAIL: expected ${COPR_SELINUX_POLICY_MLS_NVR}" >&2
        exit 1
    fi
}

install_copr_policy_set() {
    dnf install -y 'dnf-command(copr)' || true
    dnf -y copr enable "${COPR_REPO:?set COPR_REPO}"
    local evr=${COPR_SELINUX_POLICY_MLS_NVR:-$(dnf --disablerepo='*' --enablerepo='*copr*' repoquery --latest-limit=1 --qf '%{version}-%{release}' selinux-policy-mls)}
    evr=${evr#selinux-policy-mls-}
    : "${evr:?no COPR selinux-policy-mls}"
    dnf install -y --allowerasing \
        "selinux-policy-$evr" "selinux-policy-devel-$evr" "selinux-policy-mls-$evr" \
        policycoreutils-python-utils audit
    verify_copr_policy_set
}

verify_mls_ready() {
    [ "$(getenforce)" = Enforcing ] && [ "$(sestatus | awk -F': *' '/Loaded policy name/ {print $2}')" = mls ] \
        || { echo "FAIL: not enforcing MLS" >&2; exit 1; }
    semanage login -l | grep -q 'root.*sysadm_u' \
        || { echo "FAIL: root not mapped to sysadm_u" >&2; exit 1; }
    # --input-logs: do not consume stdin (tmt may attach a pipe).
    if ausearch -m avc,user_avc -i --input-logs -ts boot 2>/dev/null | grep -Eiq 'cloud_init_t|comm="cloud-init"'; then
        echo "FAIL: cloud-init AVC denials since boot" >&2
        exit 1
    fi
}

wait_for_autorelabel() {
    local deadline=$(( $(date +%s) + 1200 ))
    while [ -e /.autorelabel ] || systemctl is-active --quiet selinux-autorelabel.service 2>/dev/null; do
        [ "$(date +%s)" -lt "$deadline" ] || { echo "FAIL: selinux-autorelabel still running after 20m" >&2; exit 1; }
        sleep 15
    done
}

finish_mls_labels() {
    time fixfiles -F restore / || { echo "FAIL: fixfiles restore failed" >&2; exit 1; }
    systemctl mask selinux-autorelabel.service
}

case "$reboot_count" in
0)
    if [ "${SKIP_COPR_INSTALL:-0}" != 1 ]; then
        install_copr_policy_set
    else
        dnf install -y policycoreutils-python-utils audit
        verify_copr_policy_set
    fi
    prepare_for_mls_configure
    prepare_for_mls_reboot
    ;;
1)
    if [ "${MLS_STAY_PERMISSIVE:-0}" = 1 ]; then
        ausearch -m avc,user_avc,selinux_err,user_selinux_err -i --input-logs -ts boot || true
        exit 0
    fi
    wait_for_autorelabel
    finish_mls_labels
    prepare_for_mls_set_enforcing
    prepare_for_mls_reboot
    ;;
*)
    verify_mls_ready
    ;;
esac
