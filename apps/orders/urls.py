from django.urls import path


from apps.orders.views import (
                               QrCodeTelegramBotView,
                               AjaxOrdersListView, AjaxTasksListView, GlobalUiSummaryView,
                               )
from apps.orders.views import (OrderPCAjaxCreateView,
                               OrderPrinterAjaxCreateView,
                               OrderPrinterSendToTechnoServiceConfirmView,
                               OrderPrinterSendToTechnoServiceView,
                               OrderAhoAjaxCreateView,
                               OrderAccountAjaxCreateView,
                               OrderTransportAjaxCreateView,
                               OrderVKSAjaxCreateView,
                               OrderPrinterAjaxUpdateView,
                               OrderTransportAjaxUpdateView,
                               OrderPCAjaxUpdateView,
                               OrderAhoAjaxUpdateView,
                               OrderAccountAjaxUpdateView,
                               OrderVKSAjaxUpdateView,
                               OrderPrinterAjaxDetailView,
                               OrderTransportAjaxDetailView,
                               OrderPCAjaxDetailView,
                               OrderAhoAjaxDetailView,
                               OrderAccountAjaxDetailView,
                               OrderVKSAjaxDetailView,
                               NotifyTransportUserView)

app_name = 'orders'

urlpatterns = [

    # CREATE
    path('printer/new', OrderPrinterAjaxCreateView.as_view(), name='order_printer_create'),
    path('transport/new', OrderTransportAjaxCreateView.as_view(), name='order_transport_create'),
    path('pc/new', OrderPCAjaxCreateView.as_view(), name='order_pc_create'),
    path('aho/new', OrderAhoAjaxCreateView.as_view(), name='order_aho_create'),
    path('account/new', OrderAccountAjaxCreateView.as_view(), name='order_account_create'),
    path('vks/new', OrderVKSAjaxCreateView.as_view(), name='order_vks_create'),


    # UPDATE
    path('printer/<int:pk>/update', OrderPrinterAjaxUpdateView.as_view(), name='order_printer_update'),
    path('transport/<int:pk>/update', OrderTransportAjaxUpdateView.as_view(), name='order_transport_update'),
    path('pc/<int:pk>/update', OrderPCAjaxUpdateView.as_view(), name='order_pc_update'),
    path('aho/<int:pk>/update', OrderAhoAjaxUpdateView.as_view(), name='order_aho_update'),
    path('account/<int:pk>/update', OrderAccountAjaxUpdateView.as_view(), name='order_account_update'),
    path('vks/<int:pk>/update', OrderVKSAjaxUpdateView.as_view(), name='order_vks_update'),

    # DETAIL
    path('printer/<int:pk>', OrderPrinterAjaxDetailView.as_view(), name='order_printer_detail'),
    path('transport/<int:pk>', OrderTransportAjaxDetailView.as_view(), name='order_transport_detail'),
    path('pc/<int:pk>', OrderPCAjaxDetailView.as_view(), name='order_pc_detail'),
    path('aho/<int:pk>', OrderAhoAjaxDetailView.as_view(), name='order_aho_detail'),
    path('account/<int:pk>', OrderAccountAjaxDetailView.as_view(), name='order_account_detail'),
    path('vks/<int:pk>', OrderVKSAjaxDetailView.as_view(), name='order_vks_detail'),

    # ACTIONS
    path('printer/<int:pk>/send-to-techno-service/confirm', OrderPrinterSendToTechnoServiceConfirmView.as_view(), name='order_printer_send_to_techno_service_confirm'),
    path('printer/<int:pk>/send-to-techno-service', OrderPrinterSendToTechnoServiceView.as_view(), name='order_printer_send_to_techno_service'),

    # OTHER
    path('', AjaxOrdersListView.as_view(), name='orders_list'),
    path('tasks/', AjaxTasksListView.as_view(), name='tasks_list'),
    path('ui-summary/', GlobalUiSummaryView.as_view(), name='ui_summary'),

    path('transport/<int:pk>/notify', NotifyTransportUserView.as_view(), name='notify_user'),

    # path('survey', rating, name='survey'),

    # Active Directory

    # QR Code Telegram Bot

    # path('qr/', QrCodeTelegramBotView.as_view(), name='qr_code_telegram_bot'),
]
