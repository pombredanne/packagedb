<html xmlns:py="http://purl.org/kid/ns#">
<head>
  <title>${title}</title>
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
  <style type="text/css" media="screen">
    @import url("http://rhold.fedoraproject.org/css/layout.css");
    @import url("http://rhold.fedoraproject.org/css/content.css");
    @import url("http://rhold.fedoraproject.org/css/docbook.css");
    @import url("${tg.url("/static/css/pkgdb.css")}");
  </style>
    <style type="text/css">
        #pageLogin
        {
            text-align: right;
        }
    </style>
  <meta name="MSSmartTagsPreventParsing" content="TRUE"/>
  <script src="${tg.tg_js}/MochiKit.js"></script>
  <script type='text/javascript' py:if="not tg.identity.anonymous">
    tgUserDisplayName = "${tg.identity.user.display_name}";
    tgUserUserName = "${tg.identity.user.user_name}";
    tgUserUserId = "${tg.identity.user.user_id}";
  </script>
</head>
<body>
  <!-- Header BEGIN -->
  <div id="fedora-header">
    <div id="fedora-header-logo">
      <a href="/"><img src="http://rhold.fedoraproject.org/images/header-fedora_logo.png" alt="Fedora Project"/></a>
    </div>

    <div id="fedora-header-items">
      <span class="fedora-header-icon">
        
      </span>
    <div py:if="tg.config('identity.on',False) and not 'logging_in' in locals()"
        id="pageLogin">
        <span py:if="tg.identity.anonymous">
            <a href="${tg.url('/login/')}">Login</a>
        </span>
        <span py:if="not tg.identity.anonymous">
            Welcome ${tg.identity.user.display_name}.
            <a href="${tg.url('/logout/')}">Logout</a>
        </span>
    </div>
    </div>

  </div>

  <div id="fedora-nav"></div>
  <!-- Header END -->

  <!-- LeftNavBar BEGIN -->
  <div id="fedora-side-left">
    <div id="fedora-side-nav-label">Site Navigation:</div>
    <ul id="fedora-side-nav">
      <li><strong><a href="http://fedoraproject.org/wiki/">FedoraProject</a></strong></li>
      <li><a href="http://fedoraproject.org/wiki/PackageMaintainers">Packagers Portal</a></li>
      <li><a href="https://admin.fedoraproject.org/accounts/">Account System</a></li>
      <li><a href="http://fedoraproject.org/wiki/DocsProject">Documentation</a></li>
    </ul>
  </div>
  <!-- LeftNavBar END -->

  <!-- contentArea BEGIN -->
  <div id="fedora-middle-three">
    <div class="fedora-corner-tr">&nbsp;</div>
    <div class="fedora-corner-tl">&nbsp;</div>
    <div id="fedora-content">
      <content>Page content goes here</content>
    </div>
    <div class="fedora-corner-br">&nbsp;</div>
    <div class="fedora-corner-bl">&nbsp;</div>
  </div>
  <!-- contentArea END -->

<!-- RightNavBar BEGIN -->
  
  <!-- footer BEGIN -->
  <div id="fedora-footer">
    Copyright &copy; 2003-2006 Red Hat, Inc. All rights reserved.
    <br/>Fedora is a trademark of Red Hat, Inc. 
    <br/>The Fedora Project is not a supported product of Red Hat, Inc.
    <br/>Red Hat, Inc. is not responsible for the content of other sites. 
    <br/><a href="http://rhold.fedoraproject.org/About/legal/">Legal</a> | <a
  href="http://rhold.fedoraproject.org/About/legal/trademarks/">Trademark Guidelines</a>
    <br/>
  </div>
  <!-- footer END -->

</body>
</html>
