-- Fedora Package Database
-- Version 0.4

drop database pkgdb;
create database pkgdb with encoding 'UTF8';
\c pkgdb

-- create function plpgsql_call_handler() returns language_handler as
-- '$libdir/plpgsql' language C;
-- create function plpgsql_validator(oid) returns void as '$libdir/plpgsql'
-- language C;

-- create trusted procedural language plpgsql
--  handler plpgsql_call_handler
--  validator plpgsql_validator;

-- Status of the various components.
--
-- Fields:
-- :id: The id of a statusCode.  Can be used to reference a status from another
--   table.
create table StatusCode (
  id serial primary key
);

-- Contains translations of the status codes into natural languages.
--
-- Fields:
-- :statusCodeId: The id of the status that is referenced from other tables.
-- :language: The language code for the natural language used.
-- :statusName: The translated status code.
-- :description: A longer description of what the status means.  May be used
--    in tooltips or help pages.
create table StatusCodeTranslation (
  statusCodeId integer not null,
  language varchar (32) not null default 'C',
  statusName text not null,
  description text null,
  primary key (statusCodeId, language),
  foreign key (statusCodeId) references StatusCode(id)
    on delete cascade on update cascade
);

begin;
  insert into StatusCode default values;
  insert into StatusCodeTranslation (statusCodeId, statusName)
    values (lastval(), 'Active');
commit;
begin;
  insert into StatusCode default values;
  insert into StatusCodeTranslation (statusCodeId, statusName)
    values (lastval(), 'Added');
commit;
begin;
  insert into StatusCode default values;
  insert into StatusCodeTranslation (statusCodeId, statusName)
    values (lastval(), 'Approved');
commit;
begin;
  insert into StatusCode default values;
  insert into StatusCodeTranslation (statusCodeId, statusName)
    values (lastval(), 'Awaiting Branch');
commit;
begin;
  insert into StatusCode default values;
  insert into StatusCodeTranslation (statusCodeId, statusName)
    values (lastval(), 'Awaiting Development');
commit;
begin;
  insert into StatusCode default values;
  insert into StatusCodeTranslation (statusCodeId, statusName)
    values (lastval(), 'Awaiting QA');
commit;
begin;
  insert into StatusCode default values;
  insert into StatusCodeTranslation (statusCodeId, statusName)
    values (lastval(), 'Awaiting Publish');
commit;
begin;
  insert into StatusCode default values;
  insert into StatusCodeTranslation (statusCodeId, statusName)
    values (lastval(), 'Awaiting Review');
commit;
begin;
  insert into StatusCode default values;
  insert into StatusCodeTranslation (statusCodeId, statusName)
    values (lastval(), 'EOL');
commit;
begin;
  insert into StatusCode default values;
  insert into StatusCodeTranslation (statusCodeId, statusName)
    values (lastval(), 'Denied');
commit;
begin;
  insert into StatusCode default values;
  insert into StatusCodeTranslation (statusCodeId, statusName)
    values (lastval(), 'Maintenence');
commit;
begin;
  insert into StatusCode default values;
  insert into StatusCodeTranslation (statusCodeId, statusName)
    values (lastval(), 'Obsolete');
commit;
begin;
  insert into StatusCode default values;
  insert into StatusCodeTranslation (statusCodeId, statusName)
    values (lastval(), 'Rejected');
commit;
begin;
  insert into StatusCode default values;
  insert into StatusCodeTranslation (statusCodeId, statusName)
    values (lastval(), 'Removed');
commit;
begin;
  insert into StatusCode default values;
  insert into StatusCodeTranslation (statusCodeId, statusName)
    values (lastval(), 'Under Development');
commit;
begin;
  insert into StatusCode default values;
  insert into StatusCodeTranslation (statusCodeId, statusName)
    values (lastval(), 'Under Review');
commit;

-- Create a trigger to update the available log actions depending on the
-- available status codes for that table.
create or replace function add_status_to_log() returns trigger AS $update_log$
DECLARE
  cmd text;
  tableName text;
