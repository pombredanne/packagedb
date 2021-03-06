# -*- coding: utf-8 -*-
#
# Copyright © 2007-2008  Red Hat, Inc.
#
# This copyrighted material is made available to anyone wishing to use, modify,
# copy, or redistribute it subject to the terms and conditions of the GNU
# General Public License v.2, or (at your option) any later version.  This
# program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY expressed or implied, including the implied warranties of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.  You should have received a copy of the GNU
# General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA. Any Red Hat trademarks that are incorporated in the source
# code or documentation are not subject to the GNU General Public License and
# may only be used or replicated with the express permission of Red Hat, Inc.
#
# Red Hat Author(s): Toshio Kuratomi <tkuratom@redhat.com>
#
'''
Mapping of database tables for logs to python classes.
'''

from sqlalchemy import Table
from sqlalchemy import select, literal_column, not_
from sqlalchemy.orm import polymorphic_union, relation
from turbogears.database import metadata, mapper, get_engine

from fedora.tg.json import SABase

from pkgdb.model.packages import Package, PackageListing
from pkgdb.model.acls import PersonPackageListingAcl, GroupPackageListingAcl

get_engine()

#
# Mapped Classes
#

class Log(SABase):
    '''Base Log record.

    This is a Log record.  All logs will be entered via a subclass of this.

    Table -- Log
    '''
    # pylint: disable-msg=R0902, R0903
    def __init__(self, username, description=None, changetime=None):
        # pylint: disable-msg=R0913
        super(Log, self).__init__()
        self.username = username
        self.description = description
        self.changetime = changetime

    def __repr__(self):
        return 'Log(%r, description=%r, changetime=%r)' % (self.username,
                self.description, self.changetime)

class PackageLog(Log):
    '''Log of changes to Packages.

    Table -- PackageLog
    '''
    # pylint: disable-msg=R0902, R0903
    def __init__(self, username, action, description=None, changetime=None,
            packageid=None):
        # pylint: disable-msg=R0913
        super(PackageLog, self).__init__(username, description, changetime)
        self.action = action
        self.packageid = packageid

    def __repr__(self):
        return 'PackageLog(%r, %r, description=%r, changetime=%r,' \
                ' packageid=%r)' % (self.username, self.action,
                        self.description, self.changetime, self.packageid)

class PackageListingLog(Log):
    '''Log of changes to the PackageListings.

    Table -- PackageListingLog
    '''
    # pylint: disable-msg=R0902, R0903
    def __init__(self, username, action, description=None, changetime=None,
            packagelistingid=None):
        # pylint: disable-msg=R0913
        super(PackageListingLog, self).__init__(username, description,
                changetime)
        self.action = action
        self.packagelistingid = packagelistingid

    def __repr__(self):
        return 'PackageListingLog(%r, %r, description=%r, changetime=%r,' \
                ' packagelistingid=%r)' % (self.username,
                self.action, self.description, self.changetime,
                self.packagelistingid)

class PersonPackageListingAclLog(Log):
    '''Log changes to an Acl that a person owns.

    Table -- PersonPackageListingAcl
    '''
    # pylint: disable-msg=R0902, R0903
    def __init__(self, username, action, description=None, changetime=None,
            personpackagelistingaclid=None):
        # pylint: disable-msg=R0913
        super(PersonPackageListingAclLog, self).__init__(username, description,
                changetime)
        self.action = action
        self.personpackagelistingaclid = personpackagelistingaclid

    def __repr__(self):
        return 'PersonPackageListingAclLog(%r, %r, description=%r,' \
                ' changetime=%r, personpackagelistingaclid=%r)' % (
                        self.username, self.action, self.description,
                        self.changetime, self.personpackagelistingaclid)

class GroupPackageListingAclLog(Log):
    '''Log changes to an Acl that a group owns.

    Table -- GroupPackageListingAclLog
    '''
    # pylint: disable-msg=R0902, R0903
    def __init__(self, username, action, description=None, changetime=None,
            grouppackagelistingaclid=None):
        # pylint: disable-msg=R0913
        super(GroupPackageListingAclLog, self).__init__(username, description,
                changetime)
        self.action = action
        self.grouppackagelistingaclid = grouppackagelistingaclid

    def __repr__(self):
        return 'GroupPackageListingAclLog(%r, %r, description=%r,' \
                ' changetime=%r, grouppackagelistingaclid=%r)' % (
                        self.username, self.action, self.description,
                        self.changetime, self.grouppackagelistingaclid)

#
# Mapped Tables
#

# The log tables all inherit from the base log table.

# :C0103: Tables and mappers are constants but SQLAlchemy/TurboGears convention
# is not to name them with all uppercase
# pylint: disable-msg=C0103
LogTable = Table('log', metadata, autoload = True)

PackageLogTable = Table('packagelog', metadata, autoload = True)
PackageListingLogTable = Table('packagelistinglog', metadata, autoload = True)
PersonPackageListingAclLogTable = Table('personpackagelistingacllog', metadata,
        autoload = True)
GroupPackageListingAclLogTable = Table('grouppackagelistingacllog', metadata,
        autoload = True)

logJoin = polymorphic_union (
        {'pkglog': select((LogTable.join(
            PackageLogTable,
                LogTable.c.id == PackageLogTable.c.logid),
            literal_column("'pkglog'").label('kind'))),
         'pkglistlog': select((LogTable.join(
            PackageListingLogTable,
                LogTable.c.id == PackageListingLogTable.c.logid),
            literal_column("'pkglistlog'").label('kind'))),
         'personpkglistacllog': select((LogTable.join(
            PersonPackageListingAclLogTable,
                LogTable.c.id == PersonPackageListingAclLogTable.c.logid),
            literal_column("'personpkglistacllog'").label('kind'))),
         'grouppkglistacllog': select((LogTable.join(
            GroupPackageListingAclLogTable,
                LogTable.c.id == GroupPackageListingAclLogTable.c.logid),
            literal_column("'grouppkglistacllog'").label('kind'))),
         'log': select((LogTable, literal_column("'log'").label('kind')),
             not_(LogTable.c.id.in_(select(
                 (LogTable.c.id,),
                 LogTable.c.id == PackageListingLogTable.c.logid)
             )))
         },
        None
        )

#
# Mappers
#

logMapper = mapper(Log, LogTable, select_table=logJoin,
        polymorphic_on=logJoin.c.kind, polymorphic_identity='log'
        )

mapper(PersonPackageListingAclLog, PersonPackageListingAclLogTable,
        inherits=logMapper, polymorphic_identity='personpkglistacllog',
        inherit_condition=LogTable.c.id == \
                PersonPackageListingAclLogTable.c.logid,
        properties={
            'acl': relation(PersonPackageListingAcl, backref='logs')
            })

mapper(GroupPackageListingAclLog, GroupPackageListingAclLogTable,
        inherits=logMapper, polymorphic_identity='grouppkglistacllog',
        inherit_condition=LogTable.c.id == \
                GroupPackageListingAclLogTable.c.logid,
        properties={
            'acl': relation(GroupPackageListingAcl, backref='logs')
            })

mapper(PackageLog, PackageLogTable,
        inherits=logMapper, polymorphic_identity='pkglog',
        inherit_condition=LogTable.c.id == PackageLogTable.c.logid,
        properties={
            'package': relation(Package, backref='logs')
            })

mapper(PackageListingLog, PackageListingLogTable,
        inherits=logMapper, polymorphic_identity='pkglistlog',
        inherit_condition=LogTable.c.id == PackageListingLogTable.c.logid,
        properties={
            'listing': relation(PackageListing, backref='logs')
            })
