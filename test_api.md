# Guide de test API — Swagger UI

URL Swagger : `https://factures-backend-qb5x.onrender.com/docs`

---

## 1. POST /commission/calculate

**Description** : Calcule les commissions d'un deal (sans stockage)

**Méthode** : POST  
**URL** : `https://factures-backend-qb5x.onrender.com/commission/calculate`

### Body (JSON) — Cas A (50 bps × 1M EUR = 5 000€)

```json
{
  "deal_reference": "TEST-A",
  "products": [
    {
      "product_name": "Autocall Phoenix",
      "notional": 1000000,
      "upfront_fee_rate": 1.50,
      "currency": "EUR",
      "commission_terms": [
        {
          "introducer_id": "intro-1",
          "commission_type": "bps_notional",
          "commission_value": 50,
          "commission_currency": "EUR"
        }
      ]
    }
  ]
}
```

**Résultat attendu** : `total_commissions: "5000.00"`

---

### Body (JSON) — Cas B (1/3 × 15 000€ = 5 000€ avec fraction exacte)

```json
{
  "deal_reference": "TEST-B",
  "products": [
    {
      "product_name": "Note Reverse",
      "notional": 1000000,
      "upfront_fee_rate": 1.50,
      "currency": "EUR",
      "commission_terms": [
        {
          "introducer_id": "intro-1",
          "commission_type": "fee_share",
          "commission_value": 0,
          "fraction_numerateur": 1,
          "fraction_denominateur": 3,
          "commission_currency": "EUR"
        }
      ]
    }
  ]
}
```

**Résultat attendu** : `total_commissions: "5000.00"`

---

### Body (JSON) — Cas B' (0.3333 × 15 000€ = 4 999,50€ avec fraction décimale)

```json
{
  "deal_reference": "TEST-B-DEC",
  "products": [
    {
      "product_name": "Note Reverse",
      "notional": 1000000,
      "upfront_fee_rate": 1.50,
      "currency": "EUR",
      "commission_terms": [
        {
          "introducer_id": "intro-1",
          "commission_type": "fee_share",
          "commission_value": 0.3333,
          "commission_currency": "EUR"
        }
      ]
    }
  ]
}
```

**Résultat attendu** : `total_commissions: "4999.50"`

---

### Body (JSON) — Cas C (flat 5 000 USD)

```json
{
  "deal_reference": "TEST-C",
  "products": [
    {
      "product_name": "Certificate Twin-Win",
      "notional": 2500000,
      "upfront_fee_rate": 1.20,
      "currency": "USD",
      "commission_terms": [
        {
          "introducer_id": "intro-1",
          "commission_type": "flat",
          "commission_value": 5000,
          "commission_currency": "USD"
        }
      ]
    }
  ]
}
```

**Résultat attendu** : `total_commissions: "5000.00"`

---

### Body (JSON) — Cas D (40% × 6 375€ = 2 550€)

```json
{
  "deal_reference": "TEST-D",
  "products": [
    {
      "product_name": "Barrier Reverse",
      "notional": 750000,
      "upfront_fee_rate": 0.85,
      "currency": "EUR",
      "commission_terms": [
        {
          "introducer_id": "intro-1",
          "commission_type": "fee_share",
          "commission_value": 0.40,
          "commission_currency": "EUR"
        }
      ]
    }
  ]
}
```

**Résultat attendu** : `total_commissions: "2550.00"`

---

### Body (JSON) — Cas E (120 bps × 500K = 6 000€)

```json
{
  "deal_reference": "TEST-E",
  "products": [
    {
      "product_name": "Snowball Note",
      "notional": 500000,
      "upfront_fee_rate": 0.60,
      "currency": "EUR",
      "commission_terms": [
        {
          "introducer_id": "intro-1",
          "commission_type": "bps_notional",
          "commission_value": 120,
          "commission_currency": "EUR"
        }
      ]
    }
  ]
}
```

**Résultat attendu** : `total_commissions: "6000.00"`

---

### Body (JSON) — Multi-produits (les 5 cas A-E)

