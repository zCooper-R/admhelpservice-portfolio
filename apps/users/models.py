from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.auth.models import Group
from utils.tlg_sender import TelegramSender


class User(AbstractUser):
    full_name = models.CharField(max_length=100, verbose_name='Полное имя', blank=True)
    departament = models.CharField(max_length=100, verbose_name='Подразделение', blank=True)
    address = models.CharField(max_length=100, verbose_name='Адрес', blank=True)
    cabinet = models.CharField(max_length=50, verbose_name='Кабинет', blank=True)
    phone = models.CharField(max_length=50, verbose_name='Телефон', blank=True)
    post = models.CharField(max_length=150, verbose_name='Должность', blank=True)
    tlg_id = models.BigIntegerField(verbose_name='Телеграм ID', blank=True, null=True)
    inform_me = models.BooleanField(verbose_name='Уведомлять в телеграм', default=False,
                                    help_text='Отправка уведомлений пользователю в телеграм по его ID.')
    telegram_qrcode = models.ImageField(
        verbose_name='Telegram QRcode',
        upload_to='users/qrcode/telegram/',
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['last_name']

    def __str__(self):
        return self.full_name if self.full_name else self.username

    def get_address(self):
        """
        Return user's address
        """
        return self.address

    def get_cabinet(self):
        """
        Return user's cabinet
        """
        return self.cabinet

    def get_phone(self):
        """
        Return user's phone
        """
        return self.phone

    def get_email(self):
        """
        Return user's email
        """
        return self.email

    def get_tlg(self):
        """
        Return user's telegram id
        """
        return self.tlg_id

    def get_full_name(self):
        """
        Return user's full name
        """
        return self.full_name

    def get_post(self):
        """
        Return user's должность
        """
        return self.post

    def get_departament(self):
        """
        Return user's departament
        """
        return self.departament

    def get_last_name_with_initials(self) -> str:
        """
        Return user's last_name with initials
        Петров Иван Иванович -> Петров И.И.
        """
        full_name = self.get_full_name()
        if full_name and len(full_name.split()) == 3:
            return '{} {:.1}.{:.1}.\n'.format(*full_name.split())
        else:
            return str(self.username)

    def tlg_exists(self):
        return bool(self.tlg_id)

    def mail_exists(self):
        return bool(self.email)

    def send_telegram_message(self, bot: TelegramSender, message: str) -> None:
        bot.send_message(tlg_id=self.get_tlg(), message=message)


class SupportSpecialist(models.Model):
    user = models.OneToOneField(User, verbose_name='Специалист', on_delete=models.CASCADE, related_name='support_specialists')
    is_available = models.BooleanField(verbose_name='Доступен', default=True)
    technical_group = models.ForeignKey(
        'TechnicalGroup',
        verbose_name='Техническая группа',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='specialists',
    )

    class Meta:
        verbose_name = 'Специалист поддержки'
        verbose_name_plural = 'Специалисты поддержки'

    def __str__(self):
        return str(self.user)

    @property
    def tlg_id(self):
        """
        Return user's telegram id
        """
        return self.user.tlg_id

    @property
    def have_tlg_id(self):
        return bool(self.user.tlg_id)

    @property
    def want_receive_telegram_notifications(self):
        """
        Does the specialist want to receive notifications?
        """
        return self.user.inform_me

    def send_telegram_message(self, message: str) -> None:
        bot = TelegramSender()
        bot.send_message(tlg_id=self.tlg_id, message=message)


class TechnicalGroup(models.Model):

    class Priority(models.IntegerChoices):
        """
        Приоритет группы
        """
        HIGH = 1, 'Высокий'
        MID = 2, 'Средний'
        LOW = 3, 'Низкий'

    name = models.CharField(verbose_name='Название', max_length=255)
    priority = models.PositiveSmallIntegerField(
        verbose_name='Приоритет',
        choices=Priority.choices,
        default=Priority.HIGH
    )

    last_assigned_specialist_index = models.SmallIntegerField(
        verbose_name='Последний назначенный специалист',
        null=True,
        blank=True,
        default=0
    )

    class Meta:
        verbose_name = 'Группа специалистов'
        verbose_name_plural = 'Группы специалистов'
        ordering = ['-priority']

    def __str__(self):
        return self.name
