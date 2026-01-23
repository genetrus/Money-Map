ROLE_FAMILY_LABELS = {
    "operations": "Операционные процессы",
    "admin_office": "Админка / офис",
    "sales": "Продажи / переговоры",
    "support_service": "Поддержка / сервис",
    "logistics": "Логистика / перемещения",
    "maintenance": "Техобслуживание / ремонт",
    "content_creative": "Контент / творчество",
    "analytics": "Аналитика / исследование",
    "management": "Координация / управление",
    "unknown": "Не задано",
}

ROLE_FAMILY_IDS = list(ROLE_FAMILY_LABELS.keys())
DEFAULT_ROLE_FAMILY = "unknown"


def role_family_label(role_family: str) -> str:
    return ROLE_FAMILY_LABELS.get(role_family, ROLE_FAMILY_LABELS["unknown"])
