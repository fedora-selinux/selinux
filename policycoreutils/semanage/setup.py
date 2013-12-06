# Authors:
#   Dan Walsh <dwalsh@redhat.com>
#
# Copyright (C) 2013  Red Hat
# see file 'COPYING' for use and warranty information
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

from distutils.core import setup, Extension

setup(name             = 'seobject',
      version          = '0.1',
      description      = 'python bindings used by semanage and system-config-selinux',
      long_description = 'python bindings used by semanage and system-config-selinux',
      author           = 'Dan Walsh',
      author_email     = 'dwalsh@redhat.com',
      maintainer       = 'Dan Walsh',
      maintainer_email = 'dwalsh@redhat.com',
      license          = 'GPLv2+',
      platforms        = 'posix',
      url              = '',
      download_url     = '',
      packages=["seobject"],
)
