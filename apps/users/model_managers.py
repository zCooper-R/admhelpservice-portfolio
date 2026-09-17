from django.db import models


class SupportSpecialistManager(models.Manager):

    def prefetch_related_all(self):
        return self.get_queryset().prefetch_related('technical_group', 'user',)
