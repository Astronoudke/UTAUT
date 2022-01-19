function openPage(pageName,elmnt) {
  var i, tabcontent, tablinks;
  tabcontent = document.getElementsByClassName("tabcontent");
  for (i = 0; i < tabcontent.length; i++) {
    tabcontent[i].style.display = "none";
  }
  tablinks = document.getElementsByClassName("tablink");
  for (i = 0; i < tablinks.length; i++) {
    tablinks[i].style.backgroundColor = "";
  }
  document.getElementById(pageName).style.display = "block";
  elmnt.style.backgroundColor = rgb(200,200,200);
}

var els = document.getElementsByClassName('LoadingValue');
for (var i = 0; i < els.length; i++) {
  var cell = els[i];
  if (cell.textContent < 0.7) {
    cell.classList.add('red');
  } else {
    cell.classList.add('green');
  }
}