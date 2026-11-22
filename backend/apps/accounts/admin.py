from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import AdminPasswordChangeForm
from django.db import transaction
from apps.core.models import AuditLog
from .models import User,Profile,Address
from .security import blacklist_refresh_tokens


class RevokingAdminPasswordChangeForm(AdminPasswordChangeForm):
    def save(self,commit=True):
        candidate=super().save(commit=False)
        if not commit:
            return candidate
        with transaction.atomic():
            user=User.objects.select_for_update().get(pk=candidate.pk)
            user.password=candidate.password
            user._password=getattr(candidate,'_password',None)
            user.auth_version+=1
            user.save(update_fields=['password','auth_version'])
            blacklist_refresh_tokens(user)
        self.user=user
        return user


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    change_password_form=RevokingAdminPasswordChangeForm
    fieldsets=DjangoUserAdmin.fieldsets+(("ELVAA",{'fields':('role','phone','email_verified','auth_version')}),)
    readonly_fields=('auth_version',)
    list_display=('username','email','role','is_active','is_staff','email_verified')
    list_filter=('role','is_active','is_staff','is_superuser')

    @transaction.atomic
    def save_model(self,request,obj,form,change):
        if not change:
            return super().save_model(request,obj,form,change)
        old=User.objects.select_for_update().get(pk=obj.pk)
        deactivated=old.is_active and not obj.is_active
        obj.auth_version=old.auth_version+1 if deactivated else old.auth_version
        super().save_model(request,obj,form,change)
        if deactivated:
            blacklist_refresh_tokens(obj)
            AuditLog.objects.create(user=request.user,action='admin_user_deactivated',model_name='User',object_id=str(obj.pk))


admin.site.register(Profile)
admin.site.register(Address)