```json
{
  "deal_reference": "TEST-ALL-5",
  "products": [
    {
      "product_name": "Autocall Phoenix",
      "notional": 1000000,
      "upfront_fee_rate": 1.50,
      "currency": "EUR",
      "commission_terms": [
        {
          "introducer_id": "intro-1",
          "commission_type": "bps_notional",
          "commission_value": 50,
          "commission_currency": "EUR"
        }
      ]
    },
    {
      "product_name": "Note Reverse",
      "notional": 1000000,
      "upfront_fee_rate": 1.50,
      "currency": "EUR",
      "commission_terms": [
        {
          "introducer_id": "intro-1",
          "commission_type": "fee_share",
          "commission_value": 0,
          "fraction_numerateur": 1,
          "fraction_denominateur": 3,
          "commission_currency": "EUR"
        }
      ]
    },
    {
      "product_name": "Certificate Twin-Win",
      "notional": 2500000,
      "upfront_fee_rate": 1.20,
      "currency": "USD",
      "commission_terms": [
        {
          "introducer_id": "intro-1",
          "commission_type": "flat",
          "commission_value": 5000,
          "commission_currency": "USD"
        }
      ]
    },
    {
      "product_name": "Barrier Reverse",
      "notional": 750000,
      "upfront_fee_rate": 0.85,
      "currency": "EUR",
      "commission_terms": [
        {
          "introducer_id": "intro-1",
          "commission_type": "fee_share",
          "commission_value": 0.40,
          "commission_currency": "EUR"
        }
      ]
    },
    {
      "product_name": "Snowball Note",
      "notional": 500000,
      "upfront_fee_rate": 0.60,
      "currency": "EUR",
      "commission_terms": [
        {
          "introducer_id": "intro-1",
          "commission_type": "bps_notional",
          "commission_value": 120,
          "commission_currency": "EUR"
        }
      ]
    }
  ]
}
```

**Résultat attendu** : `total_commissions: "23550.00"`

---

### Body (JSON) — Multi-introducteurs sur un même produit

```json
{
  "deal_reference": "TEST-MULTI-INTRO",
  "products": [
    {
      "product_name": "Deal Multi",
      "notional": 1000000,
      "upfront_fee_rate": 1.50,
      "currency": "EUR",
      "commission_terms": [
        {
          "introducer_id": "intro-1",
          "commission_type": "bps_notional",
          "commission_value": 50,
          "commission_currency": "EUR"
        },
        {
          "introducer_id": "intro-2",
          "commission_type": "fee_share",
          "commission_value": 0.25,
          "commission_currency": "EUR"
        }
      ]
    }
  ]
}
```

**Résultat attendu** : `total_commissions: "8750.00"` (5000 + 3750)

---

## 2. POST /preconfirmation/generate

**Description** : Calcule, génère le PDF, stocke et versionne

**Méthode** : POST  
**URL** : `https://factures-backend-qb5x.onrender.com/preconfirmation/generate`

### Body (multipart/form-data)

| Champ | Type | Valeur |
|-------|------|--------|
| `data` | string (json) | Voir ci-dessous |
| `counterparty_name` | string | "Test Capital Partners" |
| `counterparty_address` | string | "88 King Street\nLondon EC2V 8QE" |

**Valeur de `data`** :

```json
{
  "deal_reference": "PDF-TEST-001",
  "products": [
    {
      "product_name": "Autocall Phoenix",
      "notional": 1000000,
      "upfront_fee_rate": 1.50,
      "currency": "EUR",
      "commission_terms": [
        {
          "introducer_id": "intro-1",
          "commission_type": "bps_notional",
          "commission_value": 50,
          "commission_currency": "EUR"
        }
      ]
    }
  ]
}
```

**Résultat attendu** :
```json
{
  "status": "ok",
  "document_id": "uuid-...",
  "version": 1,
  "pdf_url": "https://...supabase.co/...",
  "deal_reference": "PDF-TEST-001",
  "total_commissions": "5000.00",
  "generated_at": "2026-09-16T..."
}
```

---

## 3. GET /preconfirmation/{id}

**Description** : Récupère les métadonnées d'un document (sans données confidentielles)

