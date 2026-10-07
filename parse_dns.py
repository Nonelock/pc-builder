#!/usr/bin/env python3
"""
Парсер DNS (dns-shop.ru) для сбора каталога комплектующих ПК.

Требования:
  pip install requests beautifulsoup4 lxml

Запуск:
  python parse_dns.py

Результат:
  catalog-dns.json — каталог в формате, совместимом с PC Сборщиком.

Важно:
  - Структура и классы на сайте DNS могут меняться — скрипт потребует поддержки.
  - Уважай robots.txt и условия использования сайта. Не ставь слишком маленький интервал между запросами.
  - Этот скрипт — образовательный пример. Для продакшена лучше использовать официальные API/фиды магазинов.
"""

import time
import re
import json
from urllib.parse import urljoin, quote

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.dns-shop.ru"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)

# Категории DNS (примерные, могут потребовать уточнения)
CATEGORIES = {
    "cpu": "https://www.dns-shop.ru/catalog/17a8a01d16404e77/processory/",
    "board": "https://www.dns-shop.ru/catalog/17a8a2fe16404e77/materinskie-platy/",
    "ram": "https://www.dns-shop.ru/catalog/17a8a0c516404e77/operativnaya-pamyat/",
    "gpu": "https://www.dns-shop.ru/catalog/17a8a5b416404e77/videokarty/",
    "cooler": "https://www.dns-shop.ru/catalog/17a8a0e516404e77/sistemy-ohlazhdeniya/",
    "psu": "https://www.dns-shop.ru/catalog/17a8a04016404e77/bloki-pitaniya/",
    "case": "https://www.dns-shop.ru/catalog/17a8a03816404e77/korpusa/",
    "ssd": "https://www.dns-shop.ru/catalog/17a8a0a216404e77/tverdotelnye-nakopiteli-ssd/",
}

# Ограничение по количеству страниц для каждой категории (для теста)
MAX_PAGES = 3
SLEEP_BETWEEN_PAGES = 2.0  # секунды


def fetch_html(url):
    resp = SESSION.get(url, timeout=20)
    resp.raise_for_status()
    return resp.text


def parse_price(price_str):
    if not price_str:
        return 0
    # Убираем пробелы как разделители тысяч, оставляем цифры
    digits = re.sub(r"[^\d]", "", price_str)
    return int(digits) if digits else 0


def extract_text(el):
    return el.get_text(strip=True) if el else ""


def parse_cpu(html):
    """
    Парсинг процессоров.
    Возвращает список dict с полями:
      id, name, socket, tdp, price, cores, gen, pcie
    """
    soup = BeautifulSoup(html, "lxml")
    items = []
    products = soup.select(".catalog-item")
    for p in products:
        try:
            name_el = p.select_one(".product-title a")
            name = extract_text(name_el)
            price_el = p.select_one(".product-price .price-value")
            price = parse_price(extract_text(price_el))

            # Характеристики: ищем блоки с data-origin-title или .product-specification
            specs = {}
            for row in p.select(".product-specification li"):
                key_el = row.select_one(".product-specification-name")
                val_el = row.select_one(".product-specification-value")
                if key_el and val_el:
                    key = extract_text(key_el).lower()
                    val = extract_text(val_el)
                    specs[key] = val

            # Сокет, TDP, ядра — примерная логика, зависит от верстки DNS
            socket = ""
            for k in ["socket", "разъем"]:
                if k in specs:
                    socket = specs[k]
                    break

            tdp = 0
            for k in ["tdp", "тепловыделение"]:
                if k in specs:
                    tdp = parse_price(specs[k])
                    break

            cores = 0
            for k in ["количество ядер", "ядер"]:
                if k in specs:
                    cores = parse_price(specs[k])
                    break

            # Поколение и PCIe — эвристика по названию
            gen = ""
            if "ryzen 5" in name.lower() or "ryzen 7" in name.lower() or "ryzen 9" in name.lower():
                if "7000" in name:
                    gen = "Zen4"
                elif "5000" in name:
                    gen = "Zen3"
                else:
                    gen = "AM4-family"
            elif "core i" in name.lower():
                if "14" in name:
                    gen = "Raptor"
                elif "13" in name:
                    gen = "Raptor"
                elif "12" in name:
                    gen = "Alder"
                else:
                    gen = "Intel-gen"

            pcie = "5.0" if "5.0" in name else "4.0"

            # Формируем id из названия (транслит + обрезка)
            id_part = re.sub(r"[^0-9a-zA-Z]", "", name.split()[0].lower())[:12]
            if not id_part:
                id_part = f"cpu_{len(items)}"

            items.append({
                "id": id_part,
                "name": name,
                "socket": socket,
                "tdp": tdp,
                "price": price,
                "cores": cores,
                "gen": gen,
                "pcie": pcie,
            })
        except Exception:
            continue
    return items


