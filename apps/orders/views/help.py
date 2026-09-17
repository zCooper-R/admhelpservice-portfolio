from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.urls import reverse_lazy
from django.views.generic import CreateView

from apps.orders.forms import HelpForm
from apps.orders.tasks.mail import task_mail_admins_feedback

class HelpPageView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    template_name = 'orders/help.html'
    form_class = HelpForm
    success_url = reverse_lazy('help')
    success_message = 'Обращение успешно отправлено'

    def form_valid(self, form):
        form.instance.from_user = self.request.user
        feedback = form.save()
        if not settings.DEBUG:
            transaction.on_commit(
                lambda: task_mail_admins_feedback.delay(feedback.id)
            )
        return super().form_valid(form)
