'''Populate database with repos

This script is used to create a postgresql INSERT statement that will populate
the database with all the known fedora, epel and olpc repos.

Right now it is missing: SRPMS, OLPC releases and Fedora 1 and 2 releases.
'''

groups = [
    [['F', 'Fedora'],
     [['devel', 8], ],
     ['i386', 'x86_64'],
     [['', '', 'development/rawhide/%(arch)s/os/'],
      ['-d', ' - Debug', 'development/rawhide/%(arch)s/debug/'],
      ],
     'http://download.fedoraproject.org/pub/fedora/linux/'
     ],
    [['F', 'Fedora'],
      [[13, 23], ],
      ['i386', 'x86_64'],
     [['', '', 'development/%(ver)s/%(arch)s/os/'],
      ['-d', ' - Debug', 'development/%(ver)s/%(arch)s/debug/'],
      ['-tu', ' - Test Updates', 'updates/testing/%(ver)s/%(arch)s/'],
      ['-tud', ' - Test Updates Debug', 'updates/testing/%(ver)s/%(arch)s/debug/'],
      ],
     'http://download.fedoraproject.org/pub/fedora/linux/'
     ],
      
    ]
# this works for newer postgresqls, but not the one on publictest3 (8.1.11)
#
# s = 'INSERT INTO REPOS (shortname, name, collectionid, url, mirror) VALUES \n'
# for group in groups:
#     [[sname, lname], vers, arches, urlschemes, mirror] = group
#     for ver in vers:
#         for arch in arches:
#             for url in urlschemes:
#                 s += "('%(sname)s-%(ver)s-%(arch)s%(sdesc)s',"\
#                      "'%(lname)s %(ver)s - %(arch)s%(ldesc)s', "\
#                      "%(coll)s, \n"\
#                      "'%(urlpart)s', "\
#                      "'%(mirror)s'),\n\n" % {
#                         'lname':lname, 'sname':sname,
#                         'ver':ver[0], 'coll': ver[1],
#                         'arch':arch, 'sdesc':url[0], 'ldesc':url[1],
#                         'urlpart': url[2] % {
#                             'ver':ver[0], 'arch':arch}, 'mirror':mirror}
# # replace the two newlines and comma
# s = s[:-3] + ';'
# print s

# this is suboptimal. It generates a separate insert statement for every row.
# Please use the above version where possible.
s = ''
for group in groups:
    [[sname, lname], vers, arches, urlschemes, mirror] = group
    for ver in vers:
        for arch in arches:
            for url in urlschemes:
                if ver[1] == 8:
                    # Devel is an update
                    s += "UPDATE REPOS set url = "\
                         "'%(urlpart)s' "\
                         " where shortname = "\
                         "'%(sname)s-%(ver)s-%(arch)s%(sdesc)s';\n\n" % {
                            'lname':lname, 'sname':sname,
                            'ver':ver[0], 'coll': ver[1],
                            'arch':arch, 'sdesc':url[0], 'ldesc':url[1],
                            'urlpart': url[2] % {
                                'ver':ver[0], 'arch':arch}, 'mirror':mirror}
                else:
                    # F-13 is an insert
                    s += "INSERT INTO REPOS (shortname, name, collectionid,"\
                         "url, mirror) VALUES \n"\
                         "('%(sname)s-%(ver)s-%(arch)s%(sdesc)s',"\
                         "'%(lname)s %(ver)s - %(arch)s%(ldesc)s', "\
                         "%(coll)s, \n"\
                         "'%(urlpart)s', "\
                         "'%(mirror)s');\n\n" % {
                            'lname':lname, 'sname':sname,
                            'ver':ver[0], 'coll': ver[1],
                            'arch':arch, 'sdesc':url[0], 'ldesc':url[1],
                            'urlpart': url[2] % {
                                'ver':ver[0], 'arch':arch}, 'mirror':mirror}
print s
