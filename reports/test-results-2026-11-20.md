# Résultats de tests — Foundation Hardening CIEL

## Références

- Base de travail : `322bfd3b1e8a0697e1d7c866ffbca2696f716c35`.
- Main préservé : `3d8cf71b42ec9b3260768c5c454808bb450a153d`.
- Memory Core préservé : `d2aa828d105ecb5091af3e75db9a8aef5ad3488a`.

## Commandes locales

Créer un environnement propre :

```bash
python3 -m venv /tmp/ciel-hardening-venv
/tmp/ciel-hardening-venv/bin/python -m pip install -e '.[test]'
```

Compiler les sources :

```bash
/tmp/ciel-hardening-venv/bin/python -m compileall -q nexus tests
```

Suite sans service PostgreSQL :

```bash
cd /path/to/nexus-ciel
/tmp/ciel-hardening-venv/bin/python -m pytest -q
```

Le test de restauration PostgreSQL doit être `SKIPPED` avec la raison
`NEXUS_DATABASE_URL is required for the live PostgreSQL persistence test`.
Le test DSN doit continuer à passer.

Résultat local obtenu le 2026-11-20 sans service PostgreSQL : **69 passed,
2 skipped in 0.26s**. Les deux skips sont le test de restauration PostgreSQL
et la gate SIGKILL ; aucun `KeyError` n’est produit.

Suite PostgreSQL :

```bash
export NEXUS_DATABASE_URL=postgresql://nexus:nexus@localhost:5432/nexus_ciel
alembic upgrade head
python -m pytest -q tests/test_phase2_postgres.py tests/test_phase2_sigkill_gate.py
```

## Preuves existantes conservées

Le run CI PR #10 `42051032012` est `success` sur `322bfd3` et indique :

- 71 tests passés en 1,97 s ;
- compilation et installation propre ;
- migrations PostgreSQL ;
- gate SIGKILL de récupération/abandon contrôlé ;
- restauration Compose avec volume ;
- smoke run ;
- scénario non routable en échec propre.

## Limite d’exécution locale de l’audit précédent

L’environnement d’audit ne possédait ni Docker ni PostgreSQL local. Avant la
correction, la suite complète locale échouait par `KeyError` dans le test de
restauration DB ; les tests hors DB passaient. Cette correction rend l’absence
de service explicite et ne remplace pas la preuve d’intégration PostgreSQL.

## Scénarios CIEL actuellement exécutables

- Mission simple synthétique avec oracle de sortie : oui.
- Budget dépassé / provider insuffisant : oui.
- Vérification indépendante limitée : oui.
- Persistance et abandon après SIGKILL : oui sur CI PostgreSQL.
- Mission multiétape avec actions et observations : non, contrat seulement.
- Échec d’outil puis correction : non.
- Reprise sans répétition d’action : non ; abandon contrôlé actuel.
- Fonctionnement déterministe sans LLM : partiel ; le runtime s’abstient sans
  router, mais aucun moteur de mission déterministe multiétape n’existe.