BEGIN
  tableName := regexp_replace(TG_TABLE_NAME, 'StatusCode$', 'LogStatusCode');
  if (TG_OP = 'INSERT') then
    cmd := 'insert into ' || tableName || ' values (' || NEW.statusCodeId ||')';
    execute cmd;
    return NEW;
  elsif (TG_OP = 'DELETE') then
    cmd := 'delete from ' || tableName || ' where statusCodeId = ' || OLD.statusCodeId;
    execute cmd;
    return OLD;
  elsif (TG_OP = 'UPDATE') then
    cmd := 'update ' || tableName || ' set statusCodeId = ' || NEW.statusCodeId || ' where statusCodeId = ' || OLD.statusCodeId;
    execute cmd;
    return NEW;
  end if;
  return NULL;
END;
$update_log$ language plpgsql;

-- Holds status codes specific to a particular table.
-- Insert the status codes that a particular table can have into each of these
-- tables.  This allows us to use foreign key constraints to limit what the
-- db sees and also allows an easy query to return the human readable
-- statusNames for the table.
begin;
  create table CollectionStatusCode as select StatusCodeId
    from StatusCodeTranslation where statusName in ('Under Development',
      'Active', 'Maintenance', 'EOL', 'Rejected');
  alter table CollectionStatusCode add primary key (statusCodeId);
  alter table CollectionStatusCode add foreign key (statusCodeId)
    references StatusCode(id) on delete cascade on update cascade;
commit;

begin;
  create table PackageStatusCode as select StatusCodeId 
    from StatusCodeTranslation where statusName in ('Awaiting Review',
      'Under Review', 'Approved', 'Denied');
  alter table PackageStatusCode add primary key (statusCodeId);
  alter table PackageStatusCode add foreign key (statusCodeId)
    references StatusCode(id) on delete cascade on update cascade;
commit;
begin;
  create table PackageLogStatusCode as
    select StatusCodeId from PackageStatusCode
    union select StatusCodeId from StatusCodeTranslation
    where statusName in ('Added', 'Removed');
  alter table PackageLogStatusCode add primary key (statusCodeId);
commit;
create trigger add_status_to_action after insert or delete or update
  on PackageStatusCode
  for each row execute procedure add_status_to_log();

begin;
  create table PackageBuildStatusCode as select StatusCodeId 
    from StatusCodeTranslation where statusName in ('Awaiting Development',
      'Awaiting Review', 'Awaiting QA', 'Awaiting Publish', 'Approved',
      'Denied', 'Obsolete');
  alter table PackageBuildStatusCode add primary key (statusCodeId);
  alter table PackageBuildStatusCode add foreign key (statusCodeId)
    references StatusCode(id) on delete cascade on update cascade;
commit;
begin;
  create table PackageBuildLogStatusCode as
    select StatusCodeId from PackageBuildStatusCode
    union select StatusCodeId from StatusCodeTranslation
    where statusName in ('Added');
  alter table PackageBuildLogStatusCode add primary key (statusCodeId);
commit;
create trigger add_status_to_action after insert or delete or update
  on PackageBuildStatusCode
  for each row execute procedure add_status_to_log();

begin;
  create table PackageListingStatusCode as select StatusCodeId 
    from StatusCodeTranslation where statusName in ('Awaiting Review',
      'Awaiting Branch', 'Approved', 'Denied', 'Obsolete');
  alter table PackageListingStatusCode add primary key (statusCodeId);
  alter table PackageListingStatusCode add foreign key (statusCodeId)
    references StatusCode(id) on delete cascade on update cascade;
commit;
begin;
  create table PackageListingLogStatusCode as
    select StatusCodeId from PackageListingStatusCode
    union select StatusCodeId from StatusCodeTranslation
    where statusName in ('Added', 'Removed');
  alter table PackageListingLogStatusCode add primary key (statusCodeId);
commit;
create trigger add_status_to_action after insert or delete or update
  on PackageListingStatusCode
  for each row execute procedure add_status_to_log();

begin;
  create table PackageACLStatusCode as select StatusCodeId 
    from StatusCodeTranslation where statusName in ('Awaiting Review',
      'Approved', 'Denied', 'Obsolete');
  alter table PackageACLStatusCode add primary key (statusCodeId);
  alter table PackageACLStatusCode add foreign key (statusCodeId)
    references StatusCode(id) on delete cascade on update cascade;
commit;
begin;
  create table PackageACLLogStatusCode as
    select StatusCodeId from PackageACLStatusCode
    union select StatusCodeId from StatusCodeTranslation
    where statusName in ('Added');
  alter table PackageACLLogStatusCode add primary key (statusCodeId);
