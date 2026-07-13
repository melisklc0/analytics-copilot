# Superset dashboard exports

Drop a **native Superset dashboard export ZIP** here (Superset UI → dashboard →
Export). The committed ZIP is imported automatically by the `superset-import`
one-shot service after the dbt marts are built.

The importer rewrites each `databases/*.yaml` `sqlalchemy_uri` from environment
variables at import time — the export's masked password is replaced with the
real warehouse connection built from `.env`:

```
postgresql://${SUPERSET_RO_USER}:${SUPERSET_RO_PASSWORD}@${POSTGRES_HOST}:5432/${POSTGRES_DB}
```

So the connection host/port/credentials always follow `.env`; nothing is
hardcoded and the exported connection host does not matter.
