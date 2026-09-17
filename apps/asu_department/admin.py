from django.contrib import admin


from apps.asu_department import models


@admin.register(models.EthernetSocketConnection)
class EthernetSocketConnectionAdmin(admin.ModelAdmin):

    list_display = ['id', 'pc_name', 'ethernet_socket', 'switch_num', 'switch_port', ]
    list_display_links = ('id', )
    search_fields = ['pc_name', 'ethernet_socket', ]