def parse_board(html):
    """
    Парсинг материнских плат.
    Возвращает:
      id, name, socket, ram_type, form, m2_slots, sata_ports, price, bios_note
    """
    soup = BeautifulSoup(html, "lxml")
    items = []
    products = soup.select(".catalog-item")
    for p in products:
        try:
            name_el = p.select_one(".product-title a")
            name = extract_text(name_el)
            price_el = p.select_one(".product-price .price-value")
            price = parse_price(extract_text(price_el))

            specs = {}
            for row in p.select(".product-specification li"):
                key_el = row.select_one(".product-specification-name")
                val_el = row.select_one(".product-specification-value")
                if key_el and val_el:
                    key = extract_text(key_el).lower()
                    val = extract_text(val_el)
                    specs[key] = val

            socket = ""
            for k in ["socket", "разъем"]:
                if k in specs:
                    socket = specs[k]
                    break

            ram_type = "DDR4"
            for k in ["тип памяти", "поддерживаемая память"]:
                if k in specs:
                    v = specs[k].upper()
                    if "DDR5" in v:
                        ram_type = "DDR5"
                    elif "DDR4" in v:
                        ram_type = "DDR4"
                    break

            form = "ATX"
            for k in ["форм-фактор"]:
                if k in specs:
                    v = specs[k].upper()
                    if "MATX" in v or "M-ATX" in v:
                        form = "mATX"
                    elif "ITX" in v:
                        form = "ITX"
                    elif "ATX" in v:
                        form = "ATX"
                    break

            m2_slots = 0
            for k in ["m.2", "разъем m.2"]:
                if k in specs:
                    # часто "1 x M.2", "2 x M.2"
                    m = re.search(r"\d+", specs[k])
                    if m:
                        m2_slots = int(m.group())
                    break

            sata_ports = 4
            for k in ["sata", "разъем sata"]:
                if k in specs:
                    m = re.search(r"\d+", specs[k])
                    if m:
                        sata_ports = int(m.group())
                    break

            bios_note = ""
            if "b450" in name.lower() and ("ryzen 5000" in name.lower() or "5000" in name):
                bios_note = "Может требовать обновления BIOS для Ryzen 5000"

            id_part = re.sub(r"[^0-9a-zA-Z]", "", name.split()[0].lower())[:12]
            if not id_part:
                id_part = f"board_{len(items)}"

            items.append({
                "id": id_part,
                "name": name,
                "socket": socket,
                "ram_type": ram_type,
                "form": form,
                "m2_slots": m2_slots,
                "sata_ports": sata_ports,
                "price": price,
                "bios_note": bios_note,
            })
        except Exception:
            continue
    return items


