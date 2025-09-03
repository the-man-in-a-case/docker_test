"""
Database router for auth_service.
"""
class AuthServiceRouter:
    """
    A router to control all database operations on models in the
    auth_service application.
    """

    def db_for_read(self, model, **hints):
        """
        Attempts to read auth_service models go to auth_db.
        """
        if model._meta.app_label == 'authentication':
            return 'auth_db'
        return None

    def db_for_write(self, model, **hints):
        """
        Attempts to write auth_service models go to auth_db.
        """
        if model._meta.app_label == 'authentication':
            return 'auth_db'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if a model in the auth_service app is involved.
        """
        if obj1._meta.app_label == 'authentication' or \
           obj2._meta.app_label == 'authentication':
           return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Make sure the auth_service app only appears in the 'auth_db' database.
        """
        if app_label == 'authentication':
            return db == 'auth_db'
        return None