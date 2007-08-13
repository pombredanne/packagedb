import sqlalchemy
from sqlalchemy.ext.selectresults import SelectResults
import sqlalchemy.mods.selectresults

import turbomail
from turbogears import controllers, expose, identity, config
from turbogears.database import session

import simplejson

from fedora.accounts.fas import AuthError

from pkgdb import model

COMMITSLIST=config.get('commits_address')
ORPHAN_ID=9900

def send_msg(msg, subject, recipients):
    '''Send a message from the packagedb.'''
    fromAddr = config.get('from_address')
    for person in recipients:
        email = turbomail.Message(fromAddr, person, '[pkgdb] %s' % (subject,))
        email.plain = msg
        turbomail.enqueue(email)

class PackageDispatcher(controllers.Controller):
    def __init__(self, fas = None):
        self.fas = fas
        controllers.Controller.__init__(self)
        # We want to expose a list of public methods to the outside world so
        # they know what RPC's they can make
        ### FIXME: It seems like there should be a better way.
        self.methods = [ m for m in dir(self) if
                hasattr(getattr(self, m), 'exposed') and 
                getattr(self, m).exposed]

        ### FIXME: This is happening in two places: Here and in packages::id().
        # We should eventually only pass it in packages::id() but translating
        # from python to javascript makes this hard.

        # Possible statuses for acls:
        aclStatus = SelectResults(session.query(model.PackageAclStatus))
        self.aclStatusTranslations=['']
        # Create a mapping from status name => statuscode
        for status in aclStatus:
            ### FIXME: At some point, we have to pull other translations out,
            # not just C
            if status.translations[0].statusname != 'Obsolete':
                self.aclStatusTranslations.append(status.translations[0].statusname)

        ### FIXME: pull groups from somewhere.
        # In the future the list of groups that can commit to packages should
        # be stored in a database somewhere.  Either packagedb or FAS should
        # have a flag.

        # Create a list of groups that can possibly commit to packages
        self.groups = {100300: 'cvsextras',
                101197: 'cvsadmin',
                'cvsextras': 100300,
                'cvsadmin': 101197}

    def _send_log_msg(self, msg, subject, author, listings, acls=None,
            otherEmail=None):

        # Store the email addresses in a hash to eliminate duplicates
        recipients = {COMMITSLIST: '',
                author.user['email']: ''}

        acls = acls or ('approveacls',)
        if otherEmail:
            for email in otherEmail:
                recipients[email] = ''
        # Get the owners for this package
        for pkgListing in listings:
            if pkgListing.owner != ORPHAN_ID:
                (owner, group) = self.fas.get_user_info(pkgListing.owner)
                recipients[owner['email']] = ''

            # Get the co-maintainers
            aclUsers = SelectResults(session.query(
                model.PersonPackageListingAcl)
                ).select(model.PersonPackageListingAcl.c.personpackagelistingid == model.PersonPackageListing.c.id
                ).select(model.PersonPackageListing.c.packagelistingid==pkgListing.id
                ).select(model.PersonPackageListingAcl.c.acl.in_(*acls))
            for acl in aclUsers:
                if acl.status.translations[0].statusname=='Approved':
                    (person, groups) = self.fas.get_user_info(
                            acl.personpackagelisting.userid)
                    recipients[person['email']] = ''

        # Send the log
        send_msg(msg, subject, recipients.keys())

    def _user_can_set_acls(self, identity, pkg):
        '''Check that the current user can set acls.

        This method will return one of these values:
            'admin', 'owner', 'comaintainer', False
        depending on why the user is granted access.  You can therefore use the
        value for finer grained access to some resources.
        '''
        # Find the approved statuscode
        status = model.StatusTranslation.get_by(statusname='Approved')

        # For testing, let mizmo (Mairin Duffy) look at everything through the
        # admin web interface.
        if identity.current.user.user_id == 100548:
            return 'admin'
        # Make sure the current tg user has permission to set acls
        # If the user is a cvsadmin they can
        if identity.in_group('cvsadmin'):
            return 'admin'
        # The owner can
        if identity.current.user.user_id == pkg.owner:
            return 'owner'
        # Wasn't the owner.  See if they have been granted permission
        # explicitly
        for person in pkg.people:
            if person.userid == userid:
                # Check each acl that this person has on the package.
                for acl in person.acls:
                    if (acl.acl == 'approveacls' and acl.statuscode
                            == status.statuscodeid):
                        return 'comaintainer'
                break
        return False

    def _create_or_modify_acl(self, pkgList, personId, newAcl, status):
        '''Create or modify an acl.

        Set an acl for a user.  This takes a packageListing and makes sure
        there's an ACL for them with the given status.  It will create a new
        ACL or modify an existing one depending on what's in the db already.

        Arguments:
        :pkgList: PackageListing on which to set the ACL.
        :personId: PersonId to set the ACL for.
        :newAcl: ACL name to set.
        :status: Status DB Objcet we're setting the ACL to.
        '''
        # Create the ACL
        changePerson = None
        for person in pkgList.people:
            # Check for the person who's acl we're setting
            if person.userid == personId:
                changePerson = person
                break

        if not changePerson:
            # Person has no ACLs on this Package yet.  Create a record
            changePerson = model.PersonPackageListing(personId)
            pkgList.people.append(changePerson)
            personAcl = model.PersonPackageListingAcl(newAcl,
                    status.statuscodeid)
            changePerson.acls.append(personAcl)
        else:
            # Look for an acl for the person
            personAcl = None
            for acl in changePerson.acls:
                if acl.acl == newAcl:
                    # Found the acl, change its status
                    personAcl = acl
                    acl.statuscode = status.statuscodeid
                    break
            if not personAcl:
                # Acl was not found.  Create one.
                personAcl = model.PersonPackageListingAcl(newAcl,
                        status.statuscodeid)
                changePerson.acls.append(personAcl)

        return personAcl

    def _create_or_modify_group_acl(self, pkgList, groupId, newAcl, status):
        '''Create or modify a group acl.

        Set an acl for a group.  This takes a packageListing and makes sure
        there's an ACL for it with the given status.  It will create a new
        ACL or modify an existing one depending on what's in the db already.

        Arguments:
        :pkgList: PackageListing on which to set the ACL.
        :groupId: GroupId to set the ACL for.
        :newAcl: ACL name to set.
        :status: Status DB Objcet we're setting the ACL to.
        '''
        # Create the ACL
        changeGroup = None
        for group in pkgList.groups:
            # Check for the person who's acl we're setting
            if group.groupid == groupId:
                changeGroup = group
                break

        if not changeGroup:
            # Group has no ACLs on this Package yet.  Create a record
            changeGroup = model.GroupPackageListing(groupId)
            pkgList.group.append(changeGroup)
            groupAcl = model.GroupPackageListingAcl(newAcl,
                    status.statuscodeid)
            changeGroup.acls.append(groupAcl)
        else:
            # Look for an acl for the group
            groupAcl = None
            for acl in changeGroup.acls:
                if acl.acl == newAcl:
                    # Found the acl, change its status
                    groupAcl = acl
                    acl.statuscode = status.statuscodeid
                    break
            if not groupAcl:
                # Acl was not found.  Create one.
                groupAcl = model.GroupPackageListingAcl(newAcl,
                        status.statuscodeid)
                changeGroup.acls.append(groupAcl)

        return groupAcl

    @expose('json')
    def index(self):
        return dict(methods=self.methods)

    @expose('json')
    @identity.require(identity.not_anonymous())
    def toggle_owner(self, containerId):
        # Check that the tg.identity is allowed to set themselves as owner
        if not identity.in_any_group('cvsextras', 'cvsadmin'):
            return dict(status=False, message='User must be in cvsextras or cvsadmin')

        # Check that the pkgid is orphaned
        pkg = model.PackageListing.get_by(id=containerId)
        if not pkg:
            return dict(status=False, message='No such package %s' % containerId)
        approved = self._user_can_set_acls(identity, pkg)
        if pkg.owner == ORPHAN_ID:
            # Take ownership
            pkg.owner = identity.current.user.user_id
            ownerName = '%s (%s)' % (identity.current.user.display_name,
                    identity.current.user_name)
            logMessage = 'Package %s in %s %s is now owned by %s' % (
                    pkg.package.name, pkg.collection.name,
                    pkg.collection.version, ownerName)
            status = model.StatusTranslation.get_by(statusname='Owned')
        elif approved in ('admin', 'owner'):
            # Release ownership
            pkg.owner = ORPHAN_ID
            ownerName = 'Orphaned Package (orphan)'
            logMessage = 'Package %s in %s %s was orphaned by %s (%s)' % (
                    pkg.package.name, pkg.collection.name,
                    pkg.collection.version, identity.current.user.display_name,
                    identity.current.user_name)
            status = model.StatusTranslation.get_by(statusname='Orphaned')
        else:
            return dict(status=False, message=
                    'Package %s not available for taking' % containerId)

        # Make sure a log is created in the db as well.
        log = model.PackageListingLog(identity.current.user.user_id,
                status.statuscodeid, logMessage, None, containerId)
        log.packagelistingid = pkg.id

        try:
            session.flush()
        except sqlalchemy.exceptions.SQLError, e:
            # An error was generated
            return dict(status=False,
                    message='Not able to change owner information for %s' \
                            % (containerId))

        # Send a log to people interested in this package as well
        self._send_log_msg(logMessage, '%s %s' % (pkg.package.name,
            status.statusname), identity.current.user, (pkg,),
            ('approveacls', 'watchbugzilla', 'watchcommits', 'build', 'commit'))

        return dict(status=True, ownerId=pkg.owner, ownerName=ownerName,
                aclStatusFields=self.aclStatusTranslations)

    @expose('json')
    # Check that the requestor is in a group that could potentially set ACLs.
    @identity.require(identity.not_anonymous())
    def set_acl_status(self, pkgid, personid, newAcl, statusname):
        ### FIXME: Changing Obsolete into "" sounds like it should be
        # Pushed out to the view (template) instead of being handled in the
        # controller.
        
        # We are making Obsolete into "" for our interface.  Need to reverse
        # that here.
        if not statusname or not statusname.strip():
            statusname = 'Obsolete'
        status = model.StatusTranslation.get_by(statusname=statusname)

        # Change strings into numbers because we do some comparisons later on
        pkgid = int(pkgid)
        personid = int(personid)

        # Make sure the package listing exists
        pkg = model.PackageListing.get_by(id=pkgid)
        if not pkg:
            return dict(status=False,
                    message='Package Listing %s does not exist' % pkgid)

        # Make sure the person we're setting the acl for exists
        try:
            self.fas.verify_user_pass(personid, '')
        except AuthError, e:
            if str(e).startswith('No such user: '):
                return dict(status=False,
                        message=str(e))
            else:
                raise

        # Check that the tg.identity is allowed to set themselves as owner
        if not identity.in_any_group('cvsextras', 'cvsadmin'):
            return dict(status=False, message='User must be in cvsextras or cvsadmin')
        approved = self._user_can_set_acls(identity, pkg)
        if not approved:
            return dict(status=False, message=
                    '%s is not allowed to approve Package ACLs' %
                    identity.current.user.display_name)

        personAcl = self._create_or_modify_acl(pkg, personid, newAcl,
                status

        # Get the human name and username for the person whose acl we changed
        (user, groups) = self.fas.get_user_info(personid)
        # Make sure a log is created in the db as well.
        logMessage = u'%s (%s) has set the %s acl on %s (%s %s) to %s for %s (%s)' % (
                    identity.current.user.display_name,
                    identity.current.user_name, newAcl, pkg.package.name,
                    pkg.collection.name, pkg.collection.version, statusname,
                    user['human_name'], user['username'])
        log = model.PersonPackageListingAclLog(identity.current.user.user_id,
                status.statuscodeid, logMessage)
        log.acl = personAcl

        try:
            session.flush()
        except sqlalchemy.exceptions.SQLError, e:
            # An error was generated
            return dict(status=False,
                    message='Not able to create acl %s on %s with status %s' \
                            % (newAcl, pkgid, statusname))
        # Send a log to people interested in this package as well
        self._send_log_msg(logMessage, '%s set to %s for %s' % (newAcl,
            statusname, user['human_name']), identity.current.user,
            (pkg,), otherEmail=(user['email'],))

        return dict(status=True)

    @expose('json')
    # Check that the requestor is in a group that could potentially set ACLs.
    @identity.require(identity.not_anonymous())
    def toggle_groupacl_status(self, containerId):
        '''Set the groupacl to determine whether the group can commit.

        WARNING: Do not use changeAcl.status in this method.  There is a high
        chance that it will be out of sync with the current statuscode after
        the status is set.  Updating changeAcl.status at the same time as we
        update changeAcl.statuscodeid makes this method take 10-11s instead of
        <1s.

        If you cannot live without changeAcl.status, try flushing the session
        after changeAcl.statuscodeid is set and see if that can automatically
        refresh the status without the performance hit.
        '''
        # Pull apart the identifier
        pkgListId, groupId, aclName = containerId.split(':')
        pkgListId = int(pkgListId)
        groupId = int(groupId)

        # Make sure the package listing exists
        pkg = model.PackageListing.get_by(id=pkgListId)
        if not pkg:
            return dict(status=False,
                    message='Package Listing %s does not exist' % pkgListId)

        # Check whether the user is allowed to set this
        if not identity.in_any_group('cvsextras', 'cvsadmin'):
            return dict(status=False, message='User must be in cvsextras or cvsadmin')
        approved = self._user_can_set_acls(identity, pkg)
        if not approved:
            return dict(status=False, message=
                    '%s is not allowed to approve Package ACLs' %
                    identity.current.user.display_name)

        # Make sure the group exists
        # Note: We don't let every group in the FAS have access to packages.
        if groupId not in self.groups:
            return dict(status=False, message='%s is not a group that can commit'
                    ' to packages' % groupId)
       
        # See if the group has a record
        changeGroup = None
        changeAcl = None
        approvedStatus = model.StatusTranslation.get_by(statusname='Approved')
        deniedStatus = model.StatusTranslation.get_by(statusname='Denied')
        for group in pkg.groups:
            if group.groupid == groupId:
                changeGroup = group
                # See if the group has an acl
                for acl in group.acls:
                    if acl.acl == aclName:
                        changeAcl = acl
                        # toggle status
                        if acl.status.translations[0].statusname == 'Approved':
                            changeAcl.statuscode = deniedStatus.statuscodeid
                        else:
                            changeAcl.statuscode = approvedStatus.statuscodeid
                        ### WARNING: At this point changeAcl.status is out of
                        # sync with changeAcl.statuscode.  There is a large
                        # performance penalty to setting it here.
                        # If you need it, try doing a session.flush() here and
                        # repull the information from the database.
                        break
                if not changeAcl:
                    # if no acl yet create it
                    changeAcl = model.GroupPackageListingAcl(aclName,
                            approvedStatus.statuscodeid)
                    changeAcl.grouppackagelisting = changeGroup
                break

        if not changeGroup:
            # No record for the group yet, create it
            changeGroup = model.GroupPackageListing(groupId, pkgListId)
            changeAcl = model.GroupPackageListingAcl(aclName,
                    approvedStatus.statuscodeid)
            changeAcl.grouppackagelisting = changeGroup
        
        ### WARNING: changeAcl.status is very likely out of sync at this point.
        # See the docstring for an explanation.

        # Make sure a log is created in the db as well.
        statusname = model.StatusTranslation.get_by(
                statuscodeid=changeAcl.statuscode).statusname
        logMessage = '%s (%s) has set the %s acl on %s (%s %s) to %s for %s' % (
                    identity.current.user.display_name,
                    identity.current.user_name, aclName, pkg.package.name,
                    pkg.collection.name, pkg.collection.version, statusname,
                    self.groups[changeGroup.groupid])
        log = model.GroupPackageListingAclLog(identity.current.user.user_id,
                changeAcl.statuscode, logMessage)
        log.acl = changeAcl

        try:
            session.flush()
        except sqlalchemy.exceptions.SQLError, e:
            # An error was generated
            return dict(status=False,
                    message='Not able to create acl %s on %s with status %s' \
                            % (newAcl, pkgid, status))

        # Send a log to people interested in this package as well
        self._send_log_msg(logMessage, '%s set to %s for %s' % (aclName,
            statusname, self.groups[changeGroup.groupid]),
            identity.current.user, (pkg,))

        return dict(status=True,
                newAclStatus=statusname)

    @expose('json')
    # Check that we have a tg.identity, otherwise you can't set any acls.
    @identity.require(identity.not_anonymous())
    def toggle_acl_request(self, containerId):
        # Make sure package exists
        pkgListId, aclName = containerId.split(':')
        pkgListing = model.PackageListing.get_by(id=pkgListId)
        if not pkgListing:
            return dict(status=False, message='No such package listing %s' % pkgListId)

        # See if the Person is already associated with the pkglisting.
        person = model.PersonPackageListing.get_by(packagelistingid=pkgListId,
                userid=identity.current.user.user_id)
        awaitingStatus = model.StatusTranslation.get_by(
                statusname='Awaiting Review')
        obsoleteStatus = model.StatusTranslation.get_by(statusname='Obsolete')
        if not person:
            # There was no association, create it.
            person = model.PersonPackageListing(
                    identity.current.user.user_id, pkgListId)
            personAcl = model.PersonPackageListingAcl(aclName,
                    awaitingStatus.statuscodeid)
            personAcl.personpackagelisting = person
            aclStatus = 'Awaiting Review'
        else:
            # Check whether the person already has this acl
            aclSet = False
            for acl in person.acls:
                if acl.acl == aclName:
                    # Acl already exists, set the status
                    personAcl = acl
                    if obsoleteStatus.statuscodeid == acl.statuscode:
                        acl.statuscode = awaitingStatus.statuscodeid
                        aclStatus = 'Awaiting Review'
                    else:
                        acl.statuscode = obsoleteStatus.statuscodeid
                        aclStatus = ''
                    aclSet = True
                    break
            if not aclSet:
                # Create a new acl
                personAcl = model.PersonPackageListingAcl(aclName,
                        awaitingStatus.statuscodeid)
                personAcl.personpackagelisting = person
                aclStatus = 'Awaiting Review'

        # Make sure a log is created in the db as well.
        if aclStatus == 'Awaiting Review':
            aclAction = 'requested'
        else:
            aclAction = 'given up'
        logMessage = '%s (%s) has %s the %s acl on %s (%s %s)' % (
                    identity.current.user.display_name,
                    identity.current.user_name, aclAction, aclName,
                    pkgListing.package.name, pkgListing.collection.name,
                    pkgListing.collection.version)
        log = model.PersonPackageListingAclLog(identity.current.user.user_id,
                personAcl.statuscode, logMessage)
        log.acl = personAcl

        try:
            session.flush()
        except sqlalchemy.exceptions.SQLError, e:
            # Probably the acl is mispelled
            return dict(status=False,
                    message='Not able to create acl %s for %s on %s' %
                        (aclName, identity.current.user.user_id,
                        pkgListId))

        # Send a log to the commits list as well
        self._send_log_msg(logMessage, '%s has %s %s for %s' % (
                    identity.current.user.display_name, aclAction, aclName,
                    pkgListing.package.name), identity.current.user,
                    (pkgListing,))

        # Return the new value
        return dict(status=True, personId=identity.current.user.user_id,
                aclStatusFields=self.aclStatusTranslations, aclStatus=aclStatus)

    @expose(allow_json=True)
    # Check that we have a tg.identity, otherwise you can't set any acls.
    @identity.require(identity.not_anonymous())
    def add_package(self, package, owner, summary):
        '''Add a new package to the database.
        '''
        # Check that the tg.identity is allowed to set themselves as owner
        if not identity.in_any_group('cvsadmin'):
            return dict(status=False, message='User must be in cvsadmin')

        # Make sure the package doesn't already exist
        pkg = model.Package.get_by(name=package)
        if pkg:
            return dict(status=False, message='Package %s already exists' % package)

        approvedStatus = model.StatusTranslation.get_by(statusname='Approved')
        deniedStatus = model.StatusTranslation.get_by(statusname='Denied')
        addedStatus = model.StatusTranslation.get_by(statusname='Added')

        develCollection = model.Collection.get_by(name='Fedora',
                version='devel')
        try:
            person, group = self.fas.get_user_info(owner)
        except AuthError, e:
            return dict(status=False, message='Specified owner %s does not have a Fedora Account' % owner)

        # Create the package
        pkg = model.Package(package, summary, approvedStatus.statuscodeid)
        pkgListing = model.PackageListing(person['id'],
                approvedStatus.statuscodeid)
        pkgListing.collection = develCollection
        pkgListing.package = pkg
        cvsextrasListing = model.GroupPackageListing(self.groups['cvsextras'])
        cvsextrasListing.packagelisting = pkgListing
        cvsextrasCommitAcl = model.GroupPackageListingAcl('commit', 
                deniedStatus.statuscodeid)
        cvsextrasCommitAcl.grouppackagelisting = cvsextrasListing
        cvsextrasBuildAcl = model.GroupPackageListingAcl('build',
                approvedStatus.statuscodeid)
        cvsextrasBuildAcl.grouppackagelisting = cvsextrasListing
        cvsextrasCheckoutAcl = model.GroupPackageListingAcl('checkout',
                approvedStatus.statuscodeid)
        cvsextrasCheckoutAcl.grouppackagelisting = cvsextrasListing

        # Create a log of changes
        logs = []
        pkgLogMessage = '%s (%s) has added Package %s with summary %s' % (
                identity.current.user.display_name,
                identity.current.user_name,
                pkg.name,
                pkg.summary)
        logs.append(pkgLogMessage)
        pkgLog = model.PackageLog(
                identity.current.user.user_id, addedStatus.statuscodeid,
                pkgLogMessage)
        pkgLog.package = pkg
        pkgLogMessage = '%s (%s) has approved Package %s' % (
                identity.current.user.display_name,
                identity.current.user_name,
                pkg.name)
        logs.append(pkgLogMessage)
        pkgLog = model.PackageLog(
                identity.current.user.user_id, approvedStatus.statuscodeid,
                pkgLogMessage)
        pkgLog.package = pkg

        pkgLogMessage = '%s (%s) has added a %s %s branch for %s with an owner of %s' % (
                    identity.current.user.display_name,
                    identity.current.user_name,
                    pkgListing.collection.name,
                    pkgListing.collection.version,
                    pkgListing.package.name,
                    owner)
        logs.append(pkgLogMessage)
        pkgListLog = model.PackageListingLog(
                identity.current.user.user_id, addedStatus.statuscodeid,
                pkgLogMessage
                )
        pkgListLog.listing = pkgListing

        pkgLogMessage = '%s (%s) has approved %s in %s %s' % (
                    identity.current.user.display_name,
                    identity.current.user_name,
                    pkgListing.package.name,
                    pkgListing.collection.name,
                    pkgListing.collection.version)
        logs.append(pkgLogMessage)
        pkgListLog = model.PackageListingLog(
                identity.current.user.user_id, approvedStatus.statuscodeid,
                pkgLogMessage
                )
        pkgListLog.listing = pkgListing

        pkgLogMessage = '%s (%s) has approved Package %s' % (
                identity.current.user.display_name,
                identity.current.user_name,
                pkg.name)
        logs.append(pkgLogMessage)
        pkgLog = model.PackageLog(
                identity.current.user.user_id, approvedStatus.statuscodeid,
                pkgLogMessage)
        pkgLog.package = pkg

        for changedAcl in (cvsextrasCommitAcl, cvsExtrasBuildAcl,
                cvsextrasCheckoutAcl):
            pkgLogMessage = '%s (%s) has set %s to %s for %s on %s (%s %s)' % (
                    identity.current.user.display_name,
                    identity.current.user_name,
                    changedAcl.acl,
                    changedAcl.status.translations[0].statusname,

                    self.groups[changedAcl.grouppackagelisting.groupid],
                    pkgListing.package.name,
                    pkgListing.collection.name,
                    pkgListing.collection.version)
            pkgLog = model.GroupPackageListingAclLog(
                    identity.current.user.user_id,
                    changedAcl.status.statuscodeid, pkgLogMessage)
            pkgLog.acl = changedAcl
            logs.append(pkgLogMessage)

        try:
            session.flush()
        except sqlalchemy.exceptions.SQLError, e:
            return dict(status=False,
                    message='Unable to create PackageListing(%s, %s, %s, %s)' %
                        (pkg.id, develCollection.id, person['id'],
                        approvedStatus.statuscodeid))

        # Send notification of the new package
        self._send_log_msg('\n'.join(logs),
                '%s has added package %s for %s' % (
                    identity.current.user.display_name, pkg.name, owner),
                identity.current.user, (pkgListing,))

        # Return the new values
        return dict(status=True, package=pkg, packageListing=pkgListing)

    @expose(allow_json=True)
    # Check that we have a tg.identity, otherwise you can't set any acls.
    @identity.require(identity.not_anonymous())
    def edit_package(self, package, **changes):
        '''Add a new package to the database.
        '''
        # Check that the tg.identity is allowed to set themselves as owner
        if not identity.in_any_group('cvsadmin'):
            return dict(status=False, message='User must be in cvsadmin')

        # Log message for all owners
        pkgLogMsg = None
        # Log message for owners of a branch
        pkgListLogMsg = {}

        # Make sure the package exists
        pkg = model.Package.get_by(name=package)
        if not pkg:
            return dict(status=False, message='Package %s does not exist' % package)
        # No changes to make
        if not changes:
            return dict(status=True, package=pkg)

        modifiedStatus = model.StatusTranslation.get_by(statusname='Modified')
        # Change the summary
        if 'summary' in changes:
            pkg.summary = changes['summary']
            logMessage = '%s (%s) set package %s summary to %s' % (
                    identity.current.user.display_name,
                    identity.current.user_name, package, changes['summary'])
            log = model.PackageLog(identity.current.user.user_id,
                    modifiedStatus.statuscodeid, logMessage)
            log.package = pkg
            pkgLogMsg = logMessage

        # Retrieve the owner for use later
        person = None
        ownerId = None
        if 'owner' in changes:
            try:
                person, group = self.fas.get_user_info(changes['owner'])
            except AuthError, e:
                return dict(status=False, message='Specified owner %s does not have a Fedora Account' % changes['owner'])
            ownerId = person['id']

        if 'collections' in changes:
            # Save a reference to the pkgListings in here
            listings = []
            # Get id for statuses
            approvedStatus = model.StatusTranslation.get_by(
                    statusname='Approved')
            deniedStatus = model.StatusTranslation.get_by(
                    statusname='Denied')
            addedStatus = model.StatusTranslation.get_by(statusname='Added')
            ownedStatus = model.StatusTranslation.get_by(statusname='Owned')

            # Retrieve the id of the initial package owner
            if not ownerId:
                develCollection = model.Collection.get_by(name='Fedora',
                        version='devel')
                develPackage = model.PackageListing.get_by(packageid=pkg.id,
                        collectionid=develCollection.id)
                ownerId = develPackage.owner

            # Turn JSON collection data back to python
            collectionData = simplejson.loads(changes['collections'])
            for collectionName in collectionData:
                for version in collectionData[collectionName]:
                    # Check if collection/version exists
                    collection = model.Collection.get_by(name=collectionName,
                            version=version)
                    if not collection:
                        return dict(status=False,
                                message='No collection %s %s' %
                                (collectionName, version))

                    # Create the packageListing if necessary
                    pkgListing = model.PackageListing.get_by(
                            collectionid=collection.id, packageid=pkg.id)
                    if not pkgListing:
                        pkgListing = model.PackageListing(ownerId,
                                approvedStatus.statuscodeid)
                        pkgListing.package = pkg
                        pkgListing.collection = collection
                        cvsextrasListing = model.GroupPackageListing(
                                self.groups['cvsextras'])
                        cvsextrasListing.packagelisting = pkgListing
                        cvsextrasCommitAcl = model.GroupPackageListingAcl(
                                'commit', deniedStatus.statuscodeid)
                        cvsextrasCommitAcl.grouppackagelisting=cvsextrasListing
                        cvsextrasBuildAcl = model.GroupPackageListingAcl(
                                'build', approvedStatus.statuscodeid)
                        cvsextrasBuildAcl.grouppackagelisting=cvsextrasListing
                        cvsextrasCheckoutAcl = model.GroupPackageListingAcl(
                                'checkout', approvedStatus.statuscodeid)
                        cvsextrasCheckoutAcl.grouppackagelisting = \
                                cvsextrasListing

                        logMessage = '%s (%s) added a %s %s branch for %s' % (
                                identity.current.user.display_name,
                                identity.current.user_name,
                                pkgListing.collection.name,
                                pkgListing.collection.version,
                                pkgListing.package.name)
                        pkgLog = model.PackageListingLog(
                                identity.current.user.user_id,
                                addedStatus.statuscodeid,
                                logMessage
                                )
                        pkgLog.listing = pkgListing
                        pkgListLogMsg[pkgListing] = [logMessage]
                        for changedAcl in (cvsextrasCommitAcl,
                                cvsExtrasBuildAcl, cvsextrasCheckoutAcl):
                            pkgLogMessage = '%s (%s) has set %s to %s for %s on %s (%s %s)' % (
                                    identity.current.user.display_name,
                                    identity.current.user_name,
                                    changedAcl.acl,
                                    changedAcl.status.translations[0].statusname,
                                    self.groups[changedAcl.grouppackagelisting.groupid],
                                    pkgListing.package.name,
                                    pkgListing.collection.name,
                                    pkgListing.collection.version)
                            pkgLog = model.GroupPackageListingAclLog(
                                    identity.current.user.user_id,
                                    changedAcl.status.statuscodeid, pkgLogMessage)
                            pkgLog.acl = changedAcl
                            pkgListLog[pkgListing.append(pkgLogMessage)


                    # Save a reference to all pkgListings
                    listings.append(pkgListing)

        # If ownership, change the owners
        if 'owner' in changes:
            # Already retrieved owner into person
            for pkgList in listings:
                pkgList.owner = person['id']
                logMessage = '%s (%s) changed owner of %s in %s %s to %s' % (
                        identity.current.user.display_name,
                        identity.current.user_name,
                        pkgList.package.name,
                        pkgList.collection.name, pkgList.collection.version,
                        person['username']
                        )
                pkgLog = model.PackageListingLog(
                        identity.current.user.user_id,
                        ownedStatus.statuscodeid,
                        logMessage
                        )
                pkgLog.listing = pkgList
                try:
                    pkgListLogMsg[pkgList].append(logMessage)
                except KeyError:
                    pkgListLogMsg[pkgList] = [logMessage]
        
        # Change the cclist
        if 'ccList' in changes:
            ccList = simplejson.loads(changes['ccList'])
            for username in ccList:
                # Lookup the list members in fas
                try:
                    person, groups = self.fas.get_user_info(username)
                except AuthError, e:
                    return dict(status=False,
                            message='New cclist member %s is not in FAS' % username)
                # Add Acls for them to the packages
                for pkgList in listings:
                    for acl in ('watchbugzilla', 'watchcommits'):
                        personAcl = self._create_or_modify_acl(pkgList,
                                person['id'], acl, approvedStatus)
                        logMessage = '%s (%s) approved %s on %s (%s %s) for %s' % (
                                identity.current.user.display_name,
                                identity.current.user_name,
                                acl, pkgList.package.name,
                                pkgList.collection.name,
                                pkgList.collection.version,
                                person['username']
                                )
                        pkgLog = model.PersonPackageListingAclLog(
                                identity.current.user.user_id,
                                approvedStatus.statuscodeid,
                                logMessage
                                )
                        pkgLog.acl = personAcl
                        try:
                            pkgListLogMsg[pkgList].append(logMessage)
                        except KeyError:
                            pkgListLogMsg[pkgList] = [logMessage]

        # Change the comaintainers
        if 'comaintList' in changes:
            comaintList = simplejson.loads(changes['comaintList'])
            for username in comaintList:
                # Lookup the list members in fas
                try:
                    person, groups = self.fas.get_user_info(username)
                except AuthError, e:
                    return dict(status=False, message='New comaintainer %s does not have a Fedora Account' % username)
                # Add Acls for them to the packages
                for pkgList in listings:
                    for acl in ('watchbugzilla', 'watchcommits', 'commit', 'build', 'approveacls', 'checkout'):

                        personAcl = self._create_or_modify_acl(pkgList,
                                person['id'], acl, approvedStatus)

                        # Make sure a log is created in the db as well.
                        logMessage = u'%s (%s) approved %s on %s (%s %s) for %s' % (
                                identity.current.user.display_name,
                                identity.current.user_name, acl,
                                pkgList.package.name,
                                pkgList.collection.name,
                                pkgList.collection.version,
                                person['username'])
                        pkgLog = model.PersonPackageListingAclLog(
                                identity.current.user.user_id,
                                approvedStatus.statuscodeid,
                                logMessage
                                )
                        pkgLog.acl = personAcl
                        try:
                            pkgListLogMsg[pkgList].append(logMessage)
                        except KeyError:
                            pkgListLogMsg[pkgList] = [logMessage]

        if 'groups' in changes:
            # Change whether the group can commit to cvs.
            groupList = simplejson.loads(changes['groups'])
            for group in groupList:
                # We don't let every group commit
                try:
                    groupId = self.groups[group]
                except KeyError:
                    return dict(status=False, message='Group %s is not allowed to commit' % group)

                if groupList[group] == True:
                    status = approvedStatus
                else:
                    status = deniedStatus

                groupAcl = self._create_or_modify_group_acl(pkgList, groupId,
                    'commit', status)

                # Make sure a log is created in the db as well.
                logMessage = u'%s (%s) %s %s for commit access on %s (%s %s)' % (
                        identity.current.user.display_name,
                        identity.current.user_name, status, group
                        pkgList.package.name,
                        pkgList.collection.name,
                        pkgList.collection.version)
                pkgLog = model.GroupPackageListingAclLog(
                        identity.current.user.user_id,
                        status.statuscodeid,
                        logMessage
                        )
                pkgLog.acl = groupAcl
                try:
                    pkgListLogMsg[pkgList].append(logMessage)
                except KeyError:
                    pkgListLogMsg[pkgList] = [logMessage]

        try:
            session.flush()
        except sqlalchemy.exceptions.SQLError, e:
            # An error was generated
            return dict(status=False,
                    message='Not able to create acl %s on %s with status %s' \
                            % (newAcl, pkgid, status))
        # Send a log to people interested in this package as well
        if pkgLogMsg:
            self._send_log_msg(pkgLogMsg, '%s updated summary for %s' % (
                identity.current.user.display_name, pkg.name),
                identity.current.user, pkg.listings)
        for pkgListing in pkgListLogMsg.keys():
            self._send_log_msg('\n'.join(pkgListLogMsg[pkgListing]),
                    '%s updated %s (%s, %s)' % (
                        identity.current.user.display_name, pkg.name,
                        pkgListing.collection.name,
                        pkgListing.collection.version),
                    identity.current.user, (pkgListing,))
        return dict(status=True)