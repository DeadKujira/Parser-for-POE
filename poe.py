import requests
import time
import json
from colorama import Fore, Style, init

# Инициализация цветного вывода
init(autoreset=True)

# Конфигурация
LEAGUE = "Mercenaries"
BASE_SEARCH_URL = f"https://www.pathofexile.com/api/trade/search/{LEAGUE}"
BASE_FETCH_URL = "https://www.pathofexile.com/api/trade/fetch/"

# Параметры поиска
REQUIRED_MODS = [
    {"id": "ultimatum.reward", "value": {"option": "doubles_sacrificed_currency"}},
    {"id": "ultimatum.sacrifice", "value": {"option": "divine_orb"}}
]

BLACKLISTED_MODS = [
    "ultimatum_buff_time_+%_final",          # Buffs Expire Faster
    "ultimatum_escalating_damage_taken_+%",   # Escalating Damage Taken
    "ultimatum_cooldown_recovery_+%",         # Less Cooldown recovery
    "ultimatum_lessened_reach",               # Lessened Reach
    "ultimatum_occasional_impotence",         # Occasional Impotence
    "ultimatum_profane",                      # Profane Monsters
    "ultimatum_recovery_+%_final",            # Reduced Recovery
    "ultimatum_ruin",                         # Ruin
    "ultimatum_siphon_charges",               # Siphoned Charges
    "ultimatum_stalking_ruin",                # Stalking Ruin
    "ultimatum_unlucky_crits",                # Unlucky Criticals
    "ultimatum_no_flasks"                     # Drought
]

def create_search_query():
    """Создает корректный JSON-запрос для поиска"""
    # Создаем фильтры для черного списка модификаторов
    blacklist_filters = [
        {"id": "ultimatum.mod", "value": {"option": mod_id}}
        for mod_id in BLACKLISTED_MODS
    ]
    
    return {
        "query": {
            "status": {"option": "online"},
            "type": "Inscribed Ultimatum",
            "stats": [
                {
                    "type": "and",
                    "filters": REQUIRED_MODS
                },
                {
                    "type": "not",
                    "filters": blacklist_filters
                }
            ]
        },
        "sort": {"price": "asc"}
    }

def search_trade():
    """Выполняет поиск предметов через Trade API"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Content-Type": "application/json"
    }
    
    try:
        # Создаем поисковый запрос
        search_query = create_search_query()
        
        # Отправляем запрос
        response = requests.post(
            BASE_SEARCH_URL,
            json=search_query,
            headers=headers,
            timeout=10
        )
        
        # Проверяем статус ответа
        if response.status_code != 200:
            error_msg = f"HTTP Error {response.status_code}: {response.text}"
            if response.status_code == 400:
                error_msg += "\n\nВозможные причины:\n"
                error_msg += "1. Неверная структура запроса\n"
                error_msg += "2. Неправильные идентификаторы модификаторов\n"
                error_msg += "3. Проблемы с лигой или типом предмета"
            return {"error": error_msg}
        
        return response.json()
    
    except Exception as e:
        return {"error": f"Ошибка при поиске: {str(e)}"}

def fetch_items(item_ids, query_id):
    """Получает детальную информацию о предметах"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    results = []
    
    try:
        # Разбиваем на группы по 10 предметов (ограничение API)
        for i in range(0, len(item_ids), 10):
            chunk = item_ids[i:i+10]
            ids_param = ",".join(chunk)
            url = f"{BASE_FETCH_URL}{ids_param}?query={query_id}"
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                print(Fore.RED + f"Ошибка при получении данных: HTTP {response.status_code}")
                continue
                
            items_data = response.json()
            for result in items_data.get("result", []):
                item = result.get("item", {})
                listing = result.get("listing", {})
                
                # Извлекаем информацию
                mods = [mod["text"] for mod in item.get("mods", [])]
                price = listing.get("price", {})
                account = listing.get("account", {})
                
                results.append({
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "mods": mods,
                    "price_amount": price.get("amount"),
                    "price_currency": price.get("currency"),
                    "seller": account.get("name"),
                    "whisper": listing.get("whisper", "")
                })
            
            # Соблюдаем лимит запросов
            time.sleep(1.2)  # Более безопасная задержка
        
        return results
    
    except Exception as e:
        print(Fore.RED + f"Ошибка при получении данных: {str(e)}")
        return []

def display_results(items):
    """Выводит результаты в удобном формате"""
    if not items:
        print(Fore.YELLOW + "Подходящих предложений не найдено")
        return
    
    print(Fore.GREEN + f"\nНайдено {len(items)} предложений:")
    print("-" * 60)
    
    for idx, item in enumerate(items, 1):
        print(Fore.CYAN + f"#{idx} {item['name']}")
        print(Fore.YELLOW + f"Цена: {item['price_amount']} {item['price_currency']}")
        print(Fore.MAGENTA + f"Продавец: {item['seller']}")
        
        print(Fore.WHITE + "\nМодификаторы:")
        for mod in item["mods"]:
            # Подсвечиваем опасные модификаторы
            if any(bl_mod in mod for bl_mod in [
                "Buffs Expire Faster", "Escalating Damage Taken", "Less Cooldown recovery",
                "Lessened Reach", "Occasional Impotence", "Profane Monsters",
                "Reduced Recovery", "Ruin", "Siphoned Charges", "Stalking Ruin",
                "Unlucky Criticals", "Drought"
            ]):
                print(Fore.RED + f"- {mod} (ОПАСНО!)")
            else:
                print(f"- {mod}")
        
        print(Fore.BLUE + f"Whisper: {item['whisper']}")
        print("-" * 60)

def main():
    print(Fore.CYAN + "=" * 60)
    print(Fore.YELLOW + "ПАРСЕР ULTIMATUM ДЛЯ PATH OF EXILE TRADE")
    print(Fore.CYAN + "=" * 60)
    print(Fore.WHITE + f"Поиск Inscribed Ultimatum с параметрами:")
    print(Fore.GREEN + f"- Награда: Doubles sacrificed Currency")
    print(Fore.GREEN + f"- Требует жертву: Divine Orb")
    print(Fore.RED + f"- Без запрещенных модов ({len(BLACKLISTED_MODS)} шт.)")
    
    print(Fore.WHITE + "\n⌛ Выполняю поиск...")
    
    # Поиск предметов
    search_data = search_trade()
    
    if "error" in search_data:
        print(Fore.RED + "\n❌ ОШИБКА ПОИСКА:")
        print(search_data["error"])
        
        # Дополнительная информация для диагностики
        print(Fore.YELLOW + "\nДополнительные шаги для решения проблемы:")
        print("1. Проверьте актуальность лиги (сейчас установлена: Mercenaries)")
        print("2. Убедитесь, что идентификаторы модификаторов верны")
        print("3. Попробуйте уменьшить количество фильтров")
        print("4. Проверьте доступность сайта: https://www.pathofexile.com/trade")
        return
    
    total = search_data.get("total", 0)
    if total == 0:
        print(Fore.YELLOW + "Предметов не найдено")
        return
    
    print(Fore.GREEN + f"Найдено результатов: {total}")
    
    # Получаем первые 20 результатов
    item_ids = search_data["result"][:20]
    query_id = search_data["id"]
    
    print(Fore.WHITE + "⌛ Получаю детали...")
    items = fetch_items(item_ids, query_id)
    
    # Выводим результаты
    display_results(items)
    
    print(Fore.GREEN + "\nПоиск завершен!")

if __name__ == "__main__":
    main()