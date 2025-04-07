import datetime
import logging.config
from environs import Env
from seller import download_stock

import requests

from seller import divide, price_conversion

logger = logging.getLogger(__file__)


def get_product_list(page, campaign_id, access_token):
    """
    Получает с Яндекса список товаров.

    Arguments:
    page - токен страницы с товарами (type: str)
    campaign_id - id компании с товарами (type: str)
    access_token - токен доступа от Яндекса (type: str)

    Returns: 
    Возвращает список не более, чем 200 товаров с заданной страницы.

    Examples:
        Right:
            product_list = get_product_list("323", 343, "djs34")
        Wrong:
            product_list = get_product_list(323, "343", djs34)
    """
    endpoint_url = "https://api.partner.market.yandex.ru/"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Host": "api.partner.market.yandex.ru",
    }
    payload = {
        "page_token": page,
        "limit": 200,
    }
    url = endpoint_url + f"campaigns/{campaign_id}/offer-mapping-entries"
    response = requests.get(url, headers=headers, params=payload)
    response.raise_for_status()
    response_object = response.json()
    return response_object.get("result")


def update_stocks(stocks, campaign_id, access_token):
    """
    Обновляет стоки (товары на складе) на Яндексе.

    Arguments:
    stocks - данные об остатках товаров (type: list)
    campaign_id - id компании с товарами (type: str)
    access_token - токен доступа от Яндекса (type: str)

    Returns: 
    Возвращает ответ сайта.

    Examples:
        Right:
            stocks = create_stocks(watch_remnants, offer_ids, warehouse_id)
            update_stocks = update_stocks(stocks, 343, "djs34")
        Wrong:
            update_stocks = update_stocks(323, "343", djs34)
    """
    endpoint_url = "https://api.partner.market.yandex.ru/"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Host": "api.partner.market.yandex.ru",
    }
    payload = {"skus": stocks}
    url = endpoint_url + f"campaigns/{campaign_id}/offers/stocks"
    response = requests.put(url, headers=headers, json=payload)
    response.raise_for_status()
    response_object = response.json()
    return response_object


def update_price(prices, campaign_id, access_token):
    """
    Обновляет цены на Яндексе.

    Arguments:
    prices - цены товаров (type: list)
    campaign_id - id компании с товарами (type: str)
    access_token - токен доступа от Яндекса (type: str)

    Returns: 
    Возвращает ответ сайта.

    Examples:
        Right:
            prices = create_prices(watch_remnants, offer_ids)
            update_price = update_price(prices, 343, "djs34")
        Wrong:
            update_price = update_price(323, "343", djs34)
    """
    endpoint_url = "https://api.partner.market.yandex.ru/"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Host": "api.partner.market.yandex.ru",
    }
    payload = {"offers": prices}
    url = endpoint_url + f"campaigns/{campaign_id}/offer-prices/updates"
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    response_object = response.json()
    return response_object


def get_offer_ids(campaign_id, market_token):
    """Получает артикулы товаров с Яндекса.

    Arguments:
    campaign_id - id компании с товарами (type: str)
    market_token - токен доступа от Яндекса (type: str)

    Returns: 
    Возвращет список артикулов товаров. (type: list)

    Examples:
        Right:
            offer_ids = get_offer_ids(4535, "dfh45")
        Wrong:
            offer_ids = get_offer_ids("45", 45)
    """
    page = ""
    product_list = []
    while True:
        some_prod = get_product_list(page, campaign_id, market_token)
        product_list.extend(some_prod.get("offerMappingEntries"))
        page = some_prod.get("paging").get("nextPageToken")
        if not page:
            break
    offer_ids = []
    for product in product_list:
        offer_ids.append(product.get("offer").get("shopSku"))
    return offer_ids