def parse_ram(html):
    soup = BeautifulSoup(html, "lxml")
    items = []
    products = soup.select(".catalog-item")
    for p in products:
        try:
            name_el = p.select_one(".product-title a")
            name = extract_text(name_el)
            price_el = p.select_one(".product-price .price-value")
            price = parse_price(extract_text(price_el))

            specs = {}
            for row in p.select(".product-specification li"):
                key_el = row.select_one(".product-specification-name")
                val_el = row.select_one(".product-specification-value")
                if key_el and val_el:
                    key = extract_text(key_el).lower()
                    val = extract_text(val_el)
                    specs[key] = val

            ram_type = "DDR4"
            capacity = 0
            speed = 0

            for k in ["тип памяти"]:
                if k in specs:
                    v = specs[k].upper()
                    if "DDR5" in v:
                        ram_type = "DDR5"
                    elif "DDR4" in v:
                        ram_type = "DDR4"
                    break

            for k in ["объем", "общий объем"]:
                if k in specs:
                    m = re.search(r"(\d+)\s*гб", specs[k], re.IGNORECASE)
                    if m:
                        capacity = int(m.group(1))
                    break

            for k in ["частота", "тактовая частота"]:
                if k in specs:
                    m = re.search(r"(\d+)", specs[k])
                    if m:
                        speed = int(m.group(1))
                    break

            id_part = re.sub(r"[^0-9a-zA-Z]", "", name.split()[0].lower())[:12]
            if not id_part:
                id_part = f"ram_{len(items)}"

            items.append({
                "id": id_part,
                "name": name,
                "ram_type": ram_type,
                "capacity": capacity,
                "speed": speed,
                "price": price,
            })
        except Exception:
            continue
    return items


def parse_gpu(html):
    soup = BeautifulSoup(html, "lxml")
    items = []
    products = soup.select(".catalog-item")
    for p in products:
        try:
            name_el = p.select_one(".product-title a")
            name = extract_text(name_el)
            price_el = p.select_one(".product-price .price-value")
            price = parse_price(extract_text(price_el))

            specs = {}
            for row in p.select(".product-specification li"):
                key_el = row.select_one(".product-specification-name")
                val_el = row.select_one(".product-specification-value")
                if key_el and val_el:
                    key = extract_text(key_el).lower()
                    val = extract_text(val_el)
                    specs[key] = val

            length = 0
            for k in ["длина", "длина видеокарты"]:
                if k in specs:
                    m = re.search(r"(\d+)", specs[k])
                    if m:
                        length = int(m.group(1))
                    break

            tdp = 0
            for k in ["tdp", "энергопотребление"]:
                if k in specs:
                    tdp = parse_price(specs[k])
                    break

            connectors = []
            if "rtx 40" in name.lower() and "super" in name.lower():
                connectors.append("12VHPWR")
            else:
                # Эвристика: если мощная карта — предполагаем 8-pin
                if tdp > 150:
                    connectors = ["8-pin"]
                else:
                    connectors = ["8-pin"]

            pcie = "4.0"

            id_part = re.sub(r"[^0-9a-zA-Z]", "", name.split()[0].lower())[:12]
            if not id_part:
                id_part = f"gpu_{len(items)}"

            items.append({
                "id": id_part,
                "name": name,
                "length": length,
                "tdp": tdp,
                "price": price,
                "pcie": pcie,
                "connectors": connectors,
            })
        except Exception:
            continue
    return items


