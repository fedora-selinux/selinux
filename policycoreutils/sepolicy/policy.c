/**
 *  @file
 *  Python bindings to search SELinux Policy rules.
 *
 *  @author Dan Walsh  <dwalsh@redhat.com>
 *  Copyright (C) 2012-2013 Red Hat, INC
 *
 *  Sections copied from setools package
 *  @author Frank Mayer  mayerf@tresys.com
 *  @author Jeremy A. Mowery jmowery@tresys.com
 *  @author Paul Rosenfeld  prosenfeld@tresys.com
 *  Copyright (C) 2003-2008 Tresys Technology, LLC
 *
 *  This program is free software; you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation; either version 2 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program; if not, write to the Free Software
 *  Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
 */

#include "Python.h"

struct module_state {
    PyObject *error;
};

#if PY_MAJOR_VERSION >= 3
#define GETSTATE(m) ((struct module_state*)PyModule_GetState(m))
#else
#define GETSTATE(m) (&_state)
static struct module_state _state;
#endif

#ifdef UNUSED
#elif defined(__GNUC__)
# define UNUSED(x) UNUSED_ ## x __attribute__((unused))
#elif defined(__LCLINT__)
# define UNUSED(x) /*@unused@*/ x
#else
# define UNUSED(x) x
#endif

#include "policy.h"
apol_policy_t *global_policy = NULL;

PyObject *wrap_policy(PyObject *UNUSED(self), PyObject *args){
    const char *policy_file;
    apol_vector_t *mod_paths = NULL;
    apol_policy_path_type_e path_type = APOL_POLICY_PATH_TYPE_MONOLITHIC;
    apol_policy_path_t *pol_path = NULL;

    if (!PyArg_ParseTuple(args, "z", &policy_file))
	    return NULL;

    if (global_policy)
	    apol_policy_destroy(&global_policy);

    int policy_load_options = 0;

    pol_path = apol_policy_path_create(path_type, policy_file, mod_paths);
    if (!pol_path) {
	    apol_vector_destroy(&mod_paths);
	    PyErr_SetString(PyExc_RuntimeError,strerror(ENOMEM));
	    return NULL;
    }
    apol_vector_destroy(&mod_paths);
    
    global_policy = apol_policy_create_from_policy_path(pol_path, policy_load_options, NULL, NULL);
    apol_policy_path_destroy(&pol_path);
    if (!global_policy) {
	    PyErr_SetString(PyExc_RuntimeError,strerror(errno));
	    return NULL;
    }

    return Py_None;
}

static PyMethodDef policy_methods[] = {
	{"policy", (PyCFunction) wrap_policy, METH_VARARGS,
		 "Initialize SELinux policy for use with search and info"},
	{"info", (PyCFunction) wrap_info, METH_VARARGS,
		 "Return SELinux policy info about types, attributes, roles, users"},
	{"search", (PyCFunction) wrap_search, METH_VARARGS,
	"Search SELinux Policy for allow, neverallow, auditallow, dontaudit and transition records"},
	{NULL, NULL, 0, NULL}	/* sentinel */
};

#if PY_MAJOR_VERSION >= 3

static int policy_traverse(PyObject *m, visitproc visit, void *arg) {
    Py_VISIT(GETSTATE(m)->error);
    return 0;
}

static int policy_clear(PyObject *m) {
    Py_CLEAR(GETSTATE(m)->error);
    return 0;
}


static struct PyModuleDef moduledef = {
	PyModuleDef_HEAD_INIT,
	"policy",
	NULL,
	sizeof(struct module_state),
	policy_methods,
	NULL,
	policy_traverse,
	policy_clear,
	NULL
};

#define INITERROR return NULL

PyObject *
PyInit_policy(void)

#else
#define INITERROR return

void
initpolicy(void)
#endif
{
#if PY_MAJOR_VERSION >= 3
    PyObject *module = PyModule_Create(&moduledef);
#else
    PyObject *module = Py_InitModule("policy", policy_methods);
#endif

    if (module == NULL)
	INITERROR;
    struct module_state *st = GETSTATE(module);

    init_info(module);

    st->error = PyErr_NewException("policy.Error", NULL, NULL);
    if (st->error == NULL) {
	Py_DECREF(module);
	INITERROR;
    }

#if PY_MAJOR_VERSION >= 3
    return module;
#endif
}
