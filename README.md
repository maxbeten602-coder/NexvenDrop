# База данных (папка)

## Структура

```
db/
  users/
    5198310704.json   ← один файл на пользователя
    8133917568.json
  drops.json          ← последние дропы
  withdraws.json      ← заявки на вывод
  stats/
    global.json
```

## Пример users/5198310704.json

```json
{
  "id": 5198310704,
  "username": "user",
  "first_name": "Игрок",
  "balance": 500,
  "inventory": [
    { "id": 123, "name": "Капкейк", "value": 460, "nft": true }
  ],
  "last_free": 0,
  "total_deposited": 0,
  "total_spent": 100,
  "stats": {
    "cases_opened": 5,
    "free_opened": 1,
    "games_played": 3,
    "pickaxe_plays": 2,
    "wins": 4,
    "losses": 2,
    "items_sold": 1,
    "best_drop": "Капкейк",
    "best_drop_value": 460
  },
  "created_at": 1700000000000,
  "updated_at": 1700000000000,
  "last_active": 1700000000000
}
```

Пользователь создаётся при `/start` в боте.
Выдача TON админом пишет сюда + зеркало в Firebase для мини-приложения.
