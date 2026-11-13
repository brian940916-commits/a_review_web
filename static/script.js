// 表單送出前詢問使用者；實際權限仍由 Python 檢查。
const forms = document.querySelectorAll("form[data-confirm]");
for (const form of forms) {
  form.addEventListener("submit", function (event) {
    if (!confirm(form.dataset.confirm)) {
      event.preventDefault();
    }
  });
}
