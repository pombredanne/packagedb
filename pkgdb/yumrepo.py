# -*- coding: utf-8 -*-
#
# Copyright © 2007  Red Hat, Inc. All rights reserved.
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
Manipulate information from the download repositories.
'''
import os
import yum
import logging

from turbogears import config
from turbogears.database import session

import sqlalchemy
from sqlalchemy.exceptions import InvalidRequestError
from sqlalchemy import MetaData, create_engine
from sqlalchemy import Table, Column, Integer, String
from sqlalchemy.orm import Mapper

from pkgdb.json import SABase
from pkgdb import model

log = logging.getLogger('pkgdb.repo')

class UnknownRepoMDFormat(Exception):
    '''An unknown repository format was encountered.'''
    pass

class DB_Info (SABase):
    '''Metainformation about the yum cache.'''
    # pylint: disable-msg=R0903
    def __repr__(self):
        # pylint: disable-msg=E1101
        return 'DBInfo(%s, "%s")' % (self.dbversion, self.checksum)

class Packages(SABase):
    '''Package data in the yum repo.'''
    # pylint: disable-msg=R0903
    def __str__(self):
        # pylint: disable-msg=E1101
        return '%s-%s:%s-%s' % (self.name, self.epoch, self.version,
                self.release)

    def __repr__(self):
        # pylint: disable-msg=E1101
        return 'Packages(pkgKey=%s, pkgId="%s", name="%s", arch="%s",' \
                ' version="%s", epoch="%s", release="%s", summary="%s",' \
                ' description="%s", url="%s", time_file="%s",' \
                ' time_build="%s", rpm_license="%s", rpm_vendor="%s",' \
                ' rpm_group="%s", rpm_buildhost="%s", rpm_sourcerpm="%s",' \
                ' rpm_header_start=%s, rpm_header_end=%s, rpm_packager="%s",' \
                ' size_package=%s, size_installed=%s, size_archive=%s,' \
                ' location_href="%s", location_base="%s", checksum_type="%s")' \
                % (self.pkgKey, self.pkgId, self.name, self.arch, self.version,
                        self.epoch, self.release, self.summary,
                        self.description, self.url, self.time_file,
                        self.time_build, self.rpm_license, self.rpm_vendor,
                        self.rpm_group, self.rpm_buildhost, self.rpm_sourcerpm,
                        self.rpm_header_start, self.rpm_header_end,
                        self.rpm_packager, self.size_package,
                        self.size_installed, self.size_archive,
                        self.location_href, self.location_base,
                        self.checksum_type)

class RepoUpdater(yum.YumBase):
    '''Update yum repository information on the local system.
    
    This class allows one to update the yum metadata on the local system
    from a set of repo definitions. By splitting this into its own class we
    are able to run it from a separate application, useful because it can
    gradually acquire more memory over time which would lead a long-running
    server to have issues.
    '''

    def __init__(self):
        super(RepoUpdater, self).__init__()
        self.doConfigSetup()
        for repo in self.repos.findRepos('*'):
            self.repos.delete(repo.id)

        repodir = os.path.join(config.get('pkgdb.basedir',
                '/usr/local/fedora-packagedb'), 'yum.repos.d')
        if os.access(repodir, os.R_OK | os.X_OK):
            # Substitute for the system repo definitions because we can't
            # guarantee that the system repo's work (esp. for devel)
            self.conf.reposdir = [repodir]

        self.getReposFromConfig()
        self.repos.setCacheDir(yum.misc.getCacheDir())
        self.doRepoSetup()

        # Download repository information to use
        self._get_repodata()

    def _get_repodata(self):
        '''Use yum API to retrive new repodata files from remote repositories.
        '''
        for repo in self.repos.findRepos('*'):
            repo.sack.populate(repo)
            # If we want more than just primary metadata, then pass:
            # repo.getPackageSack().populate(repo, mdtype='TYPE')
            # where TYPE == one of: 'filelists', 'otherdata', 'all'

class RepoInfo(object):
    '''Interact with a set of yum repositories.

    Why not use the yum API to do this?  There are some memory leaks
    (More technically, it might be memory fragmentation) that can push a long
    running server into eventual memory starvation.

    Using our own access routines curbs this memory usage.
    '''
    ### FIXME: Test what happens when we are accessing a repo.sqlite file that
    # is changed or replaced.
    # Test what happens if we have a repo.sqlite file open and use RepoUpdater
    # to change it.
    
    # pylint: disable-msg=E1101
    approvedStatus = model.StatusTranslation.filter_by(statusname='Approved',
            language='C').one().statuscodeid
    # pylint: enable-msg=E1101

    def __init__(self):
        '''Setup the links to repositories and the table mappings.
        '''
        # Find all the repos we know about
        self.repodir = yum.misc.getCacheDir()
        dbFiles = yum.misc.getFileList(self.repodir, '.sqlite', [])

        # Add paths to repoDB files
        self.repoFiles = {}
        for dbFile in dbFiles:
            repoDir, dbFileName = os.path.split(dbFile)
            repoName = os.path.basename(repoDir)
            mdtype = dbFileName[:dbFileName.index('.')]
            engine = create_engine('sqlite:///' + dbFile)
            try:
                self.repoFiles[repoName][mdtype] = engine
            except KeyError:
                self.repoFiles[repoName] = {mdtype: engine}

        # Set up sqlalchemy mappers for the packageDB tables
        self.metadata = MetaData()
        self.DB_InfoTable = Table('db_info', self.metadata,
                Column('dbversion', Integer, nullable=False),
                Column('checksum', String,  primary_key=True)
                )
        self.PackagesTable = Table('packages', self.metadata,
                Column('pkgKey', Integer, primary_key=True),
                Column('pkgId', String),
                Column('name', String),
                Column('arch', String),
                Column('version', String),
                Column('epoch', String),
                Column('release', String),
                Column('summary', String),
                Column('description', String),
                Column('url', String),
                Column('time_file', String),
                Column('time_build', String),
                Column('rpm_license', String),
                Column('rpm_vendor', String),
                Column('rpm_group', String),
                Column('rpm_buildhost', String),
                Column('rpm_sourcerpm', String),
                Column('rpm_header_start', Integer),
                Column('rpm_header_end', Integer),
                Column('rpm_packager', String),
                Column('size_package', Integer),
                Column('size_installed', Integer),
                Column('size_archive', Integer),
                Column('location_href', String),
                Column('location_base', String),
                Column('checksum_type', String)
                )
        Mapper(DB_Info, self.DB_InfoTable)
        Mapper(Packages, self.PackagesTable)
        self.session = sqlalchemy.create_session()

    def _bind_to_repo(self, repo, mdtype):
        '''Set our model to talk to the db in this particular repo.'''
        self.metadata.bind = self.repoFiles[repo][mdtype]
        info = self.session.query(DB_Info).one()
        if info.dbversion not in (9, 10):
            raise UnknownRepoMDFormat, 'Expected Repo format 9 or 10, got %s' \
                    % (info.dbversion)

    def sync_package_descriptions(self):
        '''Add a new package to the database.
        '''
        # Retrieve all the packages which are active
        pkgs = model.Package.filter_by( # pylint: disable-msg=E1101
                # pylint: disable-msg=E1101
                model.Package.c.statuscode==self.approvedStatus)

        # Since we update the information, we need to be sure we search from
        # most current information to least current information
        # Order to search:
        # development
        # updates,fedora[latest two releases]
        # olpc[latest]
        # epel[latest two releases]
        # everything else

        # Separate the repos
        develRepos = []
        updateRepos = []
        fedoraRepos = []
        olpcRepos = []
        epelRepos = []
        otherRepos = []
        for repo in self.repoFiles.keys():
            if repo.startswith('updates'):
                updateRepos.append(repo)
            elif repo.startswith('fedora'):
                fedoraRepos.append(repo)
            elif repo.startswith('development'):
                develRepos.append(repo)
            elif repo.startswith('epel'):
                epelRepos.append(repo)
            elif repo.startswith('olpc'):
                olpcRepos.append(repo)
            else:
                otherRepos.append(repo)
        develRepos.sort(reverse=True)
        updateRepos.sort(reverse=True)
        fedoraRepos.sort(reverse=True)
        epelRepos.sort(reverse=True)
        olpcRepos.sort(reverse=True)
        otherRepos.sort(reverse=True)

        # All development repos first
        repoList = develRepos

        # Pull off the update and fedora repos for the latest two releases
        for numReleases in range(0, 2): # pylint: disable-msg=W0612
            release = updateRepos[0][len('updates'):updateRepos[0].index('-')]
            updateStr = 'updates%s-' % release
            while updateRepos and updateRepos[0].startswith(updateStr):
                repoList.append(updateRepos[0])
                del updateRepos[0]
            fedoraStr = 'fedora%s-' % release
            while fedoraRepos and fedoraRepos[0].startswith(fedoraStr):
                repoList.append(fedoraRepos[0])
                del fedoraRepos[0]

        # One release for olpc
        olpcStr = olpcRepos[0][0:olpcRepos[0].index('-')+1]
        while olpcRepos and olpcRepos[0].startswith(olpcStr):
            repoList.append(olpcRepos[0])
            del olpcRepos[0]

        # Two for epel
        for numRelease in range(0, 2): # pylint: disable-msg=W0612
            epelStr = epelRepos[0][0:epelRepos[0].index('-')+1]
            while epelRepos and epelRepos[0].startswith(epelStr):
                repoList.append(epelRepos[0])
                del epelRepos[0]

        # Now add all the remainders to repoList
        repoList.extend(updateRepos)
        repoList.extend(fedoraRepos)
        repoList.extend(olpcRepos)
        repoList.extend(epelRepos)
        repoList.extend(otherRepos)

        # For each repo check the packages for an updated description
        for repoName in repoList:
            self._bind_to_repo(repoName, 'primary')
            newPkgList = []
            for pkg in pkgs:
                try:
                    packages = self.session.query(Packages
                            ).filter_by(name=pkg.name).one()
                except InvalidRequestError:
                    # No information here, search another
                    pass
                else:
                    # Found!  We can stop searching for this package now
                    if pkg.description != packages.description:
                        pkg.description = packages.description
                    if pkg.summary != packages.summary:
                        pkg.summary = packages.summary
                    continue
                newPkgList.append(pkg)
                self.session.close()

            # Only continue looking for packages we haven't found
            pkgs = newPkgList

        # Flush the new descriptions to the TG context session
        session.flush()
        session.close()

        # List packages which haven't changed
        noDesc = [pkg.name for pkg in pkgs if not pkg.description]
        noDesc.sort()
        log.warning('Packages without descriptions: %s' % len(noDesc))
        log.warning('\t'.join(noDesc))

### FIXME: DB Tables not yet listed here:
# CREATE TABLE provides (  name TEXT,  flags TEXT,  epoch TEXT,  version TEXT,
# release TEXT,  pkgKey INTEGER );
# CREATE TABLE requires (  name TEXT,  flags TEXT,  epoch TEXT,  version TEXT,
# release TEXT,  pkgKey INTEGER , pre BOOLEAN DEFAULT FALSE);
# CREATE TABLE conflicts (  name TEXT,  flags TEXT,  epoch TEXT,  version
# TEXT,  release TEXT,  pkgKey INTEGER );
# CREATE TABLE files (  name TEXT,  type TEXT,  pkgKey INTEGER);
# CREATE TABLE obsoletes (  name TEXT,  flags TEXT,  epoch TEXT,  version
# TEXT,  release TEXT,  pkgKey INTEGER );
#
