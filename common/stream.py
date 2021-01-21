import queue
import time
from threading import Thread

from ibapi.wrapper import EWrapper
from ibapi.client import EClient
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.utils import iswrapper

from .utils import setup_log


logger = setup_log(__name__, "local")


class IBWrapper(EWrapper):

    @iswrapper
    def error(self, id, errorCode, errorString):
        # Overrides the native method
        errormessage = (
            f"IB returns an error with {id} errorcode {errorCode} "
            f"that says {errorString}"
        )
        self.my_errors_queue.put(errormessage)

    @iswrapper
    def tickPrice(self, reqId, tickType, price, attrib):
        logger.debug('The current ask price is: %s with ID %s', price, reqId)

    def init_error(self):
        error_queue = queue.Queue()
        self.my_errors_queue = error_queue

    def is_error(self):
        error_exist = not self.my_errors_queue.empty()
        return error_exist

    def get_error(self, timeout=6):
        if self.is_error():
            try:
                return self.my_errors_queue.get(timeout=timeout)
            except queue.Empty:
                return None
        return None


class IBClient(EClient):

    def __init__(self, wrapper):
        EClient.__init__(self, wrapper)

    def stream(self, contract: Contract, data_id):
        # Request Market Data
        logger.debug("Sending request to the server")
        self.reqMktData(data_id, contract, '', False, False, [])

        logger.debug("Waiting for error response if there is any")
        time.sleep(5)

        while self.wrapper.is_error():
            logger.debug("Error:")
            logger.debug(self.get_error(timeout=10))


class IBApp(IBWrapper, IBClient):

    def __init__(self, ipaddress, portid, clientid):
        self.init_error()

        IBWrapper.__init__(self)
        IBClient.__init__(self, wrapper=self)

        self.connect(ipaddress, portid, clientid)

        thread = Thread(target=self.run)
        thread.start()
        setattr(self, "_thread", thread)


def stream(details: list):
    """
    details: a list of dictionary
      [item1, item2, item3]

    item = {
        "contract": contract,
        "data_id": data_id,
    }
    """
    logger.debug("Connecting to the server...")
    app = IBApp("127.0.0.1", 7497, 0)

    time.sleep(5)
    logger.debug("Inputting contract information")
    for item in details:
        app.stream(**item)

    logger.debug("Starting app to stream data")
    app.run()
