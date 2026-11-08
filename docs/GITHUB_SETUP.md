# Publication sur GitHub

## Option A — interface web + terminal

1. Dans GitHub, cliquer sur **New repository** : https://github.com/new
2. Choisir le nom `wake-sleep-memory-lab`, la visibilité souhaitée et **ne pas** cocher « Add README », `.gitignore` ou licence (déjà inclus).
3. Décompresser l'archive dans un dossier local, puis ouvrir un terminal dans ce dossier.
4. Exécuter les commandes suivantes en remplaçant `OWNER` par ton identifiant GitHub :

```bash
git init -b main
git add .
git commit -m "feat: initial wake/sleep memory lab"
git remote add origin https://github.com/OWNER/wake-sleep-memory-lab.git
git push -u origin main
```

Authentifie-toi auprès de GitHub en utilisant un gestionnaire d'identifiants, SSH ou un jeton d'accès personnel. **Ne mets jamais de jeton dans le dépôt, les commandes enregistrées ou les fichiers du projet.**

## Option B — GitHub CLI

Dans le dossier décompressé :

```bash
git init -b main
git add .
git commit -m "feat: initial wake/sleep memory lab"
gh auth login
gh repo create wake-sleep-memory-lab --private --source=. --remote=origin --push
```

`--private` est la valeur prudente au départ. Pour une publication open source, vérifier soigneusement tout le contenu, puis choisir `--public` (ou modifier la visibilité après revue).

## Références officielles

- https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository
- https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github
- https://docs.github.com/en/get-started/git-basics/managing-remote-repositories
