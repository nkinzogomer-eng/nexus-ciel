# Nexus Ciel

Nexus Ciel est un systeme d'orchestration et d'apprentissage **interne d'abord**: il recoit des missions, choisit une strategie economique, execute sous controle, valide les resultats et transforme l'experience en savoir-faire reutilisable.

## Statut actuel

**Phase 1 close sur CI verte (`7d86b58`). Phase 2 ouverte.** Le Router respecte la cascade officielle, charge sa politique versionnee en lecture seule et trace chaque escalade. La Phase 0 reste incomplete sur la persistance: tout l'etat vit en memoire de processus.

Voir [REPRISE.md](REPRISE.md) pour l'etat detaille, la checklist cochable, la dette ouverte et la roadmap.

## Principes non negociables

- Manas/Core reste gele et modifiable par l'humain uniquement.
- Les sources canoniques restent uniques: State Graph, Mission Journal, Capability Registry.
- Les capacites et politiques evolutives sont versionnees, probatoires et reversibles.
- La validation deterministe precede le jugement LLM.
- Les budgets, retries, sandbox et kill-switch sont obligatoires avant autonomie accrue.
- L'apprentissage se fait en tache de fond, jamais au milieu d'une mission.

## Developpement local

```bash
pip install -e '.[test]'
pytest -q
```

La CI GitHub execute les memes tests sur Python 3.12.

## Essayer en 10 secondes

```bash
python -m nexus.demo "resume le sprint"          # le petit modele suffit, cout 0
python -m nexus.demo "probleme dur" --local-confidence 0.2   # escalade payante tracee
python -m nexus.demo "panne locale" --local-unavailable       # bascule sur le niveau suivant
```

La sortie donne le verdict, le cout reel, la trace d'escalade, la validite de la chaine du journal et les evenements publies.

## Politique de routage

La cascade et le seuil de confiance vivent dans [`policies/routing_policy_v1.json`](policies/routing_policy_v1.json). C'est de la **donnee versionnee**, propriete logique de l'Evolution Engine. Le Router la lit via `nexus.router.load_policy`, refuse toute politique qui ne serait pas `read_only`, et des tests verifient que le fichier reste identique octet pour octet apres un routage.

Pour pointer une autre politique: `NEXUS_ROUTING_POLICY=/chemin/policy.json`.
