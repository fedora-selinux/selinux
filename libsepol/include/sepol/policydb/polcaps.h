#ifndef _SEPOL_POLICYDB_POLCAPS_H_
#define _SEPOL_POLICYDB_POLCAPS_H_

#ifdef __cplusplus
extern "C" {
#endif

/* Policy capabilities */
enum {
	POLICYDB_CAP_NETPEER,
	POLICYDB_CAP_OPENPERM,
	POLICYDB_CAP_EXTSOCKCLASS,
	POLICYDB_CAP_ALWAYSNETWORK,
	POLICYDB_CAP_CGROUPSECLABEL,
	POLICYDB_CAP_NNP_NOSUID_TRANSITION,
	POLICYDB_CAP_GENFS_SECLABEL_SYMLINKS,
	POLICYDB_CAP_IOCTL_SKIP_CLOEXEC,
	POLICYDB_CAP_USERSPACE_INITIAL_CONTEXT,
	__POLICYDB_CAP_MAX
};
#define POLICYDB_CAP_MAX (__POLICYDB_CAP_MAX - 1)

/* legacy constants from past to preserve backward compatibility */
enum {
    POLICYDB_CAPABILITY_NETPEER =                 POLICYDB_CAP_NETPEER,
    POLICYDB_CAPABILITY_OPENPERM =                POLICYDB_CAP_OPENPERM,
    POLICYDB_CAPABILITY_EXTSOCKCLASS =            POLICYDB_CAP_EXTSOCKCLASS,
    POLICYDB_CAPABILITY_ALWAYSNETWORK =           POLICYDB_CAP_ALWAYSNETWORK,
    POLICYDB_CAPABILITY_CGROUPSECLABEL =          POLICYDB_CAP_CGROUPSECLABEL,
    POLICYDB_CAPABILITY_NNP_NOSUID_TRANSITION =   POLICYDB_CAP_NNP_NOSUID_TRANSITION,
    POLICYDB_CAPABILITY_GENFS_SECLABEL_SYMLINKS = POLICYDB_CAP_GENFS_SECLABEL_SYMLINKS,
    POLICYDB_CAPABILITY_IOCTL_SKIP_CLOEXEC =      POLICYDB_CAP_IOCTL_SKIP_CLOEXEC,
    __POLICYDB_CAPABILITY_MAX =                 __POLICYDB_CAP_MAX
};
#define POLICYDB_CAPABILITY_MAX (__POLICYDB_CAP_MAX - 1)

/* Convert a capability name to number. */
extern int sepol_polcap_getnum(const char *name);

/* Convert a capability number to name. */
extern const char *sepol_polcap_getname(unsigned int capnum);

#ifdef __cplusplus
}
#endif

#endif /* _SEPOL_POLICYDB_POLCAPS_H_ */
