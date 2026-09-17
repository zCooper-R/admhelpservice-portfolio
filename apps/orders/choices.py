from django.db import models


class DescriptiveIntegerChoices(models.IntegerChoices):
    @classmethod
    def get_description(cls, category: int or str):
        if category == '':
            return
        return cls._descriptions().get(int(category))

    @classmethod
    def _descriptions(cls):
        raise NotImplementedError("Subclasses must implement _descriptions()")


class OrderStatus(models.IntegerChoices):
    """
    Статус заявки
    """
    ACCEPTED = 0, 'В очереди'
    IN_WORK = 1, 'В работе'
    DONE = 2, 'Выполнена'
    CLOSED = 3, 'Закрыта'
    CANCELED = 4, 'Отменена'


class OrderWaitingFor(models.TextChoices):
    REQUESTER = "requester", "Ждёт заявителя"
    EXECUTOR = "executor", "Ждёт исполнителя"
    NONE = "none", "Не ожидает ответа"


class OrderPrinterCategory(DescriptiveIntegerChoices):
    """
    Категория принтеров
    """
    REFILL = 0, 'Заправка'
    REPAIR = 1, 'Ремонт'
    CHANGE = 2, 'Замена'
    CONNECT_OR_CONFIGURE = 3, 'Подключение или настройка'
    OTHER = 4, 'Прочее'

    @classmethod
    def _descriptions(cls):
        return {
            cls.REFILL: 'Заправка тонер-картриджей и/или замена расходных материалов принтера. '
                        'После создания заявка автоматически направляется в обслуживающую организацию. '
                        'Вопросы по качеству исполнения заявок по телефону: +79101087053',
            cls.REPAIR: 'Ремонт неисправностей принтера, МФУ, сканера.',
            cls.CHANGE: 'Замена старых устройств на новые, если старые уже не могут обеспечить нужный уровень работы.',
            cls.CONNECT_OR_CONFIGURE: 'Подключение или настройка принтеров, МФУ и сканеров к компьютеру, '
                                      'чтобы обеспечить их работу в сети.',
            cls.OTHER: 'Вопросы, не попадающие под другие подкатегории, связанные с принтером/МФУ/сканером.',
        }


class OrderPcCategory(DescriptiveIntegerChoices):
    """
    Категория ПК
    """

    SOFTWARE_INSTALL = 0, 'Установка программ'
    INTERNET = 1, 'Сеть/Интернет'
    COMPONENTS = 2, 'Неисправность компьютера'
    NEW_ARM = 3, 'Организация АРМ'
    OTHER = 4, 'Прочее'

    @classmethod
    def _descriptions(cls):
        return {
            cls.SOFTWARE_INSTALL: 'Установка и настройка новых программ, устранение проблем с существующими.',
            cls.INTERNET: 'Отсутствие, замедление интернета и другие проблемы со связью.',
            cls.COMPONENTS: 'Ремонт неисправностей компьютера, присоединенных к нему устройств ИТ и другой оргтехники.',
            cls.NEW_ARM: 'Организация нового автоматизированного рабочего места (АРМ) и его составляющих '
                         '(принтер, сканер, веб-камера и пр.). Перемещение существующего АРМ.',
            cls.OTHER: 'Прочие вопросы, связанные с автоматизацией рабочих процессов и ИТ.',
        }


class OrderAhoCategory(DescriptiveIntegerChoices):
    """
    Категория административно-хозяйственная деятельность
    """
    WATER = 0, 'Заказ воды'
    CLEANING = 1, 'Уборка помещений'
    REPAIR = 2, 'Мелкий ремонт'
    STATIONERY = 3, 'Канцтовары'
    OFFICE_EQUIPMENT = 4, 'Офисное оборудование'
    OTHER = 5, 'Прочее'

    @classmethod
    def _descriptions(cls):
        return {
            cls.WATER: 'Заказ и доставка бутилированной воды в офис. '
                       'Доставка осуществляется 1 и 15 числа каждого месяца.',
            cls.CLEANING: 'Запрос уборки помещений.',
            cls.REPAIR: 'Запрос на мелкий ремонт, такой как замена лампочек, ремонт дверей, стула и прочее.',
            cls.STATIONERY: 'Заказ канцелярских товаров, таких как бумага, ручки, блокноты и прочее.',
            cls.OFFICE_EQUIPMENT: 'Мебель (столы, стулья, шкафы, полки и т.д.), '
                                  'осветительные приборы (лампы, светильники и т.д.), '
                                  'системы отопления и кондиционирования воздуха и т.д.',
            cls.OTHER: 'Всё, что не вошло в другие категории.',
        }


