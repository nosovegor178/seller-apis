import io
import logging.config
import os
import re
import zipfile
from environs import Env

import pandas as pd
import requests

logger = logging.getLogger(__file__)


def get_product_list(last_id, client_id, seller_token):
    """Получить список товаров магазина озон

    Args:
    last_id - номер последнего товара (type: str)
    client_id - id продавца (type: str)
    seller_token - api-token продавца от сайта Ozon (type: str)

    Returns:
    Возвращает список товаров на маркетплейсе до last_id (type: list)

    Examples:
        Right:
            product_list = get_product_list("", "", "")
        Wrong:
            product_list = get_product_list([], {}, 323)

    """
    url = "https://api-seller.ozon.ru/v2/product/list"
    headers = {
        "Client-Id": client_id,
        "Api-Key": seller_token,
    }
    payload = {
        "filter": {
            "visibility": "ALL",
        },
        "last_id": last_id,
        "limit": 1000,
    }
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    response_object = response.json()
    return response_object.get("result")


def get_offer_ids(client_id, seller_token):
    """Получить артикулы товаров магазина озон
    
    Args:
    client_id - id продавца (type: str)
    seller_token - api-token продавца от сайта Ozon (type: str)

    Returns:
    Возвращает спивок артикулов товаров, которые берутся из функции get_product_list (type: list)

    Examples:
        Right:
            offer_ids = get_offer_ids("", "")
        Wrong:
            offer_ids = get_offer_ids([], 323)
    """
    last_id = ""
    product_list = []
    while True:
        some_prod = get_product_list(last_id, client_id, seller_token)
        product_list.extend(some_prod.get("items"))
        total = some_prod.get("total")
        last_id = some_prod.get("last_id")
        if total == len(product_list):
            break
    offer_ids = []
    for product in product_list:
        offer_ids.append(product.get("offer_id"))
    return offer_ids


def update_price(prices: list, client_id, seller_token):
    """Обновить цены товаров

    Args:
    prices - список цен (type: list)
    client_id - id продавца (type: str)
    seller_token - api-token продавца от сайта Ozon (type: str)

    Returns:
    Возвращает ответ с сайта

    Examples:
        Right:
            response = update_price([], "", "")
        Wrong:
            response = update_price("", {}, 323)
    """
    url = "https://api-seller.ozon.ru/v1/product/import/prices"
    headers = {
        "Client-Id": client_id,
        "Api-Key": seller_token,
    }
    payload = {"prices": prices}
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()


def update_stocks(stocks: list, client_id, seller_token):
    """Обновить остатки
    
    Args:
    stocks - список товаров на складе (type: list)
    client_id - id продавца (type: str)
    seller_token - api-token продавца от сайта Ozon (type: str)

    Returns:
    Возвращает ответ с сайта (type: list)

    Examples:
        Right:
            response = update_stocks([], "", "")
        Wrong:
            response = update_stocks("", {}, 323)
    """
    url = "https://api-seller.ozon.ru/v1/product/import/stocks"
    headers = {
        "Client-Id": client_id,
        "Api-Key": seller_token,
    }
    payload = {"stocks": stocks}
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()


def download_stock():
    """Скачать файл ostatki с сайта casio

    Returns:
    Возвращает список часов, оставшихся на складе (type: list)

    Examples:
        stock = download_stock()
    """
    # Скачать остатки с сайта
    casio_url = "https://timeworld.ru/upload/files/ostatki.zip"
    session = requests.Session()
    response = session.get(casio_url)
    response.raise_for_status()
    with response, zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        archive.extractall(".")
    # Создаем список остатков часов:
    excel_file = "ostatki.xls"
    watch_remnants = pd.read_excel(
        io=excel_file,
        na_values=None,
        keep_default_na=False,
        header=17,
    ).to_dict(orient="records")
    os.remove("./ostatki.xls")  # Удалить файл
    return watch_remnants


def create_stocks(watch_remnants, offer_ids):
    """Создает список товаров на складе для Ozon
    
    Args:
    watch_remnants - список часов (type: list)
    offer_ids - артикулы товаров (type: list)

    Returns:
    Возвращает список остатков товаров для Ozon (type: list)

    Examples:
        Right:
            stocks = create_stocks([], [])
        Wrong:
            stocks = create_stocks("", {})
    """
    # Уберем то, что не загружено в seller
    stocks = []
    for watch in watch_remnants:
        if str(watch.get("Код")) in offer_ids:
            count = str(watch.get("Количество"))
            if count == ">10":
                stock = 100
            elif count == "1":
                stock = 0
            else:
                stock = int(watch.get("Количество"))
            stocks.append({"offer_id": str(watch.get("Код")), "stock": stock})
            offer_ids.remove(str(watch.get("Код")))
    # Добавим недостающее из загруженного:
    for offer_id in offer_ids:
        stocks.append({"offer_id": offer_id, "stock": 0})
    return stocks


