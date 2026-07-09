#!/bin/sh
#
# Bad-data tests for semodule_package in the modular policy packaging pipeline.
# Covers packaging path edge cases (-m/-f) and documents deferred rejection of bad
# .mod.fc content (enforced later by sefcontext_compile).
# Unreadable -m/-f cases skip when run as root; CI runs this script as non-root.
#

set -u

# Prefer an absolute script dir, but keep a relative dirname when cd fails.
# Non-root CI can inherit the repo as CWD without being able to traverse
# /home/runner/work/...; relative paths from that CWD still work.
BASEDIR=$(dirname -- "$0")
ABS_BASEDIR=$(CDPATH= cd -- "${BASEDIR}" 2>/dev/null && pwd) || ABS_BASEDIR=
if [ -n "${ABS_BASEDIR}" ]; then
	BASEDIR="${ABS_BASEDIR}"
fi
FIXTURES="${BASEDIR}/fixtures"
if [ ! -d "${FIXTURES}" ]; then
	echo "FAIL: cannot resolve fixtures directory (\$0=$0 BASEDIR=${BASEDIR})" >&2
	exit 1
fi
OUTDIR=$(mktemp -d "${TMPDIR:-/tmp}/semodule-package-bad-data.XXXXXX")
PASS=0
FAIL=0

CHECKMODULE=${CHECKMODULE:-checkmodule}
# Modular TE for MCS/MLS builds (checkmodule -M -m).
CHECKMODULE_MOD_FLAGS=${CHECKMODULE_MOD_FLAGS:--M -m}
SEMODULE_PACKAGE=${SEMODULE_PACKAGE:-semodule_package}

GOOD_TE="${FIXTURES}/modules/good.te"
GOOD_MOD="${OUTDIR}/test_good.mod"

cleanup() {
	rm -rf "${OUTDIR}"
}
trap cleanup EXIT

die() {
	echo "FAIL: $*" >&2
	FAIL=$((FAIL + 1))
}

pass() {
	echo "==== $*"
	PASS=$((PASS + 1))
	echo ""
}

build_good_mod() {
	echo "==== Setup: build control module ${GOOD_MOD} from good.te"
	rm -f "${GOOD_MOD}"

	set +e
	# shellcheck disable=SC2086
	"${CHECKMODULE}" ${CHECKMODULE_MOD_FLAGS} -o "${GOOD_MOD}" "${GOOD_TE}" \
		2>"${OUTDIR}/build_good.err"
	rc=$?
	set -e

	if [ "${rc}" -ne 0 ]; then
		echo "FAIL: could not build control module from ${GOOD_TE}" >&2
		cat "${OUTDIR}/build_good.err" >&2
		exit 1
	fi
	if [ ! -s "${GOOD_MOD}" ]; then
		echo "FAIL: ${GOOD_MOD} is empty" >&2
		exit 1
	fi
	echo ""
}

expect_package_pass() {
	desc="$1"
	outname="$2"
	shift 2

	outpp="${OUTDIR}/${outname}.pp"
	stderr="${OUTDIR}/${outname}.err"

	echo "==== POSITIVE (expect semodule_package success): ${desc}"
	rm -f "${outpp}"

	set +e
	"${SEMODULE_PACKAGE}" -o "${outpp}" "$@" 2>"${stderr}"
	rc=$?
	set -e

	if [ "${rc}" -ne 0 ]; then
		echo "stderr:" >&2
		cat "${stderr}" >&2
		die "${desc}: expected exit 0, got rc=${rc}"
		return 0
	fi
	if [ ! -s "${outpp}" ]; then
		die "${desc}: expected non-empty ${outpp}"
		return 0
	fi

	pass "${desc} (exit 0, .pp created)"
}

