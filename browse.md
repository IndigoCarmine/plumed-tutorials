<div class="lang-en" markdown="1">

Browse the lessons 
-----------------------------
The lessons that have been submitted to the PLUMED-TUTORIALS are listed below.  PLUMED-TUTORIALS monitors whether PLUMED input files in these lessons are compatible with the current and development
versions of the code and integrates links from these files to the PLUMED manual.  Inputs in the tutorials listed below were last tested on {{ site.data.date.date }}.

Suggestions for an order to work through the tutorials can be found [here](summarygraph.md).
A complete bibliography of papers connected to these lessons can be found [here](bibliography.md).

</div>
<div class="lang-ja" markdown="1">

レッスン一覧
-----------------------------
PLUMED-TUTORIALS に投稿されたレッスンを以下に示します。PLUMED-TUTORIALS は、これらのレッスン内の PLUMED 入力ファイルがコードの現行版および開発版と
互換性があるかを監視し、それらのファイルから PLUMED マニュアルへのリンクを統合しています。以下のチュートリアルの入力ファイルは {{ site.data.date.date }} に最終テストされました。

チュートリアルに取り組む順序の提案は[こちら](summarygraph.md)にあります。
これらのレッスンに関連する論文の完全な文献リストは[こちら](bibliography.md)にあります。

</div>

{% raw %}
<div id="diplay_description"> </div>
{% endraw %}

{:#browse-table .display}
| ID | <span class="lang-en">Name</span><span class="lang-ja">タイトル</span> | <span class="lang-en">Instructors</span><span class="lang-ja">講師</span> | <span class="lang-en">Description</span><span class="lang-ja">説明</span> | Tags | Actions | Modules |
|:--------:|:--------:|:---------:|:---------:|:---------:|:---------:|:---------:|
{% for item in site.data.lessons %}| {{ item.id }} | [{{ item.title }}]({{ item.path }}) | {{ item.instructors }} | {{ item.description }} | {{ item.tags }} | {{ item.actions }} | {{ item.modules }} |
{% endfor %}


<script>
// The DataTables interface strings can only be set when the table is created, so reload when the language is changed
document.addEventListener("sitelangchange", function() { window.location.reload(); });
var isJapanese = getSiteLang() === "ja";
$(document).ready(function() {
var language = { search: '', searchPlaceholder: "Search project..." };
if( isJapanese ) {
  language = {
    search: '',
    searchPlaceholder: "レッスンを検索...",
    lengthMenu: "_MENU_ 件表示",
    info: "_TOTAL_ 件中 _START_ から _END_ まで表示",
    infoEmpty: "0 件中 0 から 0 まで表示",
    infoFiltered: "（全 _MAX_ 件より抽出）",
    zeroRecords: "一致するレッスンが見つかりません",
    emptyTable: "レッスンがありません",
    paginate: { first: "先頭", previous: "前", next: "次", last: "最終" },
    buttons: { copy: "コピー" }
  };
}
var table = $('#browse-table').DataTable({
  "dom": '<"search"f><"top"il>rt<"bottom"Bp><"clear">',
  language: language,
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
        .then( data => document.getElementById("diplay_description").innerHTML = (isJapanese ? "<b>次を使用しているレッスンを表示しています：</br></br>" : "<b>Showing lessons that use:</br></br>") + searchfor[1] + (isJapanese ? " （アクション）: " : " (action): ") + data[ searchfor[1] ]["description"] + " <a href=\"" + data[ searchfor[1] ]["hyperlink"] + "\">" + (isJapanese ? "詳細" : "More details") + "</a></b>")
      table.columns(5).search( "\\b" + searchfor[1] + "\\b", true, false, false ).draw();
  } else if( searchfor[0]=="module" ) {
      fetch("./syntax.0.json")
        .then(response => {
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        return response.json();
        })
        .then( data => document.getElementById("diplay_description").innerHTML = (isJapanese ? "<b>次を使用しているレッスンを表示しています：</br></br>" : "<b>Showing lessons that use:</br></br>") + searchfor[1] + (isJapanese ? " （モジュール）: " : " (module): ") + data["modules"][ searchfor[1] ]["description"] + " <a href=\"" + data["modules"][ searchfor[1] ]["hyperlink"] + "\">" + (isJapanese ? "詳細" : "More details") + "</a></b>")
      table.columns(6).search( "\\b" + searchfor[1] + "\\b", true, false, false ).draw();
  }
});
</script>
