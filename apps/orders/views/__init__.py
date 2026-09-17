from apps.orders.views.ajax import AjaxOrdersListView, AjaxTasksListView, GlobalUiSummaryView
from apps.orders.views.account import (
    OrderAccountAjaxDetailView,
    OrderAccountAjaxUpdateView,
    OrderAccountAjaxCreateView,
)
from apps.orders.views.aho import (
    OrderAhoAjaxDetailView,
    OrderAhoAjaxUpdateView,
    OrderAhoAjaxCreateView,
)
from apps.orders.views.pc import (
    OrderPCAjaxDetailView,
    OrderPCAjaxUpdateView,
    OrderPCAjaxCreateView,
)
from apps.orders.views.printer import (
    OrderPrinterAjaxDetailView,
    OrderPrinterAjaxUpdateView,
    OrderPrinterAjaxCreateView,
    OrderPrinterSendToTechnoServiceConfirmView,
    OrderPrinterSendToTechnoServiceView,
)
from apps.orders.views.qrcode import QrCodeTelegramBotView
from apps.orders.views.transport import (
    OrderTransportAjaxDetailView,
    OrderTransportAjaxUpdateView,
    NotifyTransportUserView,
    OrderTransportAjaxCreateView,
)
from apps.orders.views.vks import (
    OrderVKSAjaxDetailView,
    OrderVKSAjaxUpdateView,
    OrderVKSAjaxCreateView,
)
