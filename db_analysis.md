# Database State Analysis - nucleus_v12

**Date:** December 9, 2025  
**Database:** nucleus_v12  
**Instance:** nucleus-prototype-db  
**Region:** europe-west1

---

## Current State

### Schemas Found
```
dna_schema         (OLD - with underscore)
tasks_schema       (OLD - with underscore)
agents_schema      (OLD - with underscore)
results_schema     (OLD - with underscore)
public             (standard)
```

### Tables in dna_schema (OLD)
```
- entities
- interests
- capabilities
- dna_profiles
```

### Schemas Expected by Code
```
dna                (NEW - no underscore)
tasks              (NEW - no underscore)
agents             (NEW - no underscore)
results            (NEW - no underscore)
memory             (NEW)
assembly           (NEW)
execution          (NEW)
```

### Tables Expected in dna schema (NEW)
```
- entity           (not entities)
- interests
- goals
- values
- raw_data
- entity_integrations  (NEW - to be added)
```

---

## Issues Identified

### 1. Schema Name Mismatch ❌
**Problem:** Old database uses `dna_schema`, new code expects `dna`  
**Impact:** All SQLAlchemy models will fail  
**Severity:** CRITICAL

### 2. Table Name Mismatch ❌
**Problem:** Old has `entities`, new expects `entity`  
**Impact:** Foreign key references will fail  
**Severity:** CRITICAL

### 3. Migrations Table Structure ❌
**Problem:** Existing `migrations` table has different columns  
**Current:** `id, migration_name, applied_at`  
**Expected:** `id, version, description, executed_at`  
**Impact:** Cannot track new migrations  
**Severity:** HIGH

### 4. Permissions Issue ❌
**Problem:** User `nucleus` doesn't own `migrations` table  
**Owner:** postgres  
**Impact:** Cannot alter table structure  
**Severity:** HIGH

### 5. Vector Extension Missing ⚠️
**Problem:** pgvector extension not installed  
**Impact:** Cannot use embeddings (memory schema)  
**Severity:** MEDIUM (not needed for credentials system)

---

## Root Cause Analysis

### Two Different Database Versions Exist

**Old Version (dna_schema):**
- Created manually or by old terraform
- Uses `_schema` suffix
- Different table names
- Managed by postgres user

**New Version (dna):**
- Defined in `001_init_schemas.sql`
- No `_schema` suffix
- Matches SQLAlchemy models
- Should be managed by nucleus user

### Why This Happened

1. Initial database was created with different naming convention
2. Migration 001 was never run on production
3. Code was developed against local/different database
4. No schema validation in CI/CD

---

## Decision: Path Forward

### Option A: Migrate Old Schema to New (COMPLEX)
**Pros:**
- Preserves existing data
- No data loss

**Cons:**
- Need to rename schemas (requires superuser)
- Need to rename tables
- Need to update all foreign keys
- High risk of breaking existing services
- Complex migration script

### Option B: Create New Schemas Alongside Old (RECOMMENDED)
**Pros:**
- No risk to existing data
- Clean slate for new system
- Can migrate data later if needed
- Existing services continue working

**Cons:**
- Duplicate schemas temporarily
- Need to decide which to use long-term

### Option C: Drop Old and Recreate (RISKY)
**Pros:**
- Clean database
- Matches code exactly

**Cons:**
- **DATA LOSS**
- Breaks existing services
- Not acceptable for production

---

## Recommended Solution: Option B

### Phase 1: Create New Schemas
1. Run migration 001 (already partially done)
2. Fix migrations table issue
3. Verify new schemas created

### Phase 2: Run Migration 002
1. Add entity_integrations table to `dna` schema
2. Update migrations tracking

### Phase 3: Update Code to Use New Schemas
1. Verify all models use correct schema
2. Test connections
3. Deploy services

### Phase 4: Data Migration (Future)
1. Plan data migration from old to new schemas
2. Update references
3. Deprecate old schemas

---

## Immediate Actions Required

### 1. Fix Migrations Table
**Problem:** Cannot alter existing migrations table (permission denied)

**Solution A:** Create new migrations table in different schema
```sql
CREATE TABLE IF NOT EXISTS public.nucleus_migrations (
    id SERIAL PRIMARY KEY,
    version VARCHAR(10) UNIQUE NOT NULL,
    description TEXT,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Solution B:** Use existing table as-is and adapt migration scripts
```sql
-- Insert using existing columns
INSERT INTO public.migrations (migration_name, applied_at)
VALUES ('002_add_entity_integrations', CURRENT_TIMESTAMP);
```

**Recommendation:** Solution B (simpler, less risk)

### 2. Verify New Schemas Created
```sql
SELECT schema_name FROM information_schema.schemata 
WHERE schema_name IN ('dna', 'memory', 'assembly', 'execution', 'tasks', 'agents', 'results');
```

### 3. Check Tables in New dna Schema
```sql
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'dna' 
ORDER BY table_name;
```

### 4. Run Migration 002 with Fixed Migrations Insert
Update migration to use existing migrations table structure

---

## Next Steps

1. ✅ Verify migration 001 created `dna` schema
2. ✅ Check if `entity` table exists in `dna` schema
3. 🔄 Modify migration 002 to work with existing migrations table
4. 🔄 Run migration 002
5. ✅ Verify entity_integrations table created
6. ✅ Test API endpoints
7. ✅ Document final state

---

**Status:** Analysis Complete  
**Next Action:** Verify schema creation and fix migrations table issue
