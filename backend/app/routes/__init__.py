from . import auth, books, users, loans, reviews

# Opcjonalnie recommendations
try:
    from . import recommendations
except ImportError:
    pass

# 🆕 Opcjonalnie views (jeśli masz)
try:
    from . import views
except ImportError:
    pass
