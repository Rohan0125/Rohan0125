import config
import Utility
from finOrder import finApiCall
from logger import logger
from flask import request, Flask
import threading
import warnings
import datetime
import time
warnings.filterwarnings('ignore')

lock = threading.RLock()
app = Flask(__name__)


def placeEntryOrder(action, optnType, symbol, json_data):

    finApi = finApiCall()
    qnty = abs(int(json_data['Q']))
    limitPrice = 0
    transType = 'B' if action == 'BUY' else 'S'

    symbolInfo = Utility.getStrikeNear(
        config.PREMIUM_RANGE[symbol], optnType, symbol)
    config.CURR_TOKEN = symbolInfo['Token']
    config.SYMBOL_INFO = symbolInfo
    limitPrice = 0
    cordertype = 'MKT'
    qty = symbolInfo['LotSize']*qnty
    orderid = finApi.placeorder(
        symbolInfo['TradingSymbol'], transType, qty, cordertype, symbolInfo['Exchange'], price=limitPrice)


def check_loss(ltp, buy_price, quantity, maximum_loss, symbol, optnType, action):
    current_loss = (buy_price - ltp) * quantity
    if current_loss >= maximum_loss:
        exitOpenPositions(symbol, optnType, action)
        return True
    else:
        return False


def getCurrLoss(json_data, max_Loss, action):
    while True:
        current_ltp = Utility.getLTPFin(config.CURR_TOKEN, 'NSE')
        if (check_loss(current_ltp, config.SYMBOL_INFO['ltp'], json_data['Q'], max_Loss, config.SYMBOL_INFO['TS'], config.SYMBOL_INFO['OPT_TYPE'], action)):
            break
        else:
            logger.exception('not in loss for now')
        time.sleep(1)


# def exitOpenPositions(symbol, optnType, action):
#     logger.info(f"Exit {symbol} {optnType} ")
#     finApi = finApiCall()
#     closePosType = 'B' if action == 'SELL' else 'S'
#     finApi.closeOpenPositionBySymbol(symbol, closePosType, optnType=optnType)


def exitOpenPositions(symbol, optnType, tradeType, action):
    if tradeType == 'STOPLOSS':
        Utility.printSendMsg(f'{symbol} {optnType} Stoploss Trigger ')
        if symbol == 'NIFTY':
            token = '26000'
        elif symbol == 'BANKNIFTY':
            token = '26009'
        else:
            token = '26037'
        stoploss_level = Utility.getLTPFin(token, 'NSE')
        current_time = datetime.datetime.now()
        start_of_day = current_time.replace(
            hour=0, minute=0, second=0, microsecond=0)

        m = (current_time - start_of_day).total_seconds()
        TimeS = m - 33300
        interval = 6
        a = interval * 60
        b = TimeS / a
        c = b - int(b)
        d = 1 - c
        x = d * a
        time.sleep(x)
        while not status:
            current_level = Utility.getLTPFin(token, 'NSE')
            if current_level <= stoploss_level:
                # exitOpenPositions(symbol, optnType, action)
                Utility.printSendMsg(f'{symbol} {optnType} STOPLOSS Trigger ')
                status = True
            else:
                status = False
                time.sleep(a)

    logger.info(f"Exit {symbol} {optnType} ")
    finApi = finApiCall()
    closePosType = 'B' if action == 'SELL' else 'S'
    finApi.closeOpenPositionBySymbol(symbol, closePosType, optnType=optnType)
    config.CURR_TOKEN = None


""" 
   {"TT":"BUY","TS":"{{symbol}}","Q":"1","OPT_TYPE":"CE","TRADETYPE":"ENTRY"}
"""

#


@app.route('/tvwebhookfin', methods=['GET', 'POST'])
def webhook():
    message = None
    lock.acquire()
    try:
        if 'application/json' in request.content_type:
            json_data = request.json
            logger.info(json_data)
            if len(json_data) > 0:

                symbol = json_data['TS'].strip()
                if symbol[-1] == '!':
                    symbol = symbol[:-2]

                action = json_data['TT'].strip()
                optType = json_data['OPT_TYPE'].strip()
                tradeType = json_data['TRADETYPE'].strip()

                if symbol.startswith('NIFTY'):
                    symbol = 'NIFTY'
                elif symbol.startswith('BANKNIFTY'):
                    symbol = 'BANKNIFTY'
                else:
                    symbol = 'FINNIFTY'

                if tradeType == 'ENTRY':
                    Utility.printSendMsg(f'{symbol} {optType} Entry Trigger ')
                    placeEntryOrder(action, optType, symbol, json_data)
                    getCurrLoss(json_data, 2000, action)

                elif tradeType == 'EXIT' | tradeType == 'STOPLOSS':
                    Utility.printSendMsg(f'{symbol} {optType} Exit Trigger ')
                    exitOpenPositions(symbol, optType, tradeType, action)

        elif 'text/plain' in request.content_type:
            message = request.get_data().decode("utf-8")
            logger.info(f'{request.content_type} {message}')

    except:
        logger.exception(f'Error occure while reading  message')
    finally:
        lock.release()
    return 'Done'


if __name__ == '__main__':
    Utility.initializer()
    Utility.printSendMsg(f'Finvasia System Started')
    app.run(host='127.0.0.1', port=5000)
