# Compte-rendu Backend — Projet Factures

---

## 1. Contexte et objectifs

**Problème** : Société de conseil en produits structurés. Avant de payer des commissions aux apporteurs d'affaires, on leur envoie une pré-confirmation. Actuellement fait à la main sous Word — lent et source d'erreurs.

**Solution construite** : API REST FastAPI qui calcule les commissions, génère le PDF, et stocke le tout de manière tracable et confidentielle.

---

## 2. Architecture technique

```
┌─────────────┐      ┌──────────────────────┐      ┌─────────────────┐
│  Next.js     │      │   FastAPI             │      │   Supabase       │
│  (frontend)   │──────▶│   (backend)           │──────▶│   Postgres +     │
│  Vercel       │  API │   Render              │      │   Storage        │
│               │calls │                       │      │                   │
└─────────────┘      └──────────────────────┘      └─────────────────┘
```

- **Déploiement** : Render (gratuit, Python 3.11)
- **URL** : `https://factures-backend-qb5x.onrender.com`
- **Base de données** : Supabase (Postgres)
- **Stockage fichiers** : Supabase Storage (bucket `preconfirmations`)

---

## 3. Structure des fichiers

```
D:\Test\backend\
├── app/
│   ├── __init__.py
│   ├── main.py                  ← Point d'entrée FastAPI (lifespan, CORS, routers)
│   ├── config.py                ← Variables d'environnement (.env)
│   ├── database.py              ← Client Supabase + health check
│   ├── schemas/
│   │   ├── commission.py        ← Schémas Pydantic moteur (DealInput, ProductInput...)
│   │   ├── api_response.py      ← Schémas publics (sans données confidentielles)
│   │   └── audit.py             ← Schémas audit (AuditDocumentSummary, AuditComparison)
│   ├── services/
│   │   ├── commission_engine.py ← Moteur de calcul pur (3 types de commission + fractions exactes)
│   │   ├── commission_service.py ← Orchestration calcul + snapshot
│   │   ├── pdf_generator.py     ← Génération PDF avec fpdf2
│   │   ├── storage_service.py   ← Stockage Supabase + versionnage + audit
│   │   └── pdf_extractor.py     ← Extraction term sheet (PyMuPDF + regex)
│   └── routers/
│       ├── commission.py        ← POST /commission/calculate
│       ├── preconfirmation.py   ← POST /generate, GET /{id}, GET /preconfirmations/
│       └── extract.py           ← POST /extract
├── tests/
│   └── test_commission.py       ← 10 tests unitaires (tous passés)
├── fonts/
│   └── NotoSans-Regular.ttf     ← Police Unicode (accents + €)
├── requirements.txt             ← Dépendances
├── runtime.txt                  ← python-3.11.16 (pour Render)
├── .env                         ← Secrets Supabase
├── .gitignore
└── render.yaml                  ← Config déploiement Render
```

---

## 4. Les endpoints

| Méthode | Endpoint | Fonction | Status |
|---------|----------|----------|--------|
| GET | `/health` | Vérifie connexion Supabase | OK |
| POST | `/commission/calculate` | Calcule commissions (sans stockage) | OK |
| POST | `/preconfirmation/generate` | Calcule + génère PDF + stocke + versionne | OK |
| GET | `/preconfirmation/{id}` | Résumé d'un document (pas de données confidentielles) | OK |
| GET | `/preconfirmation/{id}/detail` | Détail complet (avec snapshot confidentiel) | OK |
| GET | `/preconfirmations/` | Listing historique/filtre par référence | OK |
| GET | `/preconfirmations/compare` | Compare deux versions | OK |
| POST | `/extract` | Extrait données term sheet PDF | OK |

---

## 5. Le moteur de commission

**3 types supportés** (extensibles) :

| Type | Formule | Exemple |
|------|---------|---------|
| `bps_notional` | notional × bps × 0.0001 | 50 bps × 1M = 5 000€ |
| `fee_share` | total_frais × fraction (exacte ou décimale) | 1/3 × 15 000€ = 5 000€ |
| `flat` | montant fixe | 5 000€ |