def create_stocks(watch_remnants, offer_ids, warehouse_id):
    """Получает остатки товаров на складе.

    Arguments:
    watch_remnats = список часов (type: list)
    offer_ids = список артикулов товаров (type: list)
    warehouse_id = id склада для поиска (type: str)

    Returns: 
    Возвращет список товаров, оставшихся на складе. (type: list)

    Examples:
        Right:
            stocks = create_stocks([], [], "dga5sh5d76")
        Wrong:
            stocks = create_stocks({}, {}, 45)
    """
    # Уберем то, что не загружено в market
    stocks = list()
    date = str(datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z")
    for watch in watch_remnants:
        if str(watch.get("Код")) in offer_ids:
            count = str(watch.get("Количество"))
            if count == ">10":
                stock = 100
            elif count == "1":
                stock = 0
            else:
                stock = int(watch.get("Количество"))
            stocks.append(
                {
                    "sku": str(watch.get("Код")),
                    "warehouseId": warehouse_id,
                    "items": [
                        {
                            "count": stock,
                            "type": "FIT",
                            "updatedAt": date,
                        }
                    ],
                }
            )
            offer_ids.remove(str(watch.get("Код")))
    # Добавим недостающее из загруженного:
    for offer_id in offer_ids:
        stocks.append(
            {
                "sku": offer_id,
                "warehouseId": warehouse_id,
                "items": [
                    {
                        "count": 0,
                        "type": "FIT",
                        "updatedAt": date,
                    }
                ],
            }
        )
    return stocks


def create_prices(watch_remnants, offer_ids):
    """Получает цены товаров.

    Arguments:
    watch_remnats = список часов (type: list)
    offer_ids = список артикулов товаров (type: list)

    Returns: 
    Возвращет список товаров, оставшихся на складе. (type: list)

    Examples:
        Right:
            prices = create_prices([], [])
        Wrong:
            prices = create_prices({}, {})
    """
    prices = []
    for watch in watch_remnants:
        if str(watch.get("Код")) in offer_ids:
            price = {
                "id": str(watch.get("Код")),
                # "feed": {"id": 0},
                "price": {
                    "value": int(price_conversion(watch.get("Цена"))),
                    # "discountBase": 0,
                    "currencyId": "RUR",
                    # "vat": 0,
                },
                # "marketSku": 0,
                # "shopSku": "string",
            }
            prices.append(price)
    return prices


async def upload_prices(watch_remnants, campaign_id, market_token):
    """Получает и обновляет на маркетплейсе цены товаров
    
    Args:
    watch_remnants - список часов (type: list)
    campaign_id - id компании (type: str)
    market_token - api-token продавца от сайта Yandex (type: str)

    Returns:
    Возвращает список цен. (type: list)

    Examples:
        Right:
            prices = upload_prices([], "", "")
        Wrong:
            prices = upload_prices("", {}, 323)
    """
    offer_ids = get_offer_ids(campaign_id, market_token)
    prices = create_prices(watch_remnants, offer_ids)
    for some_prices in list(divide(prices, 500)):
        update_price(some_prices, campaign_id, market_token)
    return prices


async def upload_stocks(watch_remnants, campaign_id, market_token, warehouse_id):
    """Получает и обновляет остатки товаров на складе
    
    Args:
    watch_remnants - список часов (type: list)
    campaign_id - id компании (type: str)
    market_token - api-token продавца от сайта Yandex (type: str)
    warehouse_id = id склада для поиска (type: str)

    Returns:
    Возвращает два списка: один с часами, у которых есть остаток, а второй - со всеми часами. (type: list, list)

    Examples:
        Right:
            response = update_stocks([], "", "", "")
        Wrong:
            response = update_stocks("", {}, 323, 345)
    """
    offer_ids = get_offer_ids(campaign_id, market_token)
    stocks = create_stocks(watch_remnants, offer_ids, warehouse_id)
    for some_stock in list(divide(stocks, 2000)):
        update_stocks(some_stock, campaign_id, market_token)
    not_empty = list(
        filter(lambda stock: (stock.get("items")[0].get("count") != 0), stocks)
    )
    return not_empty, stocks


def main():
    env = Env()
    market_token = env.str("MARKET_TOKEN")
    campaign_fbs_id = env.str("FBS_ID")
    campaign_dbs_id = env.str("DBS_ID")
    warehouse_fbs_id = env.str("WAREHOUSE_FBS_ID")
    warehouse_dbs_id = env.str("WAREHOUSE_DBS_ID")

    watch_remnants = download_stock()
    try:
        # FBS
        offer_ids = get_offer_ids(campaign_fbs_id, market_token)
        # Обновить остатки FBS
        stocks = create_stocks(watch_remnants, offer_ids, warehouse_fbs_id)
        for some_stock in list(divide(stocks, 2000)):
            update_stocks(some_stock, campaign_fbs_id, market_token)
        # Поменять цены FBS
        upload_prices(watch_remnants, campaign_fbs_id, market_token)

        # DBS
        offer_ids = get_offer_ids(campaign_dbs_id, market_token)
        # Обновить остатки DBS
        stocks = create_stocks(watch_remnants, offer_ids, warehouse_dbs_id)
        for some_stock in list(divide(stocks, 2000)):
            update_stocks(some_stock, campaign_dbs_id, market_token)
        # Поменять цены DBS
        upload_prices(watch_remnants, campaign_dbs_id, market_token)
    except requests.exceptions.ReadTimeout:
        print("Превышено время ожидания...")
    except requests.exceptions.ConnectionError as error:
        print(error, "Ошибка соединения")
    except Exception as error:
        print(error, "ERROR_2")


if __name__ == "__main__":
    main()
