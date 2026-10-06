#!/bin/bash
# PASS if MLS is permissive and ausearch finds no AVC/SELINUX_ERR since boot.
set -eu

[ "$(getenforce)" = Permissive ] && [ "$(sestatus | awk -F': *' '/Loaded policy name/ {print $2}')" = mls ] \
    || { echo "FAIL: not permissive MLS" >&2; exit 1; }

# --input-logs: do not consume stdin (tmt may attach a pipe).
# ausearch: 0=matches, 1=none, >=2=error
set +e
ausearch -m avc,user_avc,selinux_err,user_selinux_err -i --input-logs -ts boot
rc=$?
set -e
[ "$rc" -eq 1 ] || { echo "FAIL: AVC/SELINUX_ERR or ausearch rc=$rc" >&2; exit 1; }
echo PASS
