#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
VERSION_FILE="$ROOT/VERSION"
CHANGELOG="$ROOT/CHANGELOG.md"
CURRENT=$(cat "$VERSION_FILE" | tr -d '[:space:]')
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT"

echo "Version courante : $CURRENT"
echo "  1) patch → $MAJOR.$MINOR.$((PATCH+1))"
echo "  2) minor → $MAJOR.$((MINOR+1)).0"
echo "  3) major → $((MAJOR+1)).0.0"
read -rp "Type de release [1/2/3] : " CHOICE

case "$CHOICE" in
  1) NEW="$MAJOR.$MINOR.$((PATCH+1))" ;;
  2) NEW="$MAJOR.$((MINOR+1)).0" ;;
  3) NEW="$((MAJOR+1)).0.0" ;;
  *) echo "Choix invalide"; exit 1 ;;
esac

TODAY=$(date +%Y-%m-%d)
ENTRY_FILE=$(mktemp /tmp/changelog_entry.XXXXXX.md)
cat > "$ENTRY_FILE" <<EOF
## [$NEW] — $TODAY

### Ajouté

### Modifié

### Corrigé

EOF

echo ""
echo "Ouverture de l'éditeur pour rédiger l'entrée changelog..."
${EDITOR:-nano} "$ENTRY_FILE"

# Préfixer CHANGELOG.md après la première ligne "# Changelog"
{
  head -1 "$CHANGELOG"
  echo ""
  cat "$ENTRY_FILE"
  tail -n +2 "$CHANGELOG"
} > /tmp/cl_new.md
mv /tmp/cl_new.md "$CHANGELOG"
rm "$ENTRY_FILE"

echo "$NEW" > "$VERSION_FILE"

git add "$VERSION_FILE" "$CHANGELOG"
git commit -m "chore: release v$NEW"
git tag "v$NEW"

echo ""
echo "✓ VERSION=$NEW — commit + tag v$NEW créés localement."
echo "  Pour pousser : git push --follow-tags"
