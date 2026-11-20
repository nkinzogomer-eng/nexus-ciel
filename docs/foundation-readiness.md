# CIEL Foundation-Ready Decision

## Verdict

**Foundation-Ready partiel, pas Cognitive-Engine-Ready.**

La base PR #10 est suffisamment structurée pour continuer le durcissement de
la persistance, des contrats et de la sécurité. Elle n’est pas prête à annoncer
une autonomie cognitive ou à exécuter des outils externes.

## Prêt maintenant

- contrat de mission Pydantic ;
- runtime mono-étape honnête ;
- routeur avec cascade et coûts ;
- garde budgétaire monétaire ;
- oracle déterministe limité ;
- journal chaîné ;
- persistance snapshot PostgreSQL ;
- abandon explicite après crash ;
- CI PostgreSQL/Compose sur la PR #10.

## Non prêt

- planner et plan multiétapes ;
- action executor et Tool Registry effectif ;
- observation des effets externes ;
- stratégie corrective ;
- reprise idempotente ;
- Memory Core persistant et intégré ;
- SkillCards promues par preuves runtime ;
- approbation humaine et sécurité d’outils ;
- expérience de valeur mesurée sans biais du LLM.

## Gate avant première capacité outil

Aucune exécution d’outil ne doit être ajoutée avant :

1. contrats Plan/Step/Action/Observation/Effect ;
2. policy d’autorité et permission explicite ;
3. sandbox et dry-run ;
4. préconditions/postconditions ;
5. idempotency keys ;
6. journal append-only ;
7. test d’arrêt forcé avant/après action ;
8. approbation humaine pour les effets non réversibles.
