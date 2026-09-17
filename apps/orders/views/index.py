from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin

from django.views.generic import TemplateView



class IndexPageView(LoginRequiredMixin, SuccessMessageMixin, TemplateView):
    template_name = 'orders/index.html'