class OrderAccountCategory(DescriptiveIntegerChoices):
    """
    Категория учётная запись
    """
    CREATE = 0, 'Создание'
    DISABLE = 1, 'Блокировка'
    CHANGE = 2, 'Изменение'
    RESET_PASSWORD = 3, 'Сброс пароля'
    ACCESS_SHARED = 4, 'Доступ к общим ресурсам'
    SEDO = 5, 'Учётная запись СЭДО'
    INFORMATION_SYSTEMS = 6, 'Доступ к информационным системам'
    EMAIL = 7, 'Служебная электронная почта'
    OTHER = 8, 'Прочее'

    @classmethod
    def _descriptions(cls):
        return {
            cls.CREATE: 'Запрос на создание учётной записи для новых сотрудников, '
                        'обеспечивая им доступ к необходимым ресурсам.',
            cls.DISABLE: 'Запрос на блокировку учётной записи сотрудника, при переводе, увольнении, '
                         'уходе в декрет и других событиях, чтобы обеспечить безопасность данных.',
            cls.CHANGE: 'Если у сотрудника изменилось имя, фамилия или другие данные, связанные с учётной записью.',
            cls.RESET_PASSWORD: 'Если сотрудник не может войти на компьютер из-за забытого пароля, '
                                'мы поможем сбросить пароль и восстановить доступ.',
            cls.ACCESS_SHARED: 'Настройка доступа в доменной сети г.о.г. Арзамас '
                               '(документы отдела, зелёная папка на рабочем столе и т.п.)',
            cls.SEDO: 'Всё, что связано с учётными записями в системе электронного документооборота (СЭДО)',
            cls.INFORMATION_SYSTEMS: 'Запросы, связанные с учётными записями в информационных системах: '
                                     'Закупки, ГАСУ, АЦК, ЕТП и др.',
            cls.EMAIL: 'Создание, изменение, устранение проблем и другие запросы, '
                       'связанные со служебной электронной почтой.',
            cls.OTHER: 'Если ваш запрос не подходит ни под одну из вышеперечисленных категорий.',
        }


class OrderSEDOCategory(DescriptiveIntegerChoices):
    """
    Категория учётная запись СЭДО
    """
    CREATE = 0, 'Создание'
    CHANGE = 1, 'Изменение'
    DELETE = 2, 'Удаление'
    OTHER = 3, 'Прочее'

    @classmethod
    def _descriptions(cls):
        return {
            cls.CREATE: 'Запрос на создание учётной записи СЭДО',
            cls.CHANGE: 'Запрос на изменение учётной записи СЭДО',
            cls.DELETE: 'Запрос на удаление учётной записи СЭДО',
            cls.OTHER: 'Если ваш запрос не подходит ни под одну из вышеперечисленных категорий.',
        }


class OrderDigitalSignCategory(DescriptiveIntegerChoices):
    """
    Категория цифровая подпись
    """
    CREATE = 0, 'Создать'
    UPDATE = 1, 'Продлить'
    CHANGE = 2, 'Изменить'


class OrderVKSCategory(DescriptiveIntegerChoices):
    """
    Категория ВКС
    """
    ORGANIZE = 0, 'Создать трансляцию'
    CONNECT = 1, 'Подключиться к ВКС'
    PRESENTATION = 2, 'Презентация'

    @classmethod
    def _descriptions(cls):
        return {
            cls.ORGANIZE: 'Создание трансляции в Yandex Telemost: название, дата и время, длительность и адрес для отправки ссылки.',
            cls.CONNECT: 'Помощь с подключением к существующей ВКС: место проведения, время, ссылка и необходимое оборудование.',
            cls.PRESENTATION: 'Подготовка презентации: место, время и необходимое оборудование .',
        }


class OrderVKSEquipment(DescriptiveIntegerChoices):
    """
    Оборудование ВКС
    """
    HEAR_REMOTE = 1, 'Нужно слышать собеседника'
    BE_SEEN = 2, 'Нужно, чтобы собеседник видел нас'
    BE_HEARD = 3, 'Нужно, чтобы нас было слышно'
    INTERNET = 4, 'Нужен интернет'