expect_package_pass_deferred() {
	desc="$1"
	outname="$2"
	shift 2

	outpp="${OUTDIR}/${outname}.pp"
	stderr="${OUTDIR}/${outname}.err"

	echo "==== DOCUMENT (semodule_package accepts input; validate in sefcontext_compile): ${desc}"
	rm -f "${outpp}"

	set +e
	"${SEMODULE_PACKAGE}" -o "${outpp}" "$@" 2>"${stderr}"
	rc=$?
	set -e

	if [ "${rc}" -ne 0 ]; then
		echo "stderr:" >&2
		cat "${stderr}" >&2
		die "${desc}: expected exit 0 at packaging stage, got rc=${rc}"
		return 0
	fi
	if [ ! -s "${outpp}" ]; then
		die "${desc}: expected non-empty ${outpp} at packaging stage"
		return 0
	fi

	pass "${desc} (packaging exit 0; labeling validation deferred to sefcontext_compile)"
}

expect_package_fail() {
	desc="$1"
	pattern="$2"
	outname="$3"
	shift 3

	outpp="${OUTDIR}/${outname}.pp"
	stderr="${OUTDIR}/${outname}.err"

	echo "==== NEGATIVE (expect semodule_package failure): ${desc}"
	rm -f "${outpp}"

	set +e
	"${SEMODULE_PACKAGE}" -o "${outpp}" "$@" 2>"${stderr}"
	rc=$?
	set -e

	if [ "${rc}" -eq 0 ]; then
		die "${desc}: expected non-zero exit, got rc=0"
		return 0
	fi
	if [ -f "${outpp}" ]; then
		die "${desc}: did not expect output ${outpp}"
		return 0
	fi
	if ! grep -Eq "${pattern}" "${stderr}"; then
		echo "FAIL: stderr did not match /${pattern}/" >&2
		cat "${stderr}" >&2
		FAIL=$((FAIL + 1))
		return 0
	fi

	pass "${desc} (rejected as expected, rc=${rc})"
}

expect_package_fail_unreadable() {
	desc="unreadable -m file"
	mod="${OUTDIR}/unreadable.mod"
	outpp="${OUTDIR}/unreadable.pp"
	stderr="${OUTDIR}/unreadable.err"

	echo "==== NEGATIVE (expect semodule_package failure): ${desc}"
	if [ "$(id -u)" -eq 0 ]; then
		echo "SKIP: root can read mode 000 files; unreadable check is non-root only"
		PASS=$((PASS + 1))
		echo ""
		return 0
	fi

	rm -f "${outpp}"
	cp "${GOOD_MOD}" "${mod}"
	chmod 000 "${mod}"

	set +e
	"${SEMODULE_PACKAGE}" -o "${outpp}" -m "${mod}" 2>"${stderr}"
	rc=$?
	set -e

	if [ "${rc}" -eq 0 ]; then
		die "${desc}: expected non-zero exit, got rc=0"
		return 0
	fi
	if [ -f "${outpp}" ]; then
		die "${desc}: did not expect output ${outpp}"
		return 0
	fi
	if ! grep -Eq 'Permission denied|Could not open|Failed to open' "${stderr}"; then
		echo "FAIL: stderr did not mention permission or open failure" >&2
		cat "${stderr}" >&2
		FAIL=$((FAIL + 1))
		return 0
	fi

	pass "${desc} (rejected as expected, rc=${rc})"
}

expect_package_fail_unreadable_fc() {
	desc="unreadable -f file"
	fc="${OUTDIR}/unreadable.mod.fc"
	outpp="${OUTDIR}/unreadable_fc.pp"
	stderr="${OUTDIR}/unreadable_fc.err"

	echo "==== NEGATIVE (expect semodule_package failure): ${desc}"
	if [ "$(id -u)" -eq 0 ]; then
		echo "SKIP: root can read mode 000 files; unreadable check is non-root only"
		PASS=$((PASS + 1))
		echo ""
		return 0
	fi

	rm -f "${outpp}"
	cp "${GOOD_FC}" "${fc}"
	chmod 000 "${fc}"

	set +e
	"${SEMODULE_PACKAGE}" -o "${outpp}" -m "${GOOD_MOD}" -f "${fc}" \
		2>"${stderr}"
	rc=$?
	set -e

	if [ "${rc}" -eq 0 ]; then
		die "${desc}: expected non-zero exit, got rc=0"
		return 0
	fi
	if [ -f "${outpp}" ]; then
		die "${desc}: did not expect output ${outpp}"
		return 0
	fi
	if ! grep -Eq 'Permission denied|Could not open|Failed to open' "${stderr}"; then
		echo "FAIL: stderr did not mention permission or open failure" >&2
		cat "${stderr}" >&2
		FAIL=$((FAIL + 1))
		return 0
	fi

	pass "${desc} (rejected as expected, rc=${rc})"
}

