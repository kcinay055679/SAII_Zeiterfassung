// Picking a name from the list selects that person right away. Typing a name
// and pressing Enter works without this script.
const input = document.getElementById("name");
const known = () => Array.from(input.list.options, (o) => o.value);

input.addEventListener("input", (event) => {
  const picked = !event.inputType || event.inputType === "insertReplacementText";
  if (picked && known().includes(input.value)) {
    input.form.requestSubmit();
  }
});
