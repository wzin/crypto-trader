import os
import sys

sys.path.append("/Users/wojtek/Sources/btce-api/")

import btceapi

from decorators import debug
import sqlalchemy as sa




class Secrets:
    key='3VHY49XV-915CL848-ZL4GZZRW-U0IMFDLY-CHSQTXK0'
    secret='02bc45897f501efeb23c4fb0645e290175bad695536c0332ddc40da553276da1'

class KeyFileManager:
    def __init__(self, key_file_path):
        self.key_file = key_file_path
        self.handler = btceapi.KeyHandler(self.key_file, resaveOnDeletion=True)

    def get_handler(self):
        return self.handler

class Database():
    '''
    - Database should manage DB migrations and abstraction
    - Should return database object to interact with
    '''
    def __init__(self):
        self.sqlite_db_path = "trader.db"
        self.db = sa.create_engine('sqlite:///' + self.sqlite_db_path)
        self.metadata = sa.MetaData(self.db)
        self.db_migrate()

    def db_migrate(self):
        create_db = not os.path.isfile(self.sqlite_db_path)
        if create_db:
            print "Creating database"
            print "...secrets table"
            secrets = sa.Table('secrets', self.metadata,
                    sa.Column('id', sa.Integer, primary_key=True),
                    sa.Column('slug', sa.String(20)),
                    sa.Column('value', sa.String(100))
                    )
            secrets.create()
            i = secrets.insert()
            i.execute({'slug' : 'key', 'value' : Secrets.key},
                      {'slug' : 'secret', 'value' : Secrets.secret}
                    )
            print "...currencies table"
            currencies = sa.Table('currencies', self.metadata,
                    sa.Column('id', sa.Integer, primary_key=True),
                    sa.Column('symbol', sa.String(16)),
                    sa.Column('name', sa.String(100))
                    )
            currencies.create()
            i = currencies.insert()
            i.execute({'symbol' : 'USD', 'name' : 'United States Dollar'},
                      {'symbol' : 'BTC', 'name' : 'Bitcoin'},
                      {'symbol' : 'LTC', 'name' : 'Litecoin'},
                      {'symbol' : 'PPC', 'name' : 'Peercoin'},
                      {'symbol' : 'FTC', 'name' : 'Feathercoin'},
                      {'symbol' : 'NMC', 'name' : 'Namecoin'}
                      )
            print "...done creating tables"

    def get_db(self):
        return self.db

class CurrencyPair:
    ''' Return currency pair cost of conversion with respect to fee '''
    def __init__(self, currency_from, currency_to, cost):
        self.pair = {'from' : currency_from,
                     'to'   : currency_to,
                     'cost' : cost}
    def refresh(self):
        ''' Tell api to refresh values '''
        pass
    
    def data(self):
        return self.pair

class TradeGraph:
    ''' 
    - TradeGraph should keep the graph of currency pairs with all transition costs
    - TradeGraph should propose profitable transaction chains
        * example transaction triad : ['ltc_btc', 'btc_ftc', 'ftc_ltc']
    - TradeGraph should be initialized with dictionary of pair costs
    '''
    def __init__(self, pairs_exchange_rates, graph_depth, trade_fee):
        self.pairs_exchange_rates = [ CurrencyPair('ltc','usd', 15.42).data(),
                                      CurrencyPair('btc','usd', 612.19).data(),
                                      CurrencyPair('ppc','usd', 4.017).data(),
                                      CurrencyPair('nmc','usd', 3.737).data(),
                                      CurrencyPair('ftc','btc', 0.0004).data(),
                                      CurrencyPair('ltc','btc', 0.02512).data(),
                                      CurrencyPair('nmc','btc', 0.00606).data(),
                                      CurrencyPair('ppc','btc', 0.00651).data()
                                      ]
        self.graph = self.init_graph(graph_depth)                                                   
        self.trade_fee = 0.02
        self.graph_depth = 5
    
    def init_graph(self, graph_depth):
        ''' find all permutations of compatible transitions - length should be equal to graph_depth'''
        pass
    
    def refresh_graph(self):
        ''' Iterate through thru all CurrencyPairs and refresh pair cost'''
        pass
    