**Caractéristiques** :
- `Decimal` partout (jamais de float — précision comptable)
- Arrondi bancaire ROUND_HALF_EVEN à 2 décimales
- Fonctions pures sans effets de bord
- Chaque résultat contient `calculation_detail` (formule appliquée) pour la traçabilité
- Support de fractions exactes (1/3) via `fraction_numerateur` / `fraction_denominateur`

**Les 5 cas du brief** — tous validés :

| Cas | Type | Montant | Résultat |
|-----|------|---------|----------|
| A | 50 bps × 1M EUR | 5 000 EUR | OK |
| B | 1/3 × 15 000 EUR | 5 000 EUR | OK (corrigé avec fraction exacte) |
| C | flat 5 000 USD | 5 000 USD | OK |
| D | 40% × 6 375 EUR | 2 550 EUR | OK |
| E | 120 bps × 500K EUR | 6 000 EUR | OK |

---

## 6. La confidentialité

Le brief est explicite : la contrepartie ne doit **jamais** voir le total des frais ni ce que l'entreprise garde.

**Ce qui est protégé** :
- `total_fees` (frais totaux par produit) — absent de l'API publique
- `calculation_detail` (contient les frais intermédiaires) — absent de l'API publique
- `total_fees_global` (frais globaux du deal) — absent de l'API publique

**Ce qui est public** :
- `total_commissions` (montant dû aux apporteurs)
- `product_name`, `notional`, `currency`, `upfront_fee_rate`
- Métadonnées (id, version, date, statut)

**Architecture de confidentialité** :
```
Moteur interne → snapshot complet (audit DB)
                ↘DealPublic (API) → pas de total_fees, pas de calculation_detail
```

**Protection renforcée** :
- Messages d'erreur génériques côté client (pas de fuite via les erreurs)
- Logs détaillés côté serveur uniquement
- Champs `generated_by` dans les documents pour la traçabilité

---

## 7. Le stockage et le versionnage

