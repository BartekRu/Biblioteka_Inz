from . import auth, books, users, loans, reviews

# Opcjonalnie recommendations
try:
    from . import recommendations
except ImportError:
    pass