commit;
create trigger add_status_to_action after insert or delete or update
  on PackageACLStatusCode
  for each row execute procedure add_status_to_log();

-- Collection of packages.
-- 
-- Collections are a set of packages.  They can represent the packages in a
-- distro, in a SIG, or on a CD.
--
-- Fields:
-- :name: "Fedora Core", "Fedora Extras", "Python", "GNOME" or whatever
--   names-for-groupings you want.  If this is for a grouping that a SIG is
--   interested in, the name should make this apparent.  If it is for one
--   of the distributions it should be the name for the Product that will
--   be used in Bugzilla as well.
-- :version: The release of the `Collection`.  If the `Collection` doesn't
--   have releases (for instance, SIGs), version should be 0.
-- :status: Is the collection being worked on or is it inactive.
-- :owner: Creator, QA Contact, or other account that is in charge of the
--   collection.  This is a foreign key to an account id number.  (Since the
--   accounts live in a separate db we can't have the db enforce validity.)
-- :publishURLTemplate: URL to packages built for this collection with
--   [ARCH] and [PACKAGE] as special symbols that can be substituted from the
--   specific package built.
-- :pendingURLTemplate: URL to packages built but not yet in the repository
--   with [ARCH] and [PACKAGE] as special symbols that can be substituted from
--   the specific package built.
-- :summary: Brief description of the collection.
-- :description: Longer description of the collection.
create table Collection (
  id serial primary key,
  name text not null,
  version text not null,
  status integer not null,
  owner integer not null,
  publishURLTemplate text,
  pendingURLTemplate text,
  summary text,
  description text,
  foreign key (status) references CollectionStatusCode (statusCodeId)
    on delete restrict on update cascade,
  unique (name, version)
);

-- `Collection`s with their own branch in the VCS have extra information.
--
-- Fields:
-- :collectionId: `Collection` this branch provides information for.
-- :branchName: Name of the branch in the VCS ("FC-3", "devel")
-- :distTag: DistTag used in the buildsystem (".fc3", ".fc6")
-- :parent: Many collections are branches of other collections.  This field
--    records the parent collection to branch from.

create table Branch (
  collectionId integer not null primary key,
  branchName varchar(32) unique not null,
  distTag varchar(32) unique not null,
  parentId integer,
  foreign key (parentId) references Collection(id)
    on delete set null on update cascade,
  foreign key (collectionId) references Collection(id)
    on delete cascade on update cascade
);

-- Associate the packages in one collection with another collection.
--
-- This table is used to allow one `Collection` to be based on another with
-- certain packages that are overridden or not available in the `base`
-- `Collection`.  For instance, a `Collection` may be used to experiment with
-- a major version upgrade of python and all the dependent packages that need
-- to be rebuilt against it.  In this scenario, the base might be
-- "Fedora Core - devel".  The overlay "FC devel python3".  The overlay will
-- contain python packages that override what is present in the base.  Any
-- package that is not present in the overlay will also be searched for in
-- the base collection.
-- Once we're ready to commit to using the upgraded set of packages, we want
-- to merge them into devel.  To do this, we will actually move the packages
-- from the overlay into the base collection.  Probably, at this time, we
-- will also mark the overlay as obsolete.
--
-- Keeping things consistent is a bit problematic because we have to search for
-- for packages in the collection plus all the bases (an overlay can have
-- multiple bases) and any bases that they're overlays for.  SQL doesn't do
-- recursion -- in and of itself so we have to work around it in one of these
-- ways:
-- 1) Do the searching for packages in code; either a trigger on the server or
--    in any application code which looks at the database.
-- 2) Use a check constraint to only have one level of super/subset.  So if
--    devel contains python-2.5, devel cannot be a subset and python-2.5 cannot
--    be a superset to any other collection.  Have an insert trigger that
--    checks for this.
-- 3) Copy the packages.  When we make one collection a subset of another, add
--    all its packages including subset's packages to the superset.  Have an
--    insert trigger on packageList and packageListVer that check whether this
--    collection is a subset and copies the package to other collections.
-- Option 1, in application code may be the simplest to implement.  However,
-- option 3 has the benefit of running during insert rather than select.  As
-- always, doing something within the database rather than application logic
-- allows us to keep better control over the information.
--
-- * Note: Do not have an ondelete trigger as there may be overlap between the
-- packages in the parent and child collection.
--
-- Fields:
-- :overlay: The `Collection` which overrides packages in the base.
-- :base: The `Collection` which provides packages not explicitly listed in
--    `overlay`.
-- :priority: When searching for a package within a collection, first check the
--    `overlay`.  If not found check the lowest priority `base` collection and
--    any `base` Collections that belong to it.  Then check the next lowest
--    priority `base` until we find the package or run out. `base`s of the same
--    `overlay` with the same `priority` are searched in an undefined order.
create table CollectionSet (
  overlay integer,
  base integer,
  priority integer default 0,
  primary key (overlay, base),
  foreign key (overlay) references Collection(id)
    on delete cascade on update cascade,
  foreign key (base) references Collection(id)
    on delete cascade on update cascade
);

