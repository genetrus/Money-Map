ROLE_FAMILY_LABELS = {
    "OPS": "Операционные процессы",
    "ADMIN": "Админка / офис / документы",
    "SALES": "Продажи / переговоры / сделки",
    "SUPPORT": "Поддержка / сервис / клиентский контакт",
    "LOGISTICS": "Логистика / перемещения / доставка",
    "MAINTENANCE": "Техобслуживание / ремонт / монтаж",
    "CONTENT": "Контент / творчество / медиа",
    "ANALYTICS": "Аналитика / исследование / настройка систем",
    "UNKNOWN": "Не задано",
}

ROLE_FAMILY_IDS = list(ROLE_FAMILY_LABELS.keys())
DEFAULT_ROLE_FAMILY = "UNKNOWN"


def role_family_label(role_family: str) -> str:
    return ROLE_FAMILY_LABELS.get(role_family, ROLE_FAMILY_LABELS["UNKNOWN"])
