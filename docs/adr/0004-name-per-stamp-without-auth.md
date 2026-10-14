# A Person is a typed name, not an authenticated user

Stamps carry a free-text name, and the Valid transition check and Status run per Person. There is no login, no RBAC and no user store: anyone can stamp for any name. The deck lists user-based stamping and RBAC as optional; we took the per-person behaviour without the auth cost. The name is remembered in a cookie for convenience only, not as identity.
