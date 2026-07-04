// Comparaison de noms d'identite de publication (page entreprise vs profil).
// Le DOM affiche souvent le nom avec des decorations ("Noisyless • 123 abonnés"),
// on compare donc en normalisant et en incluant dans les deux sens.

export function normalizeName(s) {
  return (s || "")
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();
}

export function identityMatches(actual, expected) {
  const a = normalizeName(actual);
  const e = normalizeName(expected);
  if (!a || !e) return false;
  return a.includes(e) || e.includes(a);
}
