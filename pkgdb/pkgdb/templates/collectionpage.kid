<?python
layout_params['displayNotes']=True
TODO='Not yet implemented'
?>
<html xmlns="http://www.w3.org/1999/xhtml"
  xmlns:py="http://purl.org/kid/ns#"
  py:layout="'layout.kid'">

<div py:match="item.tag == 'content'">
  <h1 py:content="collection.name, ' ',  collection.version">Collection</h1>
  <table border='0'>
  <tr><td>
  Status
  </td><td py:content="collection.statusname">
  </td></tr>
  <tr><td>
  Owner
  </td><td py:content="collection.ownername">
  </td></tr>
  <tr><td>
  Creation Date
  </td><td py:content="TODO">Fill in the Creation Date
  </td></tr>
  </table>
  <p py:content="collection.summary">Summary</p>
  <p py:content="collection.description">Description</p>

  <a py:if="tg.paginate.current_page &gt; 1"
    href="${tg.paginate.get_href(1)}">&lt;&lt;</a>
  <a py:if="tg.paginate.current_page &gt; 1"
    href="${tg.paginate.get_href(tg.paginate.current_page - 1)}">&lt;</a>
  <span py:for="page in tg.paginate.pages">
    <a py:if="page != tg.paginate.current_page" href="${tg.paginate.get_href(page)}">${page}</a>
    <b py:if="page==tg.paginate.current_page">${page}</b>
  </span>
  <a py:if="tg.paginate.current_page &lt; tg.paginate.page_count"
    href="${tg.paginate.get_href(tg.paginate.current_page + 1)}">&gt;</a>
  <a py:if="tg.paginate.current_page &lt; tg.paginate.page_count"
    href="${tg.paginate.get_href(tg.paginate.page_count)}">&gt;&gt;</a>
  <ul py:for="pkg in packages">
  <li><a href="${tg.url('/packages/id/' + str(pkg.id))}"
    py:content="pkg.name"></a> --
    <span py:replace="pkg.summary">Package Summary</span></li>
  </ul>
  <p>Each collection page should have information about the Collection.
  <ul>
  <li>Date it was created</li>
  </ul>
  And it should have links to packages.  For the first cut we'll just have an
  alphabetical listing with [a-z] links at the top (and view all packages).
  In the future, we'll want
  to have most recent packages listed on this page.  And a full range of search
  functions.  Thinking about it this way, the Collections view is really a
  Package view limited by Collection.
  </p>
</div>
</html>