**Méthode** : GET  
**URL** : `https://factures-backend-qb5x.onrender.com/preconfirmation/{doc_id}`

### Paramètres

| Paramètre | Type | Valeur |
|-----------|------|--------|
| `doc_id` | string (uuid) | L'ID retourné par POST /generate |

**Exemple** : `https://factures-backend-qb5x.onrender.com/preconfirmation/117b9d96-37d3-4257-87c3-9fe466108ca1`

---

## 4. GET /preconfirmation/{id}/detail

**Description** : Récupère le détail complet (avec snapshot confidentiel)

**Méthode** : GET  
**URL** : `https://factures-backend-qb5x.onrender.com/preconfirmation/{doc_id}/detail`

### Paramètres

| Paramètre | Type | Valeur |
|-----------|------|--------|
| `doc_id` | string (uuid) | L'ID retourné par POST /generate |

---

## 5. GET /preconfirmations/

**Description** : Liste les documents génés (audit/historique)

**Méthode** : GET  
**URL** : `https://factures-backend-qb5x.onrender.com/preconfirmations/`

### Paramètres (query)

| Paramètre | Type | Requis | Valeur |
|-----------|------|--------|--------|
| `deal_reference` | string | non | "TEST-A" pour filtrer |
| `limit` | int | non | 50 (défaut) |

**Exemples** :
- Tous : `https://factures-backend-qb5x.onrender.com/preconfirmations/`
- Filtré : `https://factures-backend-qb5x.onrender.com/preconfirmations/?deal_reference=TEST-A`

---

## 6. GET /preconfirmations/compare

**Description** : Compare deux versions d'un document

**Méthode** : GET  
**URL** : `https://factures-backend-qb5x.onrender.com/preconfirmations/compare`

### Paramètres (query)

| Paramètre | Type | Requis | Valeur |
|-----------|------|--------|--------|
| `doc_id_a` | string (uuid) | oui | ID du document A |
| `doc_id_b` | string (uuid) | oui | ID du document B |

**Exemple** : `https://factures-backend-qb5x.onrender.com/preconfirmations/compare?doc_id_a=uuid-a&doc_id_b=uuid-b`

---

## 7. POST /extract

**Description** : Extrait les données d'un term sheet PDF

**Méthode** : POST  
**URL** : `https://factures-backend-qb5x.onrender.com/extract`

### Body (multipart/form-data)

| Champ | Type | Valeur |
|-------|------|--------|
| `file` | file | Un fichier PDF de term sheet |

**⚠️ Note** : L'extraction fonctionne mieux avec un PDF contenant du texte (pas un scan).

---

## 8. GET /health

**Description** : Vérifie la connexion Supabase

**Méthode** : GET  
**URL** : `https://factures-backend-qb5x.onrender.com/health`

**Résultat attendu** :
```json
{
  "status": "ok",
  "environment": "production",
  "database": "connected"
}
```

---

## 9. GET /

**Description** : Informations du service

**Méthode** : GET  
**URL** : `https://factures-backend-qb5x.onrender.com/`

---

## Résumé rapide — Valeurs à copier-coller

### Test rapide (Cas A)

```json
{
  "deal_reference": "SWAGGER-TEST",
  "products": [{
    "product_name": "Test Product",
    "notional": 1000000,
    "upfront_fee_rate": 1.50,
    "currency": "EUR",
    "commission_terms": [{
      "introducer_id": "intro-1",
      "commission_type": "bps_notional",
      "commission_value": 50,
      "commission_currency": "EUR"
    }]
  }]
}
```

### Référence des types de commission

| Type | Champ `commission_type` | Champ `commission_value` | Champs fraction |
|------|------------------------|--------------------------|-----------------|
| bps | `"bps_notional"` | nombre de bps (ex: 50) | — |
| part des frais | `"fee_share"` | fraction décimale (ex: 0.3333) | OU `fraction_numerateur` + `fraction_denominateur` |
| fixe | `"flat"` | montant (ex: 5000) | — |

### Devises supportées

- `EUR`, `USD`, `GBP`, `CHF`
