/* Author: James Athey
 */

%module selinux
%{
	#include "selinux/selinux.h"
%}

%pythoncode %{

import shutil, os, errno, stat

DISABLED = -1
PERMISSIVE = 0
ENFORCING = 1

def restorecon(path, recursive=False):
    """ Restore SELinux context on a given path """

    try:
        mode = os.lstat(path)[stat.ST_MODE]
        status, context = matchpathcon(path, mode)
    except OSError:
        path = os.path.realpath(os.path.expanduser(path))
        mode = os.lstat(path)[stat.ST_MODE]
        try:
            status, context = matchpathcon(path, mode)
        except OSError as e:
            # matchpathcon returns ENOENT when <<none>> in file context
            if e.errno != errno.ENOENT:
                raise
            return

    if status == 0:
        try:
            status, oldcontext = lgetfilecon(path)
        except OSError as e:
            if e.errno != errno.ENODATA:
                raise
            oldcontext = None
        if context != oldcontext:
            lsetfilecon(path, context)

        if recursive:
            for root, dirs, files in os.walk(path):
                for name in files + dirs:
                   restorecon(os.path.join(root, name))

def chcon(path, context, recursive=False):
    """ Set the SELinux context on a given path """
    lsetfilecon(path, context)
    if recursive:
        for root, dirs, files in os.walk(path):
            for name in files + dirs:
               lsetfilecon(os.path.join(root,name), context)

def copytree(src, dest):
    """ An SELinux-friendly shutil.copytree method """
    shutil.copytree(src, dest)
    restorecon(dest, recursive=True)

def install(src, dest):
    """ An SELinux-friendly shutil.move method """
    shutil.move(src, dest)
    restorecon(dest, recursive=True)
%}

/* security_get_boolean_names() typemap */
%typemap(argout) (char ***names, int *len) {
	PyObject* list = PyList_New(*$2);
	int i;
	for (i = 0; i < *$2; i++) {
		PyList_SetItem(list, i, PyBytes_FromString((*$1)[i]));
	}
	$result = SWIG_Python_AppendOutput($result, list);
}

/* return a sid along with the result */
%typemap(argout) (security_id_t * sid) {
	if (*$1) {
                %append_output(SWIG_NewPointerObj(*$1, $descriptor(security_id_t), 0));
	} else {
		Py_INCREF(Py_None);
		%append_output(Py_None);
	}
}

%typemap(in,numinputs=0) security_id_t *(security_id_t temp) {
  $1 = &temp;
}

%typemap(in, numinputs=0) void *(char *temp=NULL) {
	$1 = temp;
}

/* Makes security_compute_user() return a Python list of contexts */
%typemap(argout) (char ***con) {
	PyObject* plist;
	int i, len = 0;
	
	if (*$1) {
		while((*$1)[len])
			len++;
		plist = PyList_New(len);
		for (i = 0; i < len; i++) {
			PyList_SetItem(plist, i,
                                       PyBytes_FromString((*$1)[i])
                                       );
		}
	} else {
		plist = PyList_New(0);
	}

	$result = SWIG_Python_AppendOutput($result, plist);
}

/* Makes functions in get_context_list.h return a Python list of contexts */
%typemap(argout) (char ***list) {
	PyObject* plist;
	int i;
	
	if (*$1) {
		plist = PyList_New(result);
		for (i = 0; i < result; i++) {
			PyList_SetItem(plist, i,
                                       PyBytes_FromString((*$1)[i])
                                       );
		}
	} else {
		plist = PyList_New(0);
	}
	/* Only return the Python list, don't need to return the length anymore */
	$result = plist;
}

%typemap(in,noblock=1,numinputs=0) char ** (char * temp = 0) {
	$1 = &temp;
}
%typemap(freearg,match="in") char ** "";
%typemap(argout,noblock=1) char ** {
	if (*$1) {
		%append_output(SWIG_FromCharPtr(*$1));
		freecon(*$1);
	}
	else {
		Py_INCREF(Py_None);
		%append_output(Py_None);
	}
}

%typemap(in,noblock=1,numinputs=0) char ** (char * temp = 0) {
	$1 = &temp;
}
%typemap(freearg,match="in") char ** "";
%typemap(argout,noblock=1) char ** {
	if (*$1) {
		%append_output(SWIG_FromCharPtr(*$1));
		free(*$1);
	}
	else {
		Py_INCREF(Py_None);
		%append_output(Py_None);
	}
}

%typemap(in) char * const [] {
	int i, size;
	PyObject * s;

	if (!PySequence_Check($input)) {
		PyErr_SetString(PyExc_ValueError, "Expected a sequence");
		return NULL;
	}

	size = PySequence_Size($input);
	
	$1 = (char**) malloc(size + 1);

	for(i = 0; i < size; i++) {
		if (!PyBytes_Check(PySequence_GetItem($input, i))) {
			PyErr_SetString(PyExc_ValueError, "Sequence must contain only bytes");

			return NULL;
		}

	}
		
	for(i = 0; i < size; i++) {
		s = PySequence_GetItem($input, i);

		$1[i] = (char*) malloc(PyBytes_Size(s) + 1);
		strcpy($1[i], PyBytes_AsString(s));

	}
	$1[size] = NULL;
}

%typemap(freearg,match="in") char * const [] {
	int i = 0;
	while($1[i]) {
		free($1[i]);
		i++;
	}
	free($1);
}

%include "selinuxswig_python_exception.i"
%include "selinuxswig.i"
