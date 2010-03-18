# Package Database VCS Acls
# Text Format
# Collection|Package|Description|Owner|Initial QA|Initial CCList
# Backslashes (\) are escaped as \u005c Pipes (|) are escaped as \u007c
% for collection in sorted(bugzillaAcls.keys()):
  % for package in sorted(bugzillaAcls[collection].keys()):
<% startLine='|'.join((collection,package,bugzillaAcls[collection][package].summary.replace('\\', '\u005c').replace('|', r'\u007c'),bugzillaAcls[collection][package].owner,bugzillaAcls[collection][package].qacontact or ''))
%>
${startLine}|${','.join(bugzillaAcls[collection][package].cclist.people)}\
  % endfor
% endfor