def parse_cooler(html):
    soup = BeautifulSoup(html, "lxml")
    items = []
    products = soup.select(".catalog-item")
    for p in products:
        try:
            name_el = p.select_one(".product-title a")
            name = extract_text(name_el)
            price_el = p.select_one(".product-price .price-value")
            price = parse_price(extract_text(price_el))

            specs = {}
            for row in p.select(".product-specification li"):
                key_el = row.select_one(".product-specification-name")
                val_el = row.select_one(".product-specification-value")
                if key_el and val_el:
                    key = extract_text(key_el).lower()
                    val = extract_text(val_el)
                    specs[key] = val

            cooler_type = "air"
            height = 0
            radiator = 0
            sockets = ["AM4", "AM5", "LGA1700"]

            if "сво" in name.lower() or "сжо" in name.lower() or "aio" in name.lower():
                cooler_type = "aio"
                for k in ["размер радиатора", "радиатор"]:
                    if k in specs:
                        m = re.search(r"(\d+)", specs[k])
                        if m:
                            radiator = int(m.group(1))
                        break
            else:
                for k in ["высота", "высота кулера"]:
                    if k in specs:
                        m = re.search(r"(\d+)", specs[k])
                        if m:
                            height = int(m.group(1))
                        break

            id_part = re.sub(r"[^0-9a-zA-Z]", "", name.split()[0].lower())[:12]
            if not id_part:
                id_part = f"cooler_{len(items)}"

            item = {
                "id": id_part,
                "name": name,
                "type": cooler_type,
                "price": price,
                "sockets": sockets,
            }
            if cooler_type == "air":
                item["height"] = height
            else:
                item["radiator"] = radiator

            items.append(item)
        except Exception:
            continue
    return items


def parse_psu(html):
    soup = BeautifulSoup(html, "lxml")
    items = []
    products = soup.select(".catalog-item")
    for p in products:
        try:
            name_el = p.select_one(".product-title a")
            name = extract_text(name_el)
            price_el = p.select_one(".product-price .price-value")
            price = parse_price(extract_text(price_el))

            specs = {}
            for row in p.select(".product-specification li"):
                key_el = row.select_one(".product-specification-name")
                val_el = row.select_one(".product-specification-value")
                if key_el and val_el:
                    key = extract_text(key_el).lower()
                    val = extract_text(val_el)
                    specs[key] = val

            wattage = 0
            for k in ["мощность", "номинальная мощность"]:
                if k in specs:
                    m = re.search(r"(\d+)", specs[k])
                    if m:
                        wattage = int(m.group(1))
                    break

            form = "ATX"
            for k in ["форм-фактор"]:
                if k in specs:
                    v = specs[k].upper()
                    if "ATX" in v:
                        form = "ATX"
                    elif "SFX" in v:
                        form = "SFX"
                    break

            cpu_connectors = 1
            pcie_8pin = 2
            has_12vhpwr = "12vhpwr" in name.lower() or "12 vhpwr" in name.lower()

            id_part = re.sub(r"[^0-9a-zA-Z]", "", name.split()[0].lower())[:12]
            if not id_part:
                id_part = f"psu_{len(items)}"

            items.append({
                "id": id_part,
                "name": name,
                "wattage": wattage,
                "form": form,
                "price": price,
                "cpu_connectors": cpu_connectors,
                "pcie_8pin": pcie_8pin,
                "has_12vhpwr": has_12vhpwr,
            })
        except Exception:
            continue
    return items


def parse_case(html):
    soup = BeautifulSoup(html, "lxml")
    items = []
    products = soup.select(".catalog-item")
    for p in products:
        try:
            name_el = p.select_one(".product-title a")
            name = extract_text(name_el)
            price_el = p.select_one(".product-price .price-value")
            price = parse_price(extract_text(price_el))

            specs = {}
            for row in p.select(".product-specification li"):
                key_el = row.select_one(".product-specification-name")
                val_el = row.select_one(".product-specification-value")
                if key_el and val_el:
                    key = extract_text(key_el).lower()
                    val = extract_text(val_el)
                    specs[key] = val

            forms = ["ATX", "mATX", "ITX"]
            for k in ["форм-фактор", "поддерживаемые платы"]:
                if k in specs:
                    v = specs[k].upper()
                    forms = []
                    if "ATX" in v:
                        forms.append("ATX")
                    if "MATX" in v or "M-ATX" in v:
                        forms.append("mATX")
                    if "ITX" in v or "MINI-ITX" in v:
                        forms.append("ITX")
                    if "E-ATX" in v:
                        forms.append("E-ATX")
                    break

            gpu = 360
            for k in ["макс. длина видеокарты", "длина видеокарты"]:
                if k in specs:
                    m = re.search(r"(\d+)", specs[k])
                    if m:
                        gpu = int(m.group(1))
                    break

            cooler = 170
            for k in ["макс. высота кулера", "высота кулера"]:
                if k in specs:
                    m = re.search(r"(\d+)", specs[k])
                    if m:
                        cooler = int(m.group(1))
                    break

            radiators = []
            for k in ["поддержка радиаторов", "установка водяного охлаждения"]:
                if k in specs:
                    v = specs[k].upper()
                    if "120" in v:
                        radiators.append(120)
                    if "240" in v:
                        radiators.append(240)
                    if "360" in v:
                        radiators.append(360)
                    break

            psu = ["ATX"]

            id_part = re.sub(r"[^0-9a-zA-Z]", "", name.split()[0].lower())[:12]
            if not id_part:
                id_part = f"case_{len(items)}"

            items.append({
                "id": id_part,
                "name": name,
                "forms": forms,
                "gpu": gpu,
                "cooler": cooler,
                "radiators": radiators,
                "psu": psu,
                "price": price,
            })
        except Exception:
            continue
    return items


