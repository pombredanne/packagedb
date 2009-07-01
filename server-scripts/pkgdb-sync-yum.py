# BEWARE - evil yum 3.2.23-5 requirement for changing releasever

import os
import sys
import yum
import sqlalchemy
import logging
import datetime

from sqlalchemy.sql import insert
from turbogears import config, update_config
from turbogears.database import session

CONFDIR='/home/mapleoin/fedora-packagedb-devel'
PKGDBDIR=os.path.join('/home/mapleoin/fedora-packagedb-devel', 'fedora-packagedb')
sys.path.append(PKGDBDIR)

if len(sys.argv) > 1:
    update_config(configfile=sys.argv[1],
        modulename='pkgdb.config')
elif os.path.exists(os.path.join(os.path.dirname(__file__), '..', 'setup.py')):
    update_config(configfile='pkgdb.cfg', modulename='pkgdb.config')
else:
    update_config(configfile=os.path.join(CONFDIR,'pkgdb.cfg'),
            modulename='pkgdb.config')
config.update({'pkgdb.basedir': PKGDBDIR})

from pkgdb.model import Package, PackageListing, Branch, PackageBuild, \
                     PackageBuildTable, RpmProvidesTable, RpmRequiresTable, \
                     RpmConflictsTable, RpmObsoletesTable, RpmFilesTable, \
                     Repo, ReposTable, PackageBuildListingTable

fas_url = config.get('fas.url', 'https://admin.fedoraproject.org/accounts/')
username = config.get('fas.username', 'admin')
password = config.get('fas.password', 'admin')

log = logging.getLogger('pkgdb')
yb = yum.YumBase()

# don't update the cache
yb.conf.cache = os.geteuid() != 0 

yb.repos.disableRepo('*')
# A dictionary of repoid : branchname
repos = {'fedora':'F-11'}
reponum = 1

for repoid in repos: #Repo.query.all():
    yb.repos.enableRepo(repoid)
    yb._getSacks(thisrepo=repoid)
    repo = yb.repos.getRepo(repoid)
    log.info('Refreshing repo: %s' % repoid)
    
    # populate pkgdb with packagebuilds (rpms)
    rpms = repo.sack.returnNewestByName();
    for rpm in rpms:
        # FIXME yb.close

        # get the name of the Package, ignore -devel/-doc tags, version etc.
        # !version sometimes isn't the same as the sourcerpm's
        namelist = rpm.sourcerpm.split('-')
        namelist.pop()
        namelist.pop()
        packagename = '-'.join(namelist)
        
        pkg_query = Package.query.filter_by(name=packagename)
        try:
            package = pkg_query.one()
        except:
            log.warn("%s - the corresponding package does not exist in the" \
                     " pkgdb! pkgbuild was not added. Tried: %s" %
                     (rpm.name, packagename))
        else:
            # what's my packagelisting?
            collectionid = Branch.query.filter_by(
                branchname='F-11').one().collectionid
            listing_query = PackageListing.query.filter_by(
                                packageid=package.id,
                                collectionid=collectionid)
            try:
                listing = listing_query.one()
            except:
                log.warn("%s - the corresponding packagelist does not " \
                      "exist in the pkgdb! pkgbuild was not added." % rpm.name)
            else:
                if PackageBuild.query.filter_by(
                                name=rpm.name,
                                packageid=package.id,
                                version=rpm.version,
                                architecture=rpm.arch,
                                repoid=int(reponum),
                                release=rpm.release).count() != 0:
                    log.warn("%s.%s - PackageBuild already in!" % (
                        pkg_query.one().name, rpm.version))
                    break

                desktop = False
                for f in rpm.filelist:
                    if f.endswith('.desktop'):
                        desktop = True
                        
                # insert the new pkgbuild
                # TODO give the changelog part more thought
                # pkgbuild = PackageBuild(
                #     packageid=package.id, name=rpm.name,
                #     epoch=rpm.epoch, version=rpm.version,
                #     release=rpm.release, size=rpm.size,
                #     architecture=rpm.arch, desktop=desktop,
                #     license=rpm.license, changelog=rpm.changelog[0][0],
                #     repoid=int(reponum))
                # session.add(pkgbuild)
                # session.begin()
                # session.commit()

                # do a bit of house-keeping
                (committime, committer, changelog) = rpm.changelog[0]
                committime = datetime.datetime.utcfromtimestamp(committime)
                committer = committer.replace('- ', '')
                committer = committer.rpartition(' ')[0]
                
                pkgbuildid = PackageBuildTable.insert().values(
                    packageid=package.id, name=rpm.name,
                    epoch=rpm.epoch, version=rpm.version,
                    release=rpm.release, size=rpm.size,
                    architecture=rpm.arch, desktop=desktop,
                    license=rpm.license, changelog=changelog,
                    committime=committime, committer=committer,
                    repoid=int(reponum)).execute().last_inserted_ids()[-1]
                
                # associate the listing with the packagebuild
                #pkgbuild.listings.append(listing)
                PackageBuildListingTable.insert().values(
                    packagebuildid=pkgbuildid, packagelistingid=listing.id
                    ).execute()

                # update PRCOs (treat requires as special case)
                prcos = [['provides', RpmProvidesTable],
                         ['conflicts', RpmConflictsTable],
                         ['obsoletes', RpmObsoletesTable]]
                for prco, prcotable in prcos:
                    for (n, f, (e, v, r)) in getattr(rpm, prco):
                        prcotable.insert().values(name=n, flags=f, epoch=e,
                                                  version=v, release=r,
                                                  packagebuildid=pkgbuildid
                                                  ).execute()
                # requires have the extra PreReq field
                for (n, f, (e, v, r), p) in rpm._requires_with_pre():
                    RpmRequiresTable.insert().values(name=n, flags=f, epoch=e,
                                        version=v, release=r, prereq=p,
                                        packagebuildid=pkgbuildid
                                        ).execute()
                # files
                for filename in rpm.filelist:
                    RpmFilesTable.insert().values(packagebuildid=pkgbuildid,
                                                  name=filename).execute()
                # update the package information

                if package.description!=rpm.description:
                    package.description=rpm.description
                if package.summary!=rpm.summary:
                    package.summary=rpm.summary
                if package.upstreamurl!=rpm.url:
                    package.upstreamurl=rpm.url
                
                # keep only the latest packagebuild from each repo
                for expkg in PackageBuild.query.filter_by(name=rpm.name,
                                             repoid=reponum).all():
                    session.delete(expkg)

                log.info('inserted %s.%s.%s' % (pkg_query.one().name,
                                             rpm.version, rpm.release))