-- Data associated with an individual package.
-- 
-- Fields:
-- :id: Unique primary key
-- :name: Name of the package
-- :summary: Brief summary of what the package is
-- :description: Longer description of the package
-- :reviewURL: URL for the review ticket for this package
-- :status: Is the package ready to be built, in review, or other?
create table Package (
  id serial primary key,
  name text not null unique,
  summary text not null,
  description text,
  reviewURL text,
  status integer not null,
  foreign key (status) references PackageStatusCode(statusCodeId)
    on delete restrict on update cascade
);

-- Associates a `Package` with a `Collection`.
-- A package residing in a specific branch.
-- 
-- Fields:
-- :packageId: `Package` id that is in this `Collection`.
-- :collection: A `Collection` that holds this `Package`.
-- :owner: id from the accountsDB for the owner of the `Package` in this
--    `Collection`.  There is a special orphaned account to use if you want
--    to orphan the package.
-- :qacontact: Initial bugzilla QA Contact for this package.
-- :status: Whether the `Package` was entered in the `Collection`.
create table PackageListing (
  id serial primary key,
  packageId integer not null,
  collectionId integer not null,
  owner integer not null,
  qacontact integer,
  status integer not null,
  unique(packageId, collectionId),
  foreign key (packageId) references Package(id)
    on delete cascade on update cascade,
  foreign key (collectionId) references Collection(id)
    on delete cascade on update cascade,
  foreign key (status) references PackageListingStatusCode(statusCodeId)
    on delete restrict on update cascade
);

-- Specific version of a package to be built. 
--
-- Fields:
-- :id: Easily referenced primary key
-- :packageId: The package this is a specific build of.
-- :epoch: RPM Epoch for this release of the `Package`.
-- :version: RPM Version string.
-- :release: RPM Release string including any disttag value.
-- :status: What is happening with this particular version.
create table PackageBuild (
  id serial not null primary key,
  packageId integer not null,
  epoch text,
  version text not null,
  release text not null,
  status integer not null,
  unique (packageId, epoch, version, release),
  foreign key (packageId) references Package(id)
    on delete restrict on update cascade,
  foreign key (status) references PackageBuildStatusCode(StatusCodeId)
    on delete restrict on update cascade
);

-- Associate a particular build with a collection.
-- A built package may be part of multiple collections.
--
-- Fields:
-- :packageBuildId: The `PackageBuild` that is being added to a collection.
-- :packageListingId: The `PackageListing` that we're being added to.
create table PackageBuildListing (
  packageBuildId integer not null,
  packageListingId integer not null,
  primary key (packageBuildId, packageListingId),
  foreign key (packageBuildId) references PackageBuild(id)
    on delete cascade on update cascade,
  foreign key (packageListingId) references PackageListing(id)
    on delete cascade on update cascade
);

-- Make sure that the changes we're about to make don't associate a
-- PackageBuild and PackageListing that reference different packages.  This
-- really feels like I'm defining the PackageBuild or PackageListing tables
-- wrong but I haven't been able to find my error so this trigger will have to
-- do the trick.
create or replace function package_build_agreement() returns trigger AS
$pkg_build$
DECLARE
  pkgList_pid integer;
  pkgBuild_pid integer;
