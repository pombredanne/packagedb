# -*- coding: utf-8 -*-
#
# Copyright © 2007-2008  Red Hat, Inc. All rights reserved.
#
# This copyrighted material is made available to anyone wishing to use, modify,
# copy, or redistribute it subject to the terms and conditions of the GNU
# General Public License v.2.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY expressed or implied, including the
# implied warranties of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.  You should have
# received a copy of the GNU General Public License along with this program;
# if not, write to the Free Software Foundation, Inc., 51 Franklin Street,
# Fifth Floor, Boston, MA 02110-1301, USA. Any Red Hat trademarks that are
# incorporated in the source code or documentation are not subject to the GNU
# General Public License and may only be used or replicated with the express
# permission of Red Hat, Inc.
#
# Red Hat Author(s): Toshio Kuratomi <tkuratom@redhat.com>
#
'''
Mapping of acl related database tables
'''

from sqlalchemy import Table, Column, ForeignKey, Integer
from sqlalchemy import select, literal_column, not_
from sqlalchemy.orm import polymorphic_union, relation, backref
from turbogears.database import metadata, mapper, get_engine

from fedora.tg.json import SABase

get_engine()

#
# Mapped Tables
#

PersonPackageListingTable = Table('personpackagelisting', metadata,
        autoload=True)
GroupPackageListingTable = Table('grouppackagelisting', metadata, autoload=True)
PersonPackageListingAclTable = Table('personpackagelistingacl', metadata,
        autoload=True)
GroupPackageListingAclTable = Table('grouppackagelistingacl', metadata,
        autoload=True)

#
# Mapped Classes
#

class PersonPackageListing(SABase):
    '''Associate a person with a PackageListing.

    People who are watching or can modify a packagelisting.

    Table -- PersonPackageListing
    '''
    # pylint: disable-msg=R0902, R0903
    def __init__(self, userid, packagelistingid=None):
        # pylint: disable-msg=R0913
        super(PersonPackageListing, self).__init__()
        self.userid = userid
        self.packagelistingid = packagelistingid

    def __repr__(self):
        return 'PersonPackageListing(%r, %r)' % (self.userid,
                self.packagelistingid)

class GroupPackageListing(SABase):
    '''Associate a group with a PackageListing.

    Table -- GroupPackageListing
    '''
    # pylint: disable-msg=R0902, R0903
    def __init__(self, groupid, packagelistingid=None):
        # pylint: disable-msg=R0913
        super(GroupPackageListing, self).__init__()
        self.groupid = groupid
        self.packagelistingid = packagelistingid

    def __repr__(self):
        return 'GroupPackageListing(%r, %r)' % (self.groupid,
                self.packagelistingid)

class PersonPackageListingAcl(SABase):
    '''Acl on a package that a person owns.

    Table -- PersonPackageListingAcl
    '''
    # pylint: disable-msg=R0902, R0903
    def __init__(self, acl, statuscode=None, personpackagelistingid=None):
        # pylint: disable-msg=R0913
        super(PersonPackageListingAcl, self).__init__()
        self.personpackagelistingid = personpackagelistingid
        self.acl = acl
        self.statuscode = statuscode

    def __repr__(self):
        return 'PersonPackageListingAcl(%r, %r, personpackagelistingid=%r)' \
                % (self.acl, self.statuscode, self.personpackagelistingid)

class GroupPackageListingAcl(SABase):
    '''Acl on a package that a group owns.

    Table -- GroupPackageListingAcl
    '''
    # pylint: disable-msg=R0902, R0903
    def __init__(self, acl, statuscode=None, grouppackagelistingid=None):
        # pylint: disable-msg=R0913
        super(GroupPackageListingAcl, self).__init__()
        self.grouppackagelistingid = grouppackagelistingid
        self.acl = acl
        self.statuscode = statuscode

    def __repr__(self):
        return 'GroupPackageListingAcl(%r, %r, grouppackagelistingid=%r)' % (
                self.acl, self.statuscode, self.grouppackagelistingid)

#
# Mappers
#

mapper(PersonPackageListing, PersonPackageListingTable, properties = {
    'acls':relation(PersonPackageListingAcl,
        backref='personpackagelisting')})
mapper(GroupPackageListing, GroupPackageListingTable, properties = {
    'acls':relation(GroupPackageListingAcl,
        backref='grouppackagelisting')})
mapper(PersonPackageListingAcl, PersonPackageListingAclTable)
mapper(GroupPackageListingAcl, GroupPackageListingAclTable)
