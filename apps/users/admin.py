from django.contrib import admin
from django.contrib.auth.admin import UserAdmin, GroupAdmin as origGroupAdmin
from django import forms
from django.contrib.auth.models import Group

from apps.users.models import User, SupportSpecialist, TechnicalGroup

admin.site.unregister(Group)

class GroupAdminForm(forms.ModelForm):
    """
    ModelForm that adds a multiple select field for managing
    the users in the group.
    """
    users = forms.ModelMultipleChoiceField(
        User.objects.all(),
        widget=admin.widgets.FilteredSelectMultiple('Users', False),
        required=False,
        )


    def __init__(self, *args, **kwargs):
        super(GroupAdminForm, self).__init__(*args, **kwargs)
        if self.instance.pk:
            initial_users = self.instance.user_set.values_list('pk', flat=True)
            self.initial['users'] = initial_users


    def save(self, *args, **kwargs):
        kwargs['commit'] = True
        return super(GroupAdminForm, self).save(*args, **kwargs)


    def save_m2m(self):
        self.instance.user_set.clear()
        self.instance.user_set.add(*self.cleaned_data['users'])

@admin.register(Group)
class GroupAdmin(origGroupAdmin):
    """
    Customized GroupAdmin class that uses the customized form to allow
    management of users within a group.
    """
    form = GroupAdminForm


class SupportSpecialistAdminForm(forms.ModelForm):
    class Meta:
        model = SupportSpecialist
        fields = '__all__'


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = (
        (None, {"fields": ("username", )}),
        (
            "Персональная информация",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "full_name",
                    "email",
                    "tlg_id",

                ),
            },
        ),
        (
            "Дополнительная информация",
            {
                "fields": (
                    "departament",
                    'address',
                    "cabinet",
                    'post',
                    "phone",
                    "inform_me",
                ),
            },
        ),
        (
            "Статус пользователя",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        ("-", {"fields": ("last_login", "date_joined")}),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        is_superuser = request.user.is_superuser
        disabled_fields = {'last_login', 'date_joined', 'telegram_qrcode'}

        if not is_superuser:
            disabled_fields |= {
                'username',
                'is_superuser',
                'user_permissions',
            }

        # Prevent non-superusers from editing their own permissions
        if (
            not is_superuser
            and obj is not None
            and obj == request.user
        ):
            disabled_fields |= {
                'username',
                'is_staff',
                'is_superuser',
                'groups',
                'user_permissions',
            }

        for f in disabled_fields:
            if f in form.base_fields:
                form.base_fields[f].disabled = True
        return form


@admin.register(SupportSpecialist)
class SupportSpecialistAdmin(admin.ModelAdmin):
    form = SupportSpecialistAdminForm
    list_display = [
        'user',
        'is_available',
        'technical_group'
    ]
    fields = ('user', 'is_available', 'technical_group')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.prefetch_related('user', 'technical_group')

        return queryset


@admin.register(TechnicalGroup)
class TechnicalGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'priority',)
    fields = ('name', 'priority', )
