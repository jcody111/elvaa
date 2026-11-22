from django.contrib import admin
from .models import AuditLog, StoreSettings
admin.site.register(AuditLog)
admin.site.register(StoreSettings)
