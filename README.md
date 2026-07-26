# Nexus Ciel

Nexus Ciel est un systeme d'orchestration et d'apprentissage **interne d'abord**: il recoit des missions, choisit une strategie economique, execute sous controle, valide les resultats et transforme l'experience en savoir-faire reutilisable.

## Statut actuel

**Phase 1 close et durcie. Phase 2 ouverte, persistance d'abord.** Le Router respecte la cascade officielle, charge sa politique versionnee en lecture seule, contient les pannes de fournisseurs, trace chaque escalade et ne facture que ce qui est reellement depense. Le journal de mission detecte toute alteration de contenu. La Phase 0 reste incomplete sur la persistance: tout l'etat vit en memoire de processus, et `resumable_after_crash` est maintenant calcule a `False` tant qu'aucun backend durable n'existe.

Voir [REPRISE.md](REPRISE.md) pour l'etat detaille, la checklist cochable, les ecarts fermes, la dette ouverte et la roadmap.

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

**48 tests** d'acceptation. La CI GitHub execute les memes sur Python 3.12, puis rejoue la demo en succes et en echec.

## Essayer en 10 secondes

```bash
python -m nexus.demo "resume le sprint"                        # le petit modele suffit, cout 0
python -m nexus.demo "probleme dur" --local-confidence 0.2    # escalade payante tracee
python -m nexus.demo "panne locale" --local-unavailable       # bascule sur le niveau suivant
python -m nexus.demo "impossible" \
  --local-confidence 0.1 --secondary-confidence 0.2           # aucun niveau ne suffit: FAIL propre
```

La sortie donne le verdict, le cout reel, le cout evite par le cache, la trace d'escalade, la validite de la chaine du journal et les evenements publies. Le dernier scenario sort en code 1 et laisse la mission en `abandoned`, sans boucle.

## API

```bash
uvicorn nexus.api.app:app --reload
```

`POST /mission` accepte une mission et la fait passer **par la cascade**, pas par un bouchon. `GET /mission/{id}` rend l'etat, `GET /mission/{id}/report` le rapport complet avec la trace d'escalade et le cout, `GET /policy` la politique de routage en vigueur en lecture seule, `GET /health` l'etat du service, l'integrite du journal, le backend courant (`memory`) et si la reprise apres crash est reellement possible.

## Politique de routage

La cascade et le seuil de confiance vivent dans [`policies/routing_policy_v1.json`](policies/routing_policy_v1.json). C'est de la **donnee versionnee**, propriete logique de l'Evolution Engine. Le Router la lit via `nexus.router.load_policy`, refuse toute politique qui ne serait pas `read_only`, et des tests verifient que le fichier reste identique octet pour octet apres un routage.

Pour pointer une autre politique: `NEXUS_ROUTING_POLICY=/chemin/policy.json`.

## Journal de mission

Chaque entree est signee sur son contenu complet et chainee a la precedente. `verify_chain()` recalcule les signatures: modifier un payload, un acteur ou un type en place invalide la chaine, et `tampered_entries()` nomme les entrees concernees.