def parse_ssd(html):
    soup = BeautifulSoup(html, "lxml")
    items = []
    products = soup.select(".catalog-item")
    for p in products:
        try:
            name_el = p.select_one(".product-title a")
            name = extract_text(name_el)
            price_el = p.select_one(".product-price .price-value")
            price = parse_price(extract_text(price_el))

            specs = {}
            for row in p.select(".product-specification li"):
                key_el = row.select_one(".product-specification-name")
                val_el = row.select_one(".product-specification-value")
                if key_el and val_el:
                    key = extract_text(key_el).lower()
                    val = extract_text(val_el)
                    specs[key] = val

            interface = "M.2"
            for k in ["интерфейс", "разъем"]:
                if k in specs:
                    v = specs[k].upper()
                    if "SATA" in v and "M.2" not in v:
                        interface = "SATA"
                    elif "M.2" in v:
                        interface = "M.2"
                    break

            capacity = 0
            for k in ["объем", "емкость"]:
                if k in specs:
                    m = re.search(r"(\d+)\s*гб", specs[k], re.IGNORECASE)
                    if m:
                        capacity = int(m.group(1))
                    break

            id_part = re.sub(r"[^0-9a-zA-Z]", "", name.split()[0].lower())[:12]
            if not id_part:
                id_part = f"ssd_{len(items)}"

            items.append({
                "id": id_part,
                "name": name,
                "interface": interface,
                "capacity": capacity,
                "price": price,
            })
        except Exception:
            continue
    return items


PARSERS = {
    "cpu": parse_cpu,
    "board": parse_board,
    "ram": parse_ram,
    "gpu": parse_gpu,
    "cooler": parse_cooler,
    "psu": parse_psu,
    "case": parse_case,
    "ssd": parse_ssd,
}


def fetch_category(key, url):
    all_items = []
    page = 1
    base = url.rstrip("/")
    while page <= MAX_PAGES:
        if page == 1:
            page_url = base + "/"
        else:
            page_url = base + f"?page={page}"
        print(f"[{key}] Страница {page}: {page_url}")
        html = fetch_html(page_url)
        parser = PARSERS[key]
        items = parser(html)
        all_items.extend(items)
        print(f"[{key}] Найдено товаров на странице: {len(items)}")
        time.sleep(SLEEP_BETWEEN_PAGES)
        page += 1
    return all_items


def main():
    catalog = {}
    for key, url in CATEGORIES.items():
        print(f"Парсим категорию: {key}")
        try:
            items = fetch_category(key, url)
            catalog[key] = items
            print(f"[{key}] Всего: {len(items)}")
        except Exception as e:
            print(f"[{key}] Ошибка: {e}")
            catalog[key] = []

    with open("catalog-dns.json", "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    print("Готово. Файл catalog-dns.json создан.")


if __name__ == "__main__":
    main()