**Principes** :
- Jamais d'écrasement — chaque génération crée une nouvelle ligne
- Chemin unique : `deals/{ref}/{timestamp}_v{version}.pdf`
- Supabase Storage pour le PDF, Postgres pour les métadonnées
- Snapshot JSONB contenant TOUT (y compris données confidentielles pour l'audit interne)

**Tables Supabase** :
```sql
deals                  ← un dossier
products               ← notionnel, frais, lié à un deal
introducers            ← apporteurs d'affaires
commission_terms       ← type + valeur + montant calculé
preconfirmation_documents ← versionné, snapshot JSONB, jamais écrasé
```

---

## 8. La génération PDF

**Outil** : fpdf2 (pur Python — pas de dépendances système)

Pourquoi pas WeasyPrint : nécessite GTK3, Pango, GObject — lourd et instable sur Windows et sur Render.

**Contenu du PDF** :
- Logo de la contrepartie (optionnel, uploadé)
- Référence et date d'émission
- Nom et adresse de la contrepartie (optionnels)
- Tableau multi-produits (notionnel, type, montant dû)
- Total des commissions
- Bloc émetteur fixe
- Notice de confidentialité
- **JAMAIS les frais totaux**

---

## 9. L'extraction term sheet

**Endpoint** : `POST /extract`

**Outil** : PyMuPDF (lecture PDF) + regex (extraction intelligente)

**Ce qui est extrait** :
- `product_name` (nom du produit)
- `isin` (code ISIN)
- `issuer` (émetteur)
- `currency` (devise)
- `upfront_fee_rate` (taux de frais)

**Ce qui n'est JAMAIS extrait** (conforme au brief) :
- `notional` → toujours `null`
- `commission_terms` → toujours `[]`

**Score de confiance** : pourcentage de champs détectés + warnings si champs manquants

---

## 10. L'audit et l'historique

**Listing** (`GET /preconfirmations/`) :
- Résumé par document (sans données confidentielles)
- Filtre par `deal_reference` via JSONB `contains`
- Compteurs produits et introducers

**Comparaison** (`GET /preconfirmations/compare`) :
- Différences entre deux versions
- Changement de total commissions, nombre de produits, frais globaux

**Détail confidentiel** (`GET /preconfirmation/{id}/detail`) :
- Snapshot complet avec toutes les données internes
- Pour l'audit interne uniquement

---

## 11. Décisions techniques

| # | Décision | Raison |
|---|----------|--------|
| D1 | `Decimal` partout | Pas d'erreur de précision binaire sur des montants qui déclenchent un paiement |
| D2 | Arrondi ROUND_HALF_EVEN, 2 décimales | Norme comptable (IEEE 754), pas de biais systématique |
| D3 | Pas de conversion de devises | Le moteur retourne dans la devise du terme — la conversion est un problème de l'appelant |
| D4 | `fee_share` = fraction exacte ou décimale | Évite les erreurs d'arrondi sur les fractions simples (1/3, 1/4...) |
| D5 | Schéma API séparé du schéma moteur | Confidentialité — `total_fees` jamais exposé |
| D6 | Snapshot JSONB dans la DB | Audit interne complet (contient tout, même les données confidentielles) |
| D7 | Versionnage des documents | Jamais d'écrasement — conformité traçabilité |
| D8 | fpdf2 au lieu de WeasyPrint | Pas de dépendances système (GTK), déploiement facile |
| D9 | Police NotoSans | Support complet Unicode + symbole € |
| D10 | Filtrage JSONB `contains` | Flexible, pas de migration de schéma |
| D11 | Messages d'erreur génériques | Confidentialité — aucune donnée sensible dans les réponses d'erreur |
| D12 | Dispatcher CALCULATORS | Extensible — ajout d'un type = 1 fonction + 1 entrée dans le dict |

---

## 12. Problèmes rencontrés et solutions

| Problème | Cause | Solution |
|----------|-------|----------|
| Erreur 401 Supabase au démarrage | Mauvaise config `ClientOptions` dans database.py | Suppression des headers personnalisés qui interféraient avec l'auth automatique |
| WeasyPrint ne fonctionne pas sur Windows | Nécessite GTK3/Pango/GObject | Remplacement par fpdf2 (pur Python) |
| Déploiement Render échoue | Python 3.14 sans wheel pydantic-core → compilation Rust impossible | Ajout de `runtime.txt` avec `python-3.11.16` |
| Erreur `bytearray` vs `bytes` sur l'upload | fpdf2 retourne un bytearray | Conversion `bytes(pdf_bytes)` avant l'upload |
| Cas B fee_share faux (4999.50 vs 5000.00) | Fraction 0.3333 tronquée | Ajout de fractions exactes (1/3) via fraction_numerateur/denominateur |
| Fuite de données via messages d'erreur | Messages d'erreur bruts renvoyés au client | Messages génériques côté client, logs détaillés côté serveur |

---

## 13. Tests

**Tests unitaires** (`tests/test_commission.py`) : 10 tests passés
- Cas A, B (exact + décimal), C, D, E
- Multi-produits (deal complet avec les 5)
- Multi-introducers sur un même produit
- Traçabilité (vérification `calculation_detail`)
- Confidentialité (vérification absence de champs sensibles dans schémas publics)

**Tests manuels** (via curl/API) :
- Extraction term sheet avec PDF de test
- Calcul de commission via API
- Génération PDF + stockage Supabase
- Listing audit sans fuite de données confidentielles
- Comparaison de versions

---

## 14. Exclusions volontaires (hors scope)

**Conformément au brief** :

| Exclusion | Justification |
|-----------|---------------|
| Facturation inverse | Hors scope (frais que l'entreprise reçoit) |
| Comptabilité / cash-flow | Hors scope du brief |
| Validation en ligne par la contrepartie | En attente de feu vert réglementaire |

**Limitations connues (MVP)** :

| Limitation | Raison | V2 |
|------------|--------|----|
| Pas d'authentification utilisateur | MVP — accès partagé | À implémenter (auth JWT) |
| Pas de "generated_by" automatique | Pas d'auth | user_id du connecté |

---

## 15. Ce qui reste à faire

Le backend est **complet et déployé**. La suite prévue :
1. **Frontend Next.js** (déjà commencé — 5 pages fonctionnelles en local)
2. **Déploiement frontend** sur Vercel
3. **Intégration auth** pour la traçabilité utilisateur
