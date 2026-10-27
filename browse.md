Browse the lessons 
-----------------------------
The lessons that have been submitted to the PLUMED-TUTORIALS are listed below.  PLUMED-TUTORIALS monitors whether PLUMED input files in these lessons are compatible with the current and development
versions of the code and integrates links from these files to the PLUMED manual.  Inputs in the tutorials listed below were last tested on {{ site.data.date.date }}.

Suggestions for an order to work through the tutorials can be found [here](summarygraph.md).
A complete bibliography of papers connected to these lessons can be found [here](bibliography.md).

{% raw %}
<div id="diplay_description"> </div>
{% endraw %}

{:#browse-table .display}
| ID | Name | Instructors | Description | Tags | Actions | Modules |
|:--------:|:--------:|:---------:|:---------:|:---------:|:---------:|:---------:|
{% for item in site.data.lessons %}| {{ item.id }} | [{% if item.title_ja %}<span class="lang-en">{{ item.title }}</span><span class="lang-ja">{{ item.title_ja }}</span>{% else %}{{ item.title }}{% endif %}]({{ item.path }}) | {{ item.instructors }} | {% if item.description_ja %}<span class="lang-en">{{ item.description }}</span><span class="lang-ja">{{ item.description_ja }}</span>{% else %}{{ item.description }}{% endif %} | {{ item.tags }} | {{ item.actions }} | {{ item.modules }} |
{% endfor %}


<script>
// Translations of the strings in this script (from locale/ja/site.po)
var I18N = {{ site.data.i18n | jsonify }};
function t(s) { return (getSiteLang() === "ja" && I18N && I18N[s]) || s; }
// The DataTables interface strings can only be set when the table is created, so reload when the language is changed
document.addEventListener("sitelangchange", function() { window.location.reload(); });
$(document).ready(function() {
var table = $('#browse-table').DataTable({
  "dom": '<"search"f><"top"il>rt<"bottom"Bp><"clear">',
  language: {
    search: '',
    searchPlaceholder: t("Search project..."),
    lengthMenu: t("Show _MENU_ entries"),
    info: t("Showing _START_ to _END_ of _TOTAL_ entries"),
    infoEmpty: t("Showing 0 to 0 of 0 entries"),
    infoFiltered: t("(filtered from _MAX_ total entries)"),
    zeroRecords: t("No matching records found"),
    emptyTable: t("No data available in table"),
    paginate: { first: t("First"), previous: t("Previous"), next: t("Next"), last: t("Last") },
    buttons: { copy: t("Copy") }
  },
  buttons: [
        'copy', 'excel', 'pdf'
  ],
  "columnDefs": [ 
     { "targets": 4, "visible": false },
     { "targets": 5, "visible": false },
     { "targets": 6, "visible": false }
  ],
  "order": [[ 0, "desc" ]]
  });
$('#browse-table-searchbar').keyup(function () {
  table.search( this.value ).draw();
  });
  hu = window.location.search.substring(1);
  searchfor = hu.split("=");
  if( searchfor[0]=="search" ) {
      table.search( searchfor[1].replace("%20"," ") ).draw();
      document.getElementById("diplay_description").innerHTML = "";
  } else if( searchfor[0]=="action" ) {
      fetch("./syntax.0.json")
        .then(response => {
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        return response.json();
        })
        .then( data => document.getElementById("diplay_description").innerHTML = "<b>" + t("Showing lessons that use:") + "</br></br>" + searchfor[1] + " (" + t("action") + "): " + data[ searchfor[1] ]["description"] + " <a href=\"" + data[ searchfor[1] ]["hyperlink"] + "\">" + t("More details") + "</a></b>")
      table.columns(5).search( "\\b" + searchfor[1] + "\\b", true, false, false ).draw();
  } else if( searchfor[0]=="module" ) {
      fetch("./syntax.0.json")
        .then(response => {
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        return response.json();
        })
        .then( data => document.getElementById("diplay_description").innerHTML = "<b>" + t("Showing lessons that use:") + "</br></br>" + searchfor[1] + " (" + t("module") + "): " + data["modules"][ searchfor[1] ]["description"] + " <a href=\"" + data["modules"][ searchfor[1] ]["hyperlink"] + "\">" + t("More details") + "</a></b>")
      table.columns(6).search( "\\b" + searchfor[1] + "\\b", true, false, false ).draw();
  }
});
</script>
