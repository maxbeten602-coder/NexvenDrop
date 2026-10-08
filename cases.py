"""
Конфигурация кейсов Nexven Drops
"""

CASES = {
    "free": {
        "id": "free",
        "name": "Фри",
        "price_ton": 0,
        "description": "Бесплатный кейс",
        "image": "/assets/case_free.png",
        "prizes": [
            # обычные подарки (высокий шанс)
            {"id": "heart", "name": "Сердце", "type": "ordinary", "value": 15, "chance": 35.0, "is_nft": False, "image": "❤️"},
            {"id": "rose", "name": "Роза", "type": "ordinary", "value": 25, "chance": 25.0, "is_nft": False, "image": "🌹"},
            {"id": "bear", "name": "Мишка", "type": "ordinary", "value": 50, "chance": 20.0, "is_nft": False, "image": "🧸"},
            {"id": "cake", "name": "Торт", "type": "ordinary", "value": 50, "chance": 12.0, "is_nft": False, "image": "🎂"},
            # небольшой шанс на норм
            {"id": "star", "name": "Звезда", "type": "rare", "value": 100, "chance": 5.0, "is_nft": False, "image": "⭐"},
            {"id": "gift_box", "name": "Подарок", "type": "rare", "value": 150, "chance": 2.5, "is_nft": False, "image": "🎁"},
            {"id": "diamond", "name": "Алмаз", "type": "rare", "value": 200, "chance": 0.5, "is_nft": False, "image": "💎"},
        ]
    },
    "cheap": {
        "id": "cheap",
        "name": "Дешёвый",
        "price_ton": 15,
        "description": "Нищие подарки + небольшой шанс на что-то норм",
        "image": "/assets/case_cheap.png",
        "prizes": [
            {"id": "heart", "name": "Сердце", "type": "ordinary", "value": 15, "chance": 40.0, "is_nft": False, "image": "❤️"},
            {"id": "rose", "name": "Роза", "type": "ordinary", "value": 25, "chance": 25.0, "is_nft": False, "image": "🌹"},
            {"id": "bear", "name": "Мишка", "type": "ordinary", "value": 50, "chance": 15.0, "is_nft": False, "image": "🧸"},
            {"id": "cake", "name": "Торт", "type": "ordinary", "value": 50, "chance": 10.0, "is_nft": False, "image": "🎂"},
            {"id": "star", "name": "Звезда", "type": "rare", "value": 100, "chance": 6.0, "is_nft": False, "image": "⭐"},
            {"id": "gift_box", "name": "Подарок", "type": "rare", "value": 150, "chance": 3.0, "is_nft": False, "image": "🎁"},
            {"id": "ring", "name": "Кольцо", "type": "rare", "value": 250, "chance": 0.8, "is_nft": False, "image": "💍"},
            {"id": "nft_low1", "name": "NFT Лот #1", "type": "nft", "value": 300, "chance": 0.2, "is_nft": True, "image": "🖼️"},
        ]
    },
    "selected": {
        "id": "selected",
        "name": "Избранный",
        "price_ton": 100,
        "description": "Шансы на недорогие NFT + хорошие подарки",
        "image": "/assets/case_selected.png",
        "prizes": [
            {"id": "bear", "name": "Мишка", "type": "ordinary", "value": 50, "chance": 25.0, "is_nft": False, "image": "🧸"},
            {"id": "cake", "name": "Торт", "type": "ordinary", "value": 50, "chance": 20.0, "is_nft": False, "image": "🎂"},
            {"id": "star", "name": "Звезда", "type": "rare", "value": 100, "chance": 18.0, "is_nft": False, "image": "⭐"},
            {"id": "gift_box", "name": "Подарок", "type": "rare", "value": 150, "chance": 15.0, "is_nft": False, "image": "🎁"},
            {"id": "ring", "name": "Кольцо", "type": "rare", "value": 250, "chance": 10.0, "is_nft": False, "image": "💍"},
            {"id": "diamond", "name": "Алмаз", "type": "rare", "value": 300, "chance": 6.0, "is_nft": False, "image": "💎"},
            {"id": "nft_mid1", "name": "NFT Средний #1", "type": "nft", "value": 400, "chance": 3.5, "is_nft": True, "image": "🖼️"},
            {"id": "nft_mid2", "name": "NFT Средний #2", "type": "nft", "value": 500, "chance": 2.0, "is_nft": True, "image": "🖼️"},
            {"id": "nft_good", "name": "NFT Хороший", "type": "nft", "value": 800, "chance": 0.5, "is_nft": True, "image": "👑"},
        ]
    }
}


def get_case(case_id: str):
    return CASES.get(case_id)


def roll_prize(case_id: str):
    """Выбирает приз по шансам"""
    import random
    case = get_case(case_id)
    if not case:
        return None
    
    prizes = case["prizes"]
    total = sum(p["chance"] for p in prizes)
    r = random.uniform(0, total)
    
    cumulative = 0
    for prize in prizes:
        cumulative += prize["chance"]
        if r <= cumulative:
            return prize
    return prizes[-1]  # fallback
