#!/bin/sh
#
# Negative / bad-data tests for checkmodule on module (.te) inputs.
# Matches the RHIVOS modular compile path: checkmodule -M -m <input> -o <module>.mod
#

set -eu

BASEDIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
NEGDIR="${BASEDIR}/negative"
CHECKMODULE="${BASEDIR}/../checkmodule"
OUTDIR=$(mktemp -d "${TMPDIR:-/tmp}/checkmodule-negative.XXXXXX")
PASS=0
FAIL=0

cleanup() {
	rm -rf "${OUTDIR}"
}
trap cleanup EXIT

mod_name_from_fixture() {
	basename "$1" .te
}

expect_pass() {
	desc="$1"
	fixture="$2"
	modname=$(mod_name_from_fixture "${fixture}")
	outmod="${OUTDIR}/${modname}.mod"
	stderr="${OUTDIR}/${modname}.err"

	echo "==== PASS expected: ${desc}"
	rm -f "${outmod}"

	set +e
	"${CHECKMODULE}" -M -m -o "${outmod}" "${NEGDIR}/${fixture}" 2>"${stderr}"
	rc=$?
	set -e

	if [ "${rc}" -ne 0 ]; then
		echo "FAIL: expected success (rc=0), got rc=${rc}" >&2
		cat "${stderr}" >&2
		FAIL=$((FAIL + 1))
		return 1
	fi
	if [ ! -s "${outmod}" ]; then
		echo "FAIL: expected non-empty ${outmod}" >&2
		FAIL=$((FAIL + 1))
		return 1
	fi

	echo "==== ${desc} success"
	PASS=$((PASS + 1))
	echo ""
}

expect_fail() {
	desc="$1"
	pattern="$2"
	shift 2

	outmod="${OUTDIR}/fail.mod"
	stderr="${OUTDIR}/fail.err"

	echo "==== FAIL expected: ${desc}"
	rm -f "${outmod}"

	set +e
	"${CHECKMODULE}" -M -m "$@" -o "${outmod}" 2>"${stderr}"
	rc=$?
	set -e

	if [ "${rc}" -eq 0 ]; then
		echo "FAIL: expected non-zero exit, got rc=0" >&2
		FAIL=$((FAIL + 1))
		return 1
	fi
	if [ -f "${outmod}" ]; then
		echo "FAIL: did not expect output module ${outmod}" >&2
		FAIL=$((FAIL + 1))
		return 1
	fi
	if ! grep -q "${pattern}" "${stderr}"; then
		echo "FAIL: stderr did not match /${pattern}/" >&2
		cat "${stderr}" >&2
		FAIL=$((FAIL + 1))
		return 1
	fi

	echo "==== ${desc} success"
	PASS=$((PASS + 1))
	echo ""
}

# Ephemeral fixtures for path-based cases.
ln -sf /nonexistent/path "${OUTDIR}/broken_symlink.te"
cat > "${OUTDIR}/unreadable.te" <<'EOF'
module unreadable 1.0;

require {
	type foo_t;
}
EOF
chmod 000 "${OUTDIR}/unreadable.te"

# Control fixture: valid module compiles and produces .mod output.
expect_pass "good_module.te" "good_module.te"

# Corrupted .te sections (PDF #2).
expect_fail "bad_syntax.te" "syntax error" "${NEGDIR}/bad_syntax.te"
expect_fail "unknown_perm.te" "permission circular_ref is not defined" "${NEGDIR}/unknown_perm.te"
expect_fail "unknown_type.te" "unknown type undeclared_t" "${NEGDIR}/unknown_type.te"
expect_fail "unknown_class.te" "unknown class not_a_class" "${NEGDIR}/unknown_class.te"
expect_fail "bad_module_line.te" "syntax error" "${NEGDIR}/bad_module_line.te"
expect_fail "bad_require.te" "syntax error" "${NEGDIR}/bad_require.te"
expect_fail "invalid_module_version.te" "syntax error" "${NEGDIR}/invalid_module_version.te"
expect_fail "dup_module.te" "syntax error" "${NEGDIR}/dup_module.te"

# Missing / bad-path .te inputs (PDF #1).
expect_fail "missing .te path" "unable to open" "${OUTDIR}/does_not_exist.te"
expect_fail "directory instead of .te file" "input in flex scanner failed" "${NEGDIR}"
expect_fail "broken symlink to .te" "unable to open" "${OUTDIR}/broken_symlink.te"
expect_fail "unreadable .te file" "Permission denied" "${OUTDIR}/unreadable.te"
expect_fail "empty .te path argument" "unable to open" ""

# CLI edge cases.
expect_fail "checkmodule with no input file" "unable to open policy.conf"
expect_fail "checkmodule -o name mismatch" "Module name good_module is different" \
	-o "${OUTDIR}/wrong_name.mod" "${NEGDIR}/good_module.te"

echo "checkmodule negative tests: ${PASS} passed, ${FAIL} failed"
if [ "${FAIL}" -ne 0 ]; then
	exit 1
fi
