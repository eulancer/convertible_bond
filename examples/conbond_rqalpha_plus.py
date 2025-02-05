from rqalpha_plus.apis import *
import pandas as pd
from rqdatac import *

# From https://zhuanlan.zhihu.com/p/157214386

__config__ = {
    'base': {
        'start_date': '20190101',
        'end_date': '20190331',
        'frequency': '1d',
        'accounts': {
            'stock': 1000000
        }
    }
}


def init(context):
    scheduler.run_monthly(rebalance, tradingday=1)
    logger.info('RunInfo: {}'.format(context.run_info))


def rebalance(context, bar_dict):
    context.buy_list = convertible_selection(context)

    sell_list = list(
        set(context.portfolio.positions).difference(set(context.buy_list)))
    for convertible_id in sell_list:
        order_target_percent(convertible_id, 0)
    for convertible_id in context.buy_list:
        order_target_percent(convertible_id, 1 / len(context.buy_list))


def convertible_selection(context):
    conversion_info = get_conversion_info(context)
    conversion_value = (100 / conversion_info['conversion_price']
                        ) * conversion_info['stock_price']
    conversion_value_premium = conversion_info[
        'convertible_price'] / conversion_value - 1
    double_low_factors = conversion_value_premium * 100 + conversion_info[
        'conversion_price']
    if len(double_low_factors) >= 10:
        buy_list = double_low_factors.sort_values(
            ascending=True).iloc[:10].index.tolist()
    else:
        buy_list = double_low_factors.index.tolist()
    return buy_list


def get_conversion_info(context):
    date = context.now
    previous_date = get_previous_trading_date(date, 1)
    convertible_info = convertible.all_instruments(
        context.now).set_index('order_book_id')
    stock_ids = convertible_info.stock_code
    convertible_ids = convertible_info.index
    stock_price = get_price(stock_ids,
                            previous_date,
                            previous_date,
                            adjust_type='none',
                            fields='close')
    stock_price = convertible_info.join(stock_price, on='stock_code').iloc[:,
                                                                           -1]
    convertible_price = get_price(convertible_ids,
                                  previous_date,
                                  previous_date,
                                  adjust_type='none',
                                  fields='close')
    conversion_price_info = convertible.get_conversion_price(convertible_ids,
                                                             start_date=None,
                                                             end_date=date)
    conversion_price = conversion_price_info[
        ~conversion_price_info.index.get_level_values(0).duplicated(
            keep='last')]['conversion_price'].reset_index(1, drop=True)
    conversion_info = pd.concat(
        [stock_price, convertible_price, conversion_price],
        join='inner',
        axis=1)
    conversion_info.columns = [
        'stock_price', 'convertible_price', 'conversion_price'
    ]
    conversion_info.dropna(axis=0, inplace=True)
    return conversion_info