BEGIN
  if (TG_TABLE_NAME = 'PackageBuildListing') then
    -- Upon entering a new relationship between a Build and Listing, make sure
    -- they reference the same package.
    pkgList_pid := packageId from packageListing where id = NEW.packageListingId;
    pkgBuild_pid := packageId from packageBuildId where id = NEW.packageBuildId;
    if (pkgList_pid != pkgBuild_pid) then
      raise exception 'PackageBuild % and PackageListing % have to reference the same package', NEW.packageBuildId, NEW.packageListingId;
    end if;
  elsif (TG_TABLE_NAME = 'PackageBuild') then
    -- Disallow updating the packageId field of PackageBuild if it is
    -- associated with a PackageListing
    if (NEW.packageId != OLD.packageId) then
      select * from PackageBuildListing where PackageBuildId = NEW.id;
      if (FOUND) then
        raise exception 'Cannot update packageId when PackageBuild is referenced by a PackageListing';
      end if;
    end if;
  elsif (TG_TABLE_NAME = 'PackageListing') then
    -- Disallow updating the packageId field of PackageListing if it is
    -- associated with a PackageBuild
    if (NEW.packageId != OLD.packageId) then
      select * from PackageBuildListing where PackageListingId = NEW.id;
      if (FOUND) then
        raise exception 'Cannot update packageId when PackageListing is referenced by a PackageBuild';
      end if;
    end if;
  else
    raise exception 'Triggering table % is not one of PackageBuild, PackageListing, or PackageBuildListing', TG_TABLE_NAME;
  end if;
  return NEW;
END;
$pkg_build$ language plpgsql;

create trigger package_build_agreement_trigger before update or insert
  on PackageBuildListing
  for each row execute procedure package_build_agreement();

create trigger package_build_agreement_trigger before update
  on PackageListing
  for each row execute procedure package_build_agreement();

create trigger package_build_agreement_trigger before update
  on PackageBuild
  for each row execute procedure package_build_agreement();

-- Permissions for who can make various changes to the code.
-- We want to limit the access that a given person may have to edit the package
--
-- Fields:
-- :id: Primary key
-- :pkgListId: What package in what collection has this value.
-- :acl: The permission being set.
create table PackageACL (
  id serial primary key,
  packageListingId integer not null,
  acl text not null,
  unique (packageListingId, acl),
  foreign key (packageListingId) references PackageListing(id)
    on delete cascade on update cascade,
  check (acl in ('commit', 'build', 'watchbugzilla', 'watchcommits',
      'approveacls', 'checkout'))
);

-- Make the acl field non-updatable.  This prevents people from getting a
-- permission and then changing the type of permission to a different one.
create or replace function no_acl_update() returns TRIGGER as $no_acl$
BEGIN
  if (NEW.acl = OLD.acl) then
    return NEW;
  else
    raise exception 'Cannot update acl field';
  end if;
  return NULL;
END;
$no_acl$ LANGUAGE plpgsql;
create trigger no_acl_update_trigger before update on PackageACL
  for each row execute procedure no_acl_update();

-- ACLs that allow a person to do something
--
-- Fields:
-- :packageACLId: Inherit from an ACL record.
-- :userId: User id from the account system.
-- :status: Whether this permission is active.
create table PersonPackageACL (
  id serial primary key,
  packageACLId integer not null,
  userId integer not null,
  status integer not null,
  unique (packageACLId, userId),
  foreign key (packageACLId) references PackageACL (id)
    on delete cascade on update cascade,
  foreign key (status) references PackageACLStatusCode(statusCodeId)
    on delete restrict on update cascade
);

-- ACLs that allow a group to do something
--
-- Fields:
-- :packageACLId: Inherit from an ACL record.
-- :groupId: Group id from the account system.
-- :status: Whether this permission is active.
create table GroupPackageACL (
  id serial primary key,
  packageACLId integer not null,
  groupId integer not null,
  status integer not null,
  unique (packageACLId, groupId),
  foreign key (PackageACLId) references PackageACL (id)
    on delete cascade on update cascade,
  foreign key (status) references PackageACLStatusCode(statusCodeId)
    on delete restrict on update cascade
);
  
-- Log a change to the packageDB.
--
-- Fields:
-- :id: Primary key
-- :userId: Who made the change.
-- :changeTime: Time that the change occurred.
-- :description: Additional information about the change.
create table Log (
  id serial primary key,
  userId integer not null,
  changeTime timestamp default now() not null,
  description text
);

