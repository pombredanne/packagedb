CREATE TABLE iconnames (
    id serial NOT NULL PRIMARY KEY,
    name text NOT NULL UNIQUE
); 

GRANT SELECT, UPDATE, INSERT, DELETE ON TABLE iconnames TO pkgdbadmin;
GRANT SELECT, UPDATE ON iconnames_id_seq TO pkgdbadmin;
GRANT SELECT ON iconnames TO pkgdbreadonly;
GRANT SELECT, UPDATE ON iconnames_id_seq TO pkgdbreadonly;

CREATE TABLE themes (
    id serial NOT NULL PRIMARY KEY,
    name text NOT NULL UNIQUE
);                      

GRANT SELECT, UPDATE, INSERT, DELETE ON TABLE themes TO pkgdbadmin;
GRANT SELECT, UPDATE ON themes_id_seq TO pkgdbadmin;
GRANT SELECT ON themes TO pkgdbreadonly;
GRANT SELECT, UPDATE ON themes_id_seq TO pkgdbreadonly;

CREATE TABLE icons (
    id serial NOT NULL PRIMARY KEY,
    nameid integer NOT NULL,
    collectionid integer NOT NULL,
    themeid integer NOT NULL,     
    icon bytea NOT NULL
);                                

ALTER TABLE ONLY icons
    ADD CONSTRAINT icons_collectionid_fkey FOREIGN KEY (collectionid) REFERENCES collection(id) ON UPDATE CASCADE ON DELETE CASCADE;
ALTER TABLE ONLY icons
    ADD CONSTRAINT icons_nameid_fkey FOREIGN KEY (nameid) REFERENCES iconnames(id) ON UPDATE CASCADE ON DELETE CASCADE;
ALTER TABLE ONLY icons
    ADD CONSTRAINT icons_themeid_fkey FOREIGN KEY (themeid) REFERENCES themes(id) ON UPDATE CASCADE ON DELETE CASCADE;

GRANT SELECT, UPDATE, INSERT, DELETE ON TABLE icons TO pkgdbadmin;
GRANT SELECT, UPDATE ON icons_id_seq TO pkgdbadmin;
GRANT SELECT ON icons TO pkgdbreadonly;
GRANT SELECT, UPDATE ON icons_id_seq TO pkgdbreadonly;


CREATE TABLE apptypes (
    apptype varchar(32) NOT NULL PRIMARY KEY
    );
INSERT INTO apptypes (apptype) VALUES ('desktop');
INSERT INTO apptypes (apptype) VALUES ('unknown');
INSERT INTO apptypes (apptype) VALUES ('commandline');

GRANT SELECT, UPDATE, INSERT, DELETE ON TABLE apptypes TO pkgdbadmin;
GRANT SELECT ON apptypes TO pkgdbreadonly;

CREATE TABLE applications (
    id serial NOT NULL PRIMARY KEY,
    name text NOT NULL,
    description text NOT NULL,
    url text,
    apptype varchar(32) NOT NULL REFERENCES apptypes
            ON UPDATE CASCADE,
    desktoptype text,
    iconnameid integer,                    
    iconid integer,                        
    summary text                           
    );
   
ALTER TABLE ONLY applications
    ADD CONSTRAINT applications_iconid_fkey FOREIGN KEY (iconid) REFERENCES icons(id);
ALTER TABLE ONLY applications
    ADD CONSTRAINT applications_iconnameid_fkey FOREIGN KEY (iconnameid) REFERENCES iconnames(id);


GRANT SELECT, UPDATE, INSERT, DELETE ON TABLE applications TO pkgdbadmin;
GRANT SELECT, UPDATE ON applications_id_seq TO pkgdbadmin;
GRANT SELECT ON applications TO pkgdbreadonly;
GRANT SELECT, UPDATE ON applications_id_seq TO pkgdbreadonly;


CREATE TABLE packagebuildapplications (
    applicationid integer NOT NULL REFERENCES applications
                     ON DELETE CASCADE,
    packagebuildid integer NOT NULL REFERENCES packagebuild ON DELETE CASCADE
    );

GRANT SELECT, UPDATE, INSERT, DELETE ON TABLE packagebuildapplications TO pkgdbadmin;
GRANT SELECT ON packagebuildapplications TO pkgdbreadonly;

-- packagebuild updates
GRANT ALL ON TABLE packagebuild TO pkgdbadmin;
DELETE FROM packagebuild;
ALTER TABLE packagebuild DROP COLUMN desktop;
ALTER TABLE packagebuild DROP CONSTRAINT packagebuild_name_fkey;

-- applicationstags
CREATE TABLE applicationstags (
    applicationid integer NOT NULL REFERENCES applications
                     ON DELETE CASCADE,
    tagid int NOT NULL REFERENCES tags ON DELETE CASCADE,
    score int NOT NULL DEFAULT 1
    );
GRANT SELECT, UPDATE, INSERT, DELETE ON TABLE applicationstags TO pkgdbadmin;
GRANT SELECT ON applicationstags TO pkgdbreadonly;

DROP TABLE packagebuildnamestags;

-- comments
DELETE FROM comments;
ALTER TABLE comments DROP COLUMN packagebuildname;
ALTER TABLE comments ADD applicationid integer NOT NULL REFERENCES applications ON DELETE CASCADE ON UPDATE CASCADE;


DROP TABLE packagebuildnames ;

-- updates score every time someone uses a tag/application combination
CREATE OR REPLACE FUNCTION applicationstags_score()
RETURNS trigger AS $applicationstags_score$
    DECLARE
        old_score integer;
    BEGIN
        SELECT score INTO old_score FROM applicationstags WHERE
            tagid = NEW.tagid AND applicationid = NEW.applicationid;
            
        IF NOT FOUND THEN
            RETURN NEW;
        ELSE
            UPDATE applicationstags SET tagid = NEW.tagid,
                                        applicationid = NEW.applicationid,
                                        score = old_score + 1
                                    WHERE tagid = NEW.tagid AND
                                          applicationid =NEW.applicationid;
            RETURN NULL;
        END IF;
    END;
$applicationstags_score$ LANGUAGE plpgsql;

CREATE TRIGGER applicationstags_score BEFORE INSERT ON applicationstags
    FOR EACH ROW EXECUTE PROCEDURE applicationstags_score();

DROP FUNCTION packagebuildnamestags_score();

ALTER TABLE packagebuild DROP CONSTRAINT packagebuild_uniques;
ALTER TABLE packagebuild ADD CONSTRAINT packagebuild_uniques UNIQUE (name, packageid, epoch, architecture, version, release, repoid);