build_good_mod

# Ephemeral path fixtures for packaging path tests.
ln -sf /nonexistent/test_good.mod "${OUTDIR}/broken_symlink.mod"
ln -sf /nonexistent/test_good.mod.fc "${OUTDIR}/broken_symlink.mod.fc"
printf '' > "${OUTDIR}/empty.mod.fc"

# NUL byte inside path column (packaging accepts; sefcontext_compile rejects).
printf '/bin/foo\x00bar\t--\tsystem_u:object_r:test_good_exec_t:s0\n' \
	> "${OUTDIR}/nul_bytes.mod.fc"

GOOD_FC="${FIXTURES}/file_contexts/good.mod.fc"

# --- semodule_package input paths ---
expect_package_pass \
	"control good .mod without file contexts" \
	good_mod \
	-m "${GOOD_MOD}"

expect_package_pass \
	"control good .mod with good .mod.fc" \
	good_mod_fc \
	-m "${GOOD_MOD}" -f "${GOOD_FC}"

expect_package_fail \
	"missing -m path" \
	"Could not open|Failed to open" \
	missing_mod \
	-m "${OUTDIR}/does_not_exist.mod"

expect_package_fail \
	"missing -f path" \
	"Failed to open|Could not open" \
	missing_fc \
	-m "${GOOD_MOD}" -f "${OUTDIR}/does_not_exist.mod.fc"

expect_package_fail \
	"directory instead of -m file" \
	"Error while reading policy module|Could not open" \
	directory_mod \
	-m "${BASEDIR}"

expect_package_fail \
	"broken symlink for -m" \
	"Could not open|Failed to open|No such file" \
	symlink_mod \
	-m "${OUTDIR}/broken_symlink.mod"

expect_package_fail_unreadable

expect_package_fail \
	"empty -m path argument" \
	"Could not open|Failed to open" \
	empty_mod \
	-m ""

expect_package_fail \
	"directory instead of -f file" \
	"Permission denied|Failed to mmap|Failed to open|Could not open" \
	directory_fc \
	-m "${GOOD_MOD}" -f "${BASEDIR}"

expect_package_fail \
	"broken symlink for -f" \
	"Could not open|Failed to open|No such file" \
	symlink_fc \
	-m "${GOOD_MOD}" -f "${OUTDIR}/broken_symlink.mod.fc"

expect_package_fail_unreadable_fc

expect_package_fail \
	"empty -f path argument" \
	"Could not open|Failed to open" \
	empty_fc_arg \
	-m "${GOOD_MOD}" -f ""

# --- bad .mod.fc at packaging time ---
expect_package_pass_deferred \
	"invalid SELinux context in .mod.fc" \
	bad_context \
	-m "${GOOD_MOD}" -f "${FIXTURES}/file_contexts/bad_context.mod.fc"

expect_package_pass_deferred \
	"wrong field count in .mod.fc" \
	bad_fields \
	-m "${GOOD_MOD}" -f "${FIXTURES}/file_contexts/bad_fields.mod.fc"

expect_package_pass_deferred \
	"NUL byte in .mod.fc path field" \
	nul_bytes \
	-m "${GOOD_MOD}" -f "${OUTDIR}/nul_bytes.mod.fc"

expect_package_pass_deferred \
	"empty .mod.fc file" \
	empty_fc \
	-m "${GOOD_MOD}" -f "${OUTDIR}/empty.mod.fc"

echo "========================================"
echo "Results: ${PASS} passed, ${FAIL} failed"
if [ "${FAIL}" -ne 0 ]; then
	exit 1
fi
exit 0