-- Log a change made to the Package table.
--
-- Fields:
-- :logId: The id of the log entry.
-- :packageId: The package that changed.
-- :action: What happened to the package.
create table PackageLog (
  logId integer primary key,
  packageId integer not null,
  action integer not null,
  foreign key (logId) references Log(id)
    on delete cascade on update cascade,
  foreign key (packageId) references Package(id)
    on delete restrict on update cascade,
  foreign key (action) references PackageLogStatusCode (statusCodeId)
    on delete restrict on update cascade
);

-- Log changes to packages in collections.
--
-- Fields:
-- :logId: The id of the log entry.
-- :packageListingId: The packageListing that changed.
-- :action: What happened to the package in the collection.
create table PackageListingLog (
  logId integer primary key,
  packageListingId integer not null,
  action integer not null,
  foreign key (logId) references Log (id)
    on delete cascade on update cascade,
  foreign key (packageListingId) references PackageListing(id)
    on delete restrict on update cascade,
  foreign key (action) references PackageListingLogStatusCode(statusCodeId)
    on delete restrict on update cascade
);

-- Log changes to built packages.
--
-- Fields:
-- :logId: The id of the log entry.
-- :packageBuildId: The `PackageBuild` that changed.
-- :action: What happened to the `PackageBuild`.
create table PackageBuildLog (
  logId integer primary key,
  packageBuildId integer not null,
  action integer not null,
  foreign key (action) references PackageBuildLogStatusCode(statusCodeId)
    on delete cascade on update cascade,
  foreign key (logId) references Log (id)
    on delete restrict on update cascade,
  foreign key (packageBuildId) references PackageBuild(id)
    on delete restrict on update cascade
);

-- Log changes to built package ACLs.
--
-- Fields:
-- :logId: The id of the log entry.
-- :packageBuildId: The `PackageACL` that changed.
-- :action: What happened to the ACLs for the package.
create table PersonPackageACLLog (
  logId integer primary key,
  personPackageACLId integer not null,
  action integer not null,
  foreign key (action) references PackageACLLogStatusCode(statusCodeId)
    on delete cascade on update cascade,
  foreign key (logId) references Log (id)
    on delete restrict on update cascade,
  foreign key (personPackageACLId) references PersonPackageACL(id)
    on delete restrict on update cascade
);

-- Log changes to built package ACLs.
--
-- Fields:
-- :logId: The id of the log entry.
-- :packageBuildId: The `PackageACL` that changed.
-- :action: What happened to the ACLs for the package.
create table GroupPackageACLLog (
  logId integer primary key,
  groupPackageACLId integer not null,
  action integer not null,
  foreign key (action) references PackageACLLogStatusCode(statusCodeId)
    on delete cascade on update cascade,
  foreign key (logId) references Log (id)
    on delete restrict on update cascade,
  foreign key (groupPackageACLId) references groupPackageACL(id)
    on delete restrict on update cascade
);

-- FIXME: Audit these grant settings to make sure we are giving out just the
-- permissions that we need.
-- pgsql 8.2:
-- grant connect on database pkgdb to pkgdbadmin;
grant select, insert, update, delete on PackageBuildListing to pkgdbadmin;
grant select, insert, update 
  on Collection, Branch, CollectionSet, Package, PackageBuild,
    PackageListing, PackageACL
  to pkgdbadmin;
grant select, insert
  on PersonPackageACL, GroupPackageACL, Log, PackageLog, PackageListingLog,
    PackageBuildLog, PersonPackageACLLog, GroupPackageACLLog
  to pkgdbadmin;

grant update
  on collection_id_seq, grouppackageacl_id_seq, log_id_seq, package_id_seq,
    packageacl_id_seq, packagebuild_id_seq, packagelisting_id_seq,
    personpackageacl_id_seq
  to pkgdbadmin;
grant select
  on StatusCode, StatusCodeTranslation, CollectionStatusCode,
    PackageStatusCode, PackageLogStatusCode, PackageBuildStatusCode,
    PackageBuildLogStatusCode, PackageListingStatusCode,
    PackageListingLogStatusCode, PackageACLStatusCode,
    PackageACLLogStatusCode
  to pkgdbadmin;

-- FIXME: In order to implement groups/categories/comps we need to have tables
-- that list the subpackages per collection.
--
-- create table SubPackage (
-- );
-- create table Category (
--   category text primary key
-- );
-- create table BuiltPackageCategories (
--   category text references Category(category),
--   builtPackageListingId references BuiltPackageListing(id),
-- );
--
-- FIXME: Add a CollectionLog table