def create_prices(watch_remnants, offer_ids):
    """Создает список цен для Ozon
    
    Args:
    watch_remnants - список часов (type: list)
    offer_ids - артикулы товаров (type: list)

    Returns:
    Возвращает список цен для Ozon (type: list)

    Examples:
        Right:
            prices = create_prices([], [])
        Wrong:
            prices = create_prices("", {})
    """
    prices = []
    for watch in watch_remnants:
        if str(watch.get("Код")) in offer_ids:
            price = {
                "auto_action_enabled": "UNKNOWN",
                "currency_code": "RUB",
                "offer_id": str(watch.get("Код")),
                "old_price": "0",
                "price": price_conversion(watch.get("Цена")),
            }
            prices.append(price)
    return prices


def price_conversion(price: str) -> str:
    """Преобразовать цену. Пример: 5'990.00 руб. -> 5990

    Args:
    price - цена до преобразования (type: str)

    Returns:
    Возвращает преобразованную цену (type: str)

    Example:
        Правильно:
            price = price_conversation("5900.00")
        Неправильно:
            price = price_conversation(5900.00)

    """
    return re.sub("[^0-9]", "", price.split(".")[0])


def divide(lst: list, n: int):
    """Разделить список lst на части по n элементов
    
    Args:
    lst - список для разделения (type: list)
    n - количество элементов (type: int)

    Yield:
    Генерирует части списка размером в n элементов (type: list)

    Examples:
        Right:
            divided_list = divide([], 5)
        Wrong:
            divided_list = divide({}, "5")
    """
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


async def upload_prices(watch_remnants, client_id, seller_token):
    """Получает и обновляет на маркетплейсе цены товаров
    
    Args:
    watch_remnants - список часов (type: list)
    client_id - id продавца (type: str)
    seller_token - api-token продавца от сайта Ozon (type: str)

    Returns:
    Возвращает список цен (type: list)

    Examples:
        Right:
            prices = upload_prices([], "", "")
        Wrong:
            prices = upload_prices("", {}, 323)
    """
    offer_ids = get_offer_ids(client_id, seller_token)
    prices = create_prices(watch_remnants, offer_ids)
    for some_price in list(divide(prices, 1000)):
        update_price(some_price, client_id, seller_token)
    return prices


async def upload_stocks(watch_remnants, client_id, seller_token):
    """Получает и обновляет остатки товаров на складе
    
    Args:
    watch_remnants - список часов (type: list)
    client_id - id продавца (type: str)
    seller_token - api-token продавца от сайта Ozon (type: str)

    Returns:
    Возвращает два списка: один с часами, у которых есть остаток, а второй - со всеми часами. (type: list, list)

    Examples:
        Right:
            response = upload_stocks([], "", "")
        Wrong:
            response = upload_stocks("", {}, 323)
    """
    offer_ids = get_offer_ids(client_id, seller_token)
    stocks = create_stocks(watch_remnants, offer_ids)
    for some_stock in list(divide(stocks, 100)):
        update_stocks(some_stock, client_id, seller_token)
    not_empty = list(filter(lambda stock: (stock.get("stock") != 0), stocks))
    return not_empty, stocks


def main():
    env = Env()
    seller_token = env.str("SELLER_TOKEN")
    client_id = env.str("CLIENT_ID")
    try:
        offer_ids = get_offer_ids(client_id, seller_token)
        watch_remnants = download_stock()
        # Обновить остатки
        stocks = create_stocks(watch_remnants, offer_ids)
        for some_stock in list(divide(stocks, 100)):
            update_stocks(some_stock, client_id, seller_token)
        # Поменять цены
        prices = create_prices(watch_remnants, offer_ids)
        for some_price in list(divide(prices, 900)):
            update_price(some_price, client_id, seller_token)
    except requests.exceptions.ReadTimeout:
        print("Превышено время ожидания...")
    except requests.exceptions.ConnectionError as error:
        print(error, "Ошибка соединения")
    except Exception as error:
        print(error, "ERROR_2")


if __name__ == "__main__":
    main()