class MarketKnowledge:
    '''
    - Knowledge should be able to access database but leave
    all the lower level logic to Database class
    - Knowledge should provide API abstraction
    '''
    def __init__(self, key_file_path):
        self.handler = KeyFileManager(key_file_path).get_handler()
        self.db = self.init_database()
        self.trade_api = self.init_trade_api()
        self.all_currencies = btceapi.all_currencies
        self.graph = TradeGraph()
        
    def __repr__(self):
        return str(self.handler)

    def init_database(self):
        db = Database().get_db()
        return db

    def init_trade_api(self):
        try:
            self.api_connection = btceapi.BTCEConnection()
            self.key = self.handler.getKeys()[0]
            trade_api = btceapi.TradeAPI(self.key, self.handler)
            return trade_api
        except Exception, e:
            print "Could not initialize API because %s" % e
            raise
    @debug
    def get_pair_depth(self, pair):
        ''' Returns asks and bids '''
        asks, bids = btceapi.getDepth(pair)
        ask_prices, ask_volumes = zip(*asks)
        bid_prices, bid_volumes = zip(*bids)
        pair_depth = {pair: {'ask_prices': ask_prices,
                             'ask_volumes': ask_volumes,
                             'bid_prices': bid_prices, 
                             'bid_volumes' : bid_volumes
                             }
                      }
        return pair_depth
    
    def get_all_depth(self):
        all_pairs_depth = {}
        for pair in btceapi.all_pairs:
            pair_depth = self.get_pair_depth(pair)
            all_pairs_depth[pair] = pair_depth
        return all_pairs_depth

    def get_ticker(self, pair):
        ''' Returns high, low, avg, etc '''
        pass

    def get_trade_fee(self, pair):
        ''' Returns exchange's trade fee '''
        pass

    def get_info(self):
        ''' Returns dictionary that contains all needed data '''
        r = self.trade_api.getInfo(connection = self.api_connection)
        balances = self.get_balances(r)
        open_orders = self.get_open_orders()
        transaction_history_count = self.get_transaction_history_count(r)
        market_depth = self.get_all_depth()
        info = {'balances' : balances,
                'open_orders' : open_orders,
                'transaction_history_count' : transaction_history_count,
                'market_depth' : market_depth
                }
        return info

    def get_transaction_history_count(self, r):
        return r.transaction_count


    def get_open_orders(self):
        orders = self.trade_api.activeOrders(connection = self.api_connection)
        orders_list = {}
        for o in orders:
            order = {}
            order['id'] = o.order_id
            order['type'] = o.type
            order['pair'] = o.pair
            order['rate'] = o.rate
            order['amount'] = o.amount
            order['timestamp_created'] = o.timestamp_created
            order['status'] = o.status
            orders_list[o.order_id] = order
        return orders_list

    def get_balances(self, r):
        balances = {}
        for currency in self.all_currencies:
            balance = getattr(r, "balance_" + currency)
            balances[currency.upper()] = balance
        return balances
    
class Trader():
    '''
    - Trader should receive currencies to trade with from database
    - Trader should compute transition costs/profits so trader must know:
        * current commission/fee of exchange api
        * last transactions (good to have)
        * price of every cryptocurrency with respect to dollar
        * trader should keep trace of all operations
    - Trader should perform only synchronous trades (live trading)
    - Trader should have some fallback-currency or safety strategy
    '''
    def __init__(self, key_file):
        self.market = MarketKnowledge(key_file)
        self.trade_pairs =  TradeGraph().trade_pairs

    def trade(self):
        print self.market.get_info()

if __name__ == "__main__":
    print "Launching trader with key file %s" % sys.argv[1]
    t = Trader(sys.argv[1])
    t.trade